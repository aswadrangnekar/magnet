from itertools import combinations

# verbose = True
verbose = False

# TODO: maintain a previous result ; algo stops when null set and returns the previous result        
def new_apriori(G_DOC_VECTOR, L_DOC_VECTOR , MIN_SUPPORT, document_count):
    is_not_frequent = True
    frequent_items = {}
    results = {}
    apriori_pass = 1
    
    def get_support_per_tx(candidate_itemset,_pass):
        count = 0
        for sha, tx in L_DOC_VECTOR.iteritems():
            if set(candidate_itemset).issubset(tx.keys()):
                count +=1
        # print 'apriori pass %d' %_pass, '::', candidate_itemset, ':', count
        support = (float(count)/document_count) * 100
        #if support > 40:
        #    print candidate_itemset, support
        return support

    # pass 1 precalculations
    #frequent_items = dict([(term, frequency) 
    #                        for term, frequency in G_DOC_VECTOR.iteritems()
    #                        if frequency >= MIN_SUPPORT])

    _frequent_terms = G_DOC_VECTOR.keys()
    
    while is_not_frequent:
        if verbose:
            print 'frequent: ', _frequent_terms

        combos = combinations(_frequent_terms, apriori_pass)
        
        if verbose:
            print '\nApriori pass %d' % apriori_pass
            print '---------------------------------------------------------------->'
        
        previous_pass_frequent_items = frequent_items
        frequent_items = {}
        for candidate_itemset in combos:
            support = get_support_per_tx(candidate_itemset, apriori_pass)
            if support >= MIN_SUPPORT:
                frequent_items[candidate_itemset] = support
                if verbose:
                    print candidate_itemset, frequent_items[candidate_itemset]
        
        # print '\n\n\n >> ', frequent_items.keys(), len(frequent_items.keys())
        tmp_set = []
        for item in frequent_items.keys():
            tmp_set += item

        _frequent_terms = list(set(tmp_set))
        results[apriori_pass] = frequent_items
                
        apriori_pass += 1
        
        # temporary termination condition
        if not frequent_items:
            is_not_frequent = False
    
    #return frequent_items, results
    return previous_pass_frequent_items, results
