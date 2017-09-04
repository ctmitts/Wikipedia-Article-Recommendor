import request_category as rc
import database as db
from download import download

import pickle
from pathlib import Path
import re

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, NMF

from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, StratifiedShuffleSplit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
import sklearn.externals.joblib


#%matplotlib inline

def get_data(*categories):
    queries = []
    for category in categories:
        cat_query = db.query_pages_by_category( category)
        
        queries.append( cat_query)
    if len( categories) > 1:
        pages_query = """SELECT b.category, b.subcategory, b.title, b.pageid, b.article
                 FROM (({}) UNION ({}) ) as b;""".format( queries[0], queries[1])
    else: 
        pages_query = cat_query + ";"
        
    #ml_query = db.query_pages_by_category( categories[0])  # 'machine learning'
    #bs_query = db.query_pages_by_category( categories[1])   # 'business software'
    #pages_query = """SELECT b.category, b.subcategory, b.title, b.pageid, b.article
    #             FROM (({}) UNION ({}) ) as b;""".format( ml_query, bs_query)

    pages_df = db.query_to_dataframe( pages_query)
    
    empty_mask =  pages_df.article == ''
    nonempty_pages_df = pages_df[~empty_mask].reset_index(drop = True).copy()
    nonempty_pages_df.index = nonempty_pages_df.pageid
    nonempty_pages_df.drop( ['pageid'], axis = 1, inplace = True)
    

    return nonempty_pages_df


    
def search(article, pckle = False ):
    
    nonempty_pages_df = get_data('machine learning', 'business software') 
    
    n_components = 700
    component_names = ["component_" + str(i+1) for i in range(n_components)]
    
    if pckle:
        cosine_pipe = sklearn.externals.joblib.load('./pickles/cosine.p')
        LSA_mat = pd.read_pickle( './pickles/LSA_mat.p')
        
        
    else:
        
        cosine_pipe = Pipeline([
            ('encoder', TfidfVectorizer(ngram_range = (1,2),
                                 min_df = 3, max_df = .9, 
                                 stop_words = 'english')),
            ('truncator',TruncatedSVD(n_components=n_components) ),
        ])

        svd_matrix = cosine_pipe.fit_transform( nonempty_pages_df.article)

        latent_semantic_analysis = pd.DataFrame(svd_matrix,
                                            index=nonempty_pages_df.index,#nonempty_pages_df.pageid,
                                            columns=component_names)

        LSA_mat = nonempty_pages_df[['category','subcategory', 'title','article']] \
                      .merge( latent_semantic_analysis, how = 'outer',
                              left_index = True, right_index = True, 
                                 copy = True, suffixes = ('', ''))
            
        sklearn.externals.joblib.dump(cosine_pipe, './pickles/cosine.p')
        pd.to_pickle( LSA_mat, './pickles/LSA_mat.p')
        
        
    search_doc, pageid = rc.get_article(article)  ## Saffron Technology , Spreadsheet, Brain, Statistics

    search_doc = rc.cleaner( search_doc)
    
    search_svd = cosine_pipe.transform( [search_doc])

    search_lsa = pd.DataFrame(search_svd,
                        index=[int(pageid)],#nonempty_pages_df.pageid,
                                        columns=component_names)
    
    search_cosine_df = pd.DataFrame( cosine_similarity( LSA_mat.drop(['category','subcategory','title','article'], axis = 1), search_lsa ), columns = ['cosine'], index = LSA_mat.index)
    search_cosine_df = nonempty_pages_df[['category', 'subcategory', 'title']] \
                    .merge( search_cosine_df, how = 'outer', 
                           left_index = True, right_index = True, copy = True, suffixes = ('', '') )
    search_cosine_df.index = search_cosine_df.title
    search_cosine_df.drop( ['title'], axis = 1, inplace = True)
    return search_cosine_df.sort_values(by = 'cosine', ascending=False)[0:5]
    
   
    
    
    
    
    