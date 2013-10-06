#! /usr/bin/env python
# -*- coding: utf-8 -*-


from settings import DOCUMENT_DIR


class Document(object):
    def __init__(self, name):
        self.name = name
        # self.word_count = None
        # self.tokens = None
        # self.hash_id = None
        # self.local_support = None
        # self.global_support = None

    def tokenize(self):
        pass
