#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os


# verbose = True
normalize = True
verbose = False
PROJECT_DIR = os.path.dirname(__file__)
DOCUMENT_DIR = os.path.join(PROJECT_DIR, 'var/documents')
DOC_CLEANUP_PATTERN = r"[@().,!\[\]:\-?;*/]|[0-9]"


# number of docs in RESUMEDIR
DOCUMENT_count = len(os.listdir(DOCUMENT_DIR))


# search patterns
# TODO 1 : find an alternative to replace or eliminate junk chars
# DOC_CLEANUP_PATTERN = '\(|\)|&|,|:|\-|\/|\*|[0-9]+|\.|www'

# Minimum support value in % (demo: 60+)
MIN_SUPPORT = 60

