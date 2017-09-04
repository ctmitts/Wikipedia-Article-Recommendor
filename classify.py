import request_category as rc
import database as db
from download import download
import search

import pickle
from pathlib import Path
import re

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer, LabelEncoder
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, StratifiedShuffleSplit
from sklearn.linear_model import LogisticRegression
import sklearn.externals.joblib


def train():

    pages_df = search.get_data( 'machine learning', 'business software')
    
    X = pages_df['article'].copy()

    encoder = LabelEncoder()
    y = encoder.fit_transform( pages_df['subcategory'] )
    
    
    X_train, X_test, y_train, y_test = train_test_split( X, y, random_state = 42)
    
    lr_pipe = Pipeline([
        ('encoder', TfidfVectorizer(ngram_range = (1,2),
                                 min_df = 3, max_df = .9, 
                                 stop_words = 'english')),
        ('truncator',TruncatedSVD(n_components=700) ),
        ('model', LogisticRegression())
    ])

    lr_params = {
        'model__C':np.logspace(-3,3,7)
    }

    gs_lr_pipe = GridSearchCV(lr_pipe, param_grid=lr_params, cv=5) # StratifiedShuffleSplit(n_splits=5)

    gs_lr_pipe.fit(X_train,y_train)
  
    #gs_lr_pipe.best_score_
    
    sklearn.externals.joblib.dump(gs_lr_pipe, './pickles/LogitModel1.p')
    
    return gs_lr_pipe
    
    
    
def predict(article, pckle = True, n = 5 ):
    
    '''Pass article name as title, pageid, or url, Return top 5 predicted categories by default'''

    pages_df = search.get_data( 'machine learning', 'business software')
    
    X = pages_df['article'].copy()

    encoder = LabelEncoder()
    y = encoder.fit_transform( pages_df['subcategory'] )
    cats = encoder.inverse_transform(  range(0,(max(y) + 1) ) ) 
    

    if pckle:
        gs_lr_pipe = sklearn.externals.joblib.load('./pickles/LogitModel1.p')
        
    else:
        gs_lr_pipe = train()
    # Slack (software),Saffron Technology, Brain, Statistics, TensorFlow, Tableau Software
    
    
    if 'wiki/' in article:
        article = article.split('wiki/')[1]
    
    #else:
        
    search_doc, pageid = rc.get_article(article)  
    search_doc = rc.cleaner( search_doc)
        
        
    predicted_probs = gs_lr_pipe.predict_proba([search_doc])  ## 'Brain'
    predicted_probs = predicted_probs.reshape(-1,1)

    #cats = encoder.inverse_transform(  range(63))

    probs_df = pd.DataFrame( predicted_probs , columns= ['P'], index = cats)
    
    
    n_closest = probs_df.sort_values(by = ['P'],ascending=False)[0:n]
    predicted = encoder.inverse_transform( gs_lr_pipe.predict( [search_doc] ) )[0]
    
    return predicted, n_closest
    
        
        
        
        
        
        
        
        