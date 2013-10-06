#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import syslog
import time
import traceback

from lib.stopwords import STOPWORDS
from functools import partial
from itertools import combinations
from operator import ne
from pprint import pprint
from lib.PorterStemmer import PorterStemmer
from lib.pydocx.docx import *
from settings import *
from util import generate_sha1, path_checksum

from lib.algos import apriori
from lib.algos1 import new_apriori

# Following parameters are imported from settings and used in this module
#   :DOCUMENT_DIR directory base path where the word documents are stacked
#                 (currently only word docs are supported,
#                  later will convert all type of doc to 
#                  xml/json format in this directory)
#   :if any other param used metion here

# syslog LOG_EMERG, LOG_ALERT, LOG_CRIT, 
#        LOG_ERR, LOG_WARNING, LOG_NOTICE, 
#        LOG_INFO, LOG_DEBUG


class Document(object):
    """ Document abstraction"""

    def __init__(self, doc_name):
        self.doc_name = doc_name
        self.abs_path = os.path.join(DOCUMENT_DIR, self.doc_name)
        self.doc_sha = generate_sha1(doc_name)

        self.tokens = []
        self.local_doc_vector_not_normalized = {}
        self.local_doc_vector = {}

        self.cluster_label = []

    def _clean_formatting(self, token):
        return re.sub(ur'•|“|”|’|–', '', token)

    def _eliminate_punctuations(self, token):
        ''' Detects punctuations and returns a list seperated tokens
        
        DOC_CLEANUP_PATTERN below is imported from settings.py
        : DOC_CLEANUP_PATTERN r"[().,!:-?;*/]|[0-9]"
        
        example:
                if,
                token = token = 'aswad, (aswad; (aswad)*'
                
                then the function would return,
                    ['aswad', 'aswad', 'aswad']
        
        '''
        return re.sub(DOC_CLEANUP_PATTERN, ' ', token).strip().split()

    def tokenize(self):
        # TODO: part of filteration can be excluded from here
        doc = opendocx(self.abs_path)
        stanzas = getdocumenttext(doc)

        for stanza in stanzas:
            dirty_tokens = stanza.split(" ")

            for token in dirty_tokens:
                if (token != ''):
                    token = self._clean_formatting(token)
                    token = self._eliminate_punctuations(token)
                    token = [token.lower() for token in token]
                    self.tokens = self.tokens + token

                    if verbose:
                        print token

        if verbose:
            print 'tokens for %s : ' % self.doc_name
            print 'hash : ', self.doc_sha
            print 'tokens : ', self.tokens

    def stem(self):
        stemmer = PorterStemmer()
        stm = lambda str: stemmer.stem(str, 0, len(str)-1)
        self.tokens = [stm(token) for token in self.tokens]

        if verbose:
            print 'token stem for %s : ' % self.doc_name
            print 'hash : ', self.doc_sha
            print 'tokens : ', self.tokens

    def remove_stopwords(self):
        self.tokens = [token for token in self.tokens if len(token) > 2]
        for wrd in STOPWORDS:
            self.tokens = filter(partial(ne,wrd), self.tokens)

        if verbose:
            print 'eliminate stop words %s : ' % self.doc_name
            print 'hash : ', self.doc_sha
            print 'tokens : ', self.tokens

    def generate_doc_vector(self):
        for token in self.tokens:
            self.local_doc_vector_not_normalized[token] = \
                                            self.tokens.count(token)
            self.local_doc_vector[token] = self.tokens.count(token)
        


class Preprocessor(object):
    """ Implementation of common pre-processing steps

        Note: A document can have customized pre-processing steps,
        in such cases this class can be overridden
        
        default pre-processing steps
            Tokenize
            get document frequency vector

    """

    def __init__(self):
        self.doc_names = os.listdir(DOCUMENT_DIR)
        self.document_count = len(self.doc_names)
        self.doc_dict = {}      # key/value = doc_sha/doc object
        self.prepare_doc_dict()

        self.global_doc_vector = {}
        self.global_doc_vector_not_normalized = {}
        self.global_support = {}
        self.frequent_itemset = None
        self.apriori_pass_results = None
        self.cluster = {}
        self.outliers = []

        
    def prepare_doc_dict(self, update=False):
        if update is True:
            # Update doc_names, change was detected in Document directory
            self.doc_names = os.listdir(DOCUMENT_DIR)
            syslog.syslog(syslog.LOG_INFO, 'INFO: updated document names')

        for doc_name in self.doc_names:
            d = Document(doc_name)
            self.doc_dict.setdefault(d.doc_sha, d)

    def update_global_doc_vector(self, local_doc_vector, local_doc_vector_not_normalized, doc_sha):
        for token, freq in local_doc_vector.iteritems():
            try:
                self.global_doc_vector[token] += freq
                self.global_doc_vector_not_normalized[token] += \
                                    local_doc_vector_not_normalized[token]
                self.global_support[token].add(doc_sha)
            except:
                self.global_doc_vector[token] = freq
                self.global_doc_vector_not_normalized[token] = \
                                    local_doc_vector_not_normalized[token]
                self.global_support[token] = set([doc_sha])

    def get_initial_cluster(self):
        """ Forms overlapping initial clusters."""

        for doc_hash, doc in self.doc_dict.iteritems():
            self.outliers.append({doc_hash: doc.doc_name})
            flaged_outlier = True
            for frequent_items in self.frequent_itemset.keys():
                is_subset = set(frequent_items).issubset(set(doc.local_doc_vector.keys()))
                try:
                    if is_subset and self.cluster[frequent_items]:
                        self.cluster[frequent_items].append({doc_hash: doc.doc_name})
                        doc.cluster_label.append(frequent_items)
                        flaged_outlier = False
                except:
                    syslog.syslog(syslog.LOG_INFO, \
                        'handeling key error by inserting a key in dict')
                    self.cluster[frequent_items] = [{doc_hash: doc.doc_name}]
                    doc.cluster_label.append(frequent_items)
                    flaged_outlier = False

            if not flaged_outlier:
                self.outliers.pop()

        if verbose:
            pprint(self.outliers)
            print '\n\n'
            pprint(self.cluster)

    def _get_cluster_support(self, token):
        return 100

    def _get_global_support(self, token):
        return (float(len(self.global_support[token]))/self.document_count) * 100

    def _get_score(self, doc):
        """ calculate score to make cluster disjoint.
            
            TODO: 1: there is scope to parallelize this
                  function, so moved this aside.
                  
                  2: also if possible it should be assigned
                  to only one cluster since frequent_itemset are known.
                  
                  3. rewrite
        """

        score = {}
        label_items = set([])

        for label in doc.cluster_label:
            label_items = label_items.union(set(label))

        for label in doc.cluster_label:
            term1 = sum(
                    [doc.local_doc_vector_not_normalized[token] * \
                     self._get_cluster_support(token) \
                     for token in label]
                     )

            term2 = sum(
                    [(doc.local_doc_vector_not_normalized[token] * \
                     self._get_global_support(token)) \
                     for token in (label_items - set(label))]
                     )

            score[term1 - term2] = label

        # print score
        return score

    def get_disjoint_cluster(self):
        """ makes clusters disjoint"""

        disjoint_clusters = {}
        for cluster_label in self.cluster.keys():
            disjoint_clusters[cluster_label] = []

        for doc_hash, doc in self.doc_dict.iteritems():
            if len(doc.cluster_label) > 1:
                scores = self._get_score(doc)
                cluster_label = scores[max(scores.keys())]
                doc.cluster_label = cluster_label
                disjoint_clusters[cluster_label].append({doc.doc_sha: doc.doc_name})

        return disjoint_clusters
                
    def preprocess(self):
        for doc_hash, doc in self.doc_dict.iteritems():
            syslog.syslog(syslog.LOG_INFO, \
                        'started processing document : %s' % doc.doc_name)
            if verbose:
                print 'processing document :', doc.doc_name
            doc.tokenize()
            doc.stem()
            doc.remove_stopwords()
            doc.generate_doc_vector()
            self.update_global_doc_vector(doc.local_doc_vector,
                                          doc.local_doc_vector_not_normalized,
                                          doc.doc_sha)

            if verbose:
                time.sleep(1)

        # normalize local_doc_vector
        if normalize:
            import math
            for doc_hash, doc in self.doc_dict.iteritems():
                for token, freq in doc.local_doc_vector.iteritems():
                    if self.global_doc_vector[token] > 0:
                        doc.local_doc_vector[token] = \
                            freq * (float(self.document_count)/self.global_doc_vector[token])
                            #freq * math.log(float(self.document_count)/self.global_doc_vector[token])

                self.update_global_doc_vector(doc.local_doc_vector,
                                          doc.local_doc_vector_not_normalized,
                                          doc.doc_sha)

        # TODO: clean this code
        L_DOC_VECTOR = {}
        for doc_hash, doc in self.doc_dict.iteritems():
            L_DOC_VECTOR[doc_hash] =  doc.local_doc_vector


        self.frequent_itemset, self.apriori_pass_results = \
                new_apriori(self.global_doc_vector, 
                            L_DOC_VECTOR, MIN_SUPPORT,
                            self.document_count)

        # cluster formation
        if self.frequent_itemset:
            syslog.syslog('started cluster formation')
            self.get_initial_cluster()         # initial clusters

            if len(self.cluster.keys()) > 1:
                disjoint_clusters = \
                    self.get_disjoint_cluster()    # disjoint clusters
                if disjoint_clusters:
                    self.cluster = disjoint_clusters

            print 'Clusters: '
            pprint(self.cluster)

            print '\n\nOutliers : '
            pprint(self.outliers)


if __name__ == '__main__':
    DOCUMENT_DIR_HASH = path_checksum([DOCUMENT_DIR])
    preprocessor = Preprocessor()

    # TODO: move in while loop to run as service
    preprocessor.preprocess()
    
    while True:
        # directory watchdog
        hash_check = path_checksum([DOCUMENT_DIR])
        
        if not hash_check == DOCUMENT_DIR_HASH:
            syslog.syslog(syslog.LOG_INFO, \
                        'INFO: changed detected in DOCUMENT_DIR')

            preprocessor.prepare_doc_dict(update = True)
            DOCUMENT_DIR_HASH = hash_check
        else:
            syslog.syslog(syslog.LOG_INFO, \
                        'INFO: No changed detected in DOCUMENT_DIR')
                        
        time.sleep(5)
            
