import pandas as pd
import numpy as np

from datetime import datetime
import matplotlib.pyplot as plt

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, NMF

from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV

import database as db
import request_category as rc

class Recommend():
    def __init__(self, min_df=.05, max_df=.90, ngram_range=(1,3), n_components=100):
        self.min_df = min_df
        self.max_df = max_df
        self.ngram_range = ngram_range
        self.n_components = n_components
        self.component_names = ["component_" + str(i+1) for i in range(self.n_components)]
        self.pipe = None
        self.lsa_df = None #pd.DataFrame()
        
    def fit(self, X, Y=None):
        self.pipe = Pipeline([
            ('encoder', TfidfVectorizer( min_df = self.min_df, max_df = self.max_df, 
                                        ngram_range = self.ngram_range, stop_words = 'english')),
            ('truncator',TruncatedSVD( n_components=self.n_components) ),
        ])
        self.lsa_df = pd.DataFrame( self.pipe.fit_transform(X.article), index=X.index, columns=self.component_names)
        self.lsa_df = X[['category','subcategory', 'title','article']].merge( \
                        self.lsa_df, how = 'outer', copy = True,
                        left_index = True, right_index = True, suffixes = ('', ''))
        return self

    def transform(self, X, Y=None): 
        if Y is not None:
            search_doc, pageid = rc.get_article(Y)  ## Y = 'Saffron Technology'

        else:
            pageid = X.index[1]
            search_doc = X.article[pageid]
            
        article_lsa_df = pd.DataFrame( self.pipe.transform( [search_doc]), index=[int(pageid)],columns=self.component_names )
        search_cosine_df = pd.DataFrame( cosine_similarity( self.lsa_df.drop(['category','subcategory','title','article'], axis = 1), article_lsa_df ), columns = ['cosine'], index = self.lsa_df.index)
        search_cosine_df = X[['category', 'subcategory', 'title']] \
            .merge( search_cosine_df, how = 'outer', 
                   left_index = True, right_index = True, copy = True, suffixes = ('', '') )
        search_cosine_df.index = search_cosine_df.title
        search_cosine_df.drop( ['title'], axis = 1, inplace = True)
        return search_cosine_df.sort_values(by = 'cosine', ascending=False)[0:5]
            
    def fit_transform(self, X, Y=None):
        self.fit(X, Y)
        return self.transform(X, Y)