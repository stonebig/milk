# -*- coding: utf-8 -*-
# Copyright (C) 2008-2010, Luis Pedro Coelho <lpc@cmu.edu>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
'''
================
Tree Classifier
================

Decision tree based classifier
------------------------------

'''

from __future__ import division
import numpy as np
from .classifier import normaliselabels

class Leaf(object):
    '''
    v : value
    w : weight
    '''
    def __init__(self, v, w):
        self.v = v
        self.w = w
    def __repr__(self):
        return 'Leaf(%s,%s)' % (self.v, self.w)

class Node(object): # This could be replaced by a namedtuple
    def __init__(self, featid, featval, left, right):
        self.featid = featid
        self.featval = featval
        self.left = left
        self.right = right

def _split(features, labels, weights, criterion, subsample, R):
    N,f = features.shape
    if subsample is not None:
        samples = np.array(R.sample(xrange(features.shape[1]), subsample))
        features = features[:, samples]
        f = subsample
    best = None
    best_val = -1.
    for i in xrange(f):
        domain_i = sorted(set(features[:,i]))
        for d in domain_i[1:]:
            cur_split = (features[:,i] < d)
            if weights is not None:
                value = criterion(labels[cur_split], labels[~cur_split], weights[cur_split], weights[~cur_split])
            else:
                value = criterion(labels[cur_split], labels[~cur_split])
            if value > best_val:
                best_val = value
                if subsample is not None:
                    ti = samples[i]
                else:
                    ti = i
                best = ti,d
    return best


from ._tree import set_entropy
from ._tree import information_gain as _information_gain
def information_gain(labels0, labels1, include_entropy=False):
    '''
    ig = information_gain(labels0, labels1, include_entropy=False)

    Information Gain
    See http://en.wikipedia.org/wiki/Information_gain_in_decision_trees

    The function calculated here does not include the original entropy unless
    you explicitly ask for it (by passing include_entropy=True)
    '''
    if include_entropy:
        return set_entropy(np.concatenate( (labels0, labels1) )) + \
                _information_gain(labels0, labels1)
    return _information_gain(labels0, labels1)


def build_tree(features, labels, criterion, min_split=4, subsample=None, R=None, weights=None):
    '''
    tree = build_tree(features, labels, criterion, min_split=4, subsample=None, R=None, weights={all 1s})

    Parameters
    ----------
    features : sequence
        features to use
    labels : sequence
        labels
    criterion : function {labels} x {labels} -> float
        function to measure goodness of split
    min_split : integer
        minimum size to split on
    subsample : integer, optional
        if given, then, at each step, choose
    R : source of randomness, optional
        See `milk.util.get_pyrandom`
    weights : sequence, optional
        weight of instance (default: all the same)

    Returns
    -------
    tree : Tree
    '''
    assert len(features) == len(labels), 'build_tree: Nr of labels does not match nr of features'
    features = np.asanyarray(features)
    labels = np.asanyarray(labels)
    if subsample is not None:
        if subsample <= 0:
            raise ValueError('milk.supervised.tree.build_tree: `subsample` must be > 0.\nDid you mean to use None to signal no subsample?')
        from ..utils import get_pyrandom
        R = get_pyrandom(R)

    def recursive(features, labels):
        N = float(len(labels))
        if N < min_split:
            return Leaf(labels.sum()/N, N)
        S = _split(features, labels, weights, criterion, subsample, R)
        if S is None:
            return Leaf(labels.sum()/N, N)
        i,thresh = S
        split = features[:,i] < thresh
        return Node(featid=i,
                    featval=thresh,
                    left =recursive(features[ split], labels[ split]),
                    right=recursive(features[~split], labels[~split]))
    return recursive(features, labels)

def apply_tree(tree, features):
    '''
    conf = apply_tree(tree, features)

    Applies the decision tree to a set of features.
    '''
    if type(tree) is Leaf:
        return tree.v
    if features[tree.featid] < tree.featval:
        return apply_tree(tree.left, features)
    return apply_tree(tree.right, features)


class tree_learner(object):
    '''
    tree = tree_learner()
    model = tree.train(features, labels)
    model2 = tree.train(features, labels, weights=weights)
    predicted = model.apply(testfeatures)

    A decision tree classifier (currently, implements the greedy ID3 
    algorithm without any pruning.

    Attributes
    ----------
    criterion : function, optional
        criterion to use for tree construction,
        this should be a function that receives a set of labels
        (default: information_gain).

    min_split : integer, optional
        minimum size to split on (default: 4).
    '''
    def __init__(self, criterion=information_gain, min_split=4, return_label=True, subsample=None, R=None):
        self.criterion = criterion
        self.min_split = min_split
        self.return_label = return_label
        self.subsample = subsample
        self.R = R

    def train(self, features, labels, normalisedlabels=False, weights=None):
        if not normalisedlabels:
            labels,names = normaliselabels(labels)
        tree = build_tree(features, labels, self.criterion, self.min_split, self.subsample, self.R, weights)
        return tree_model(tree, self.return_label)

tree_classifier = tree_learner

class tree_model(object):
    '''
    tree model
    '''
    def __init__(self, tree, return_label):
        self.tree = tree
        self.return_label = return_label

    def apply(self,feats):
        value = apply_tree(self.tree, feats)
        if self.return_label:
            return value > .5
        return value

