#!/usr/bin/env python
# -*- coding: utf-8 -*-


from settings import *
from lib.document import Document


document_names = os.listdir(DOCUMENT_DIR)


if  __name__ == '__main__':
    print 'clustering...'
    for name in document_names:
        document = Document(name)
        print document.name
