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
from sklearn.linear_model import LogisticRegression

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer, LabelEncoder

import database as db
import request_category as rc

pages_df = db.get_data('machine learning', 'business software', unique = False) 

X = pages_df['article'].copy()

encoder = LabelEncoder()
y = encoder.fit_transform( pages_df['subcategory'] )

X_train, X_test, y_train, y_test = train_test_split( X, y, random_state = 42)

lr_pipe = Pipeline([
        ('encoder', TfidfVectorizer(ngram_range = (1,2),
                                 min_df = 3, max_df = .9, 
                                 stop_words = 'english')),
        ('truncator',TruncatedSVD(n_components=700, random_state=42) ),
        ('model', LogisticRegression( random_state= 42, n_jobs=-1, solver = 'sag', multi_class = 'ovr' )) #  'multinomial'
    ])

lr_params = {
    'model__C':np.logspace(-3,3,7)
}

gs_lr_pipe = GridSearchCV(lr_pipe, param_grid=lr_params, cv=5, n_jobs=-1) # StratifiedShuffleSplit(n_splits=5)

gs_lr_pipe.fit(X_train,y_train)



def predict( article):
    
    search_doc, pageid = rc.get_article(article)  
        
        
    #predicted_probs = gs_lr_pipe.predict_proba([search_doc])  ## 'Brain'
    #predicted_probs = predicted_probs.reshape(-1,1)

    #cats = encoder.inverse_transform(  range(63))

    #probs_df = pd.DataFrame( predicted_probs , columns= ['P'], index = cats)
    
    
    #n_closest = probs_df.sort_values(by = ['P'],ascending=False)[0:n]
    predicted = encoder.inverse_transform( gs_lr_pipe.predict( [search_doc] ) )[0]
    
    return predicted#, n_closest