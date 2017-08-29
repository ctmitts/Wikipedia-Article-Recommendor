import pandas as pd
import numpy as np
import re
import requests
import psycopg2 as pg2
from psycopg2.extras import RealDictCursor
import wikipedia
from spacy.en import STOP_WORDS
from spacy.en import English

nlp = English()

import nltk

def category_format( category):
    category_query = re.sub( '\s', '+', category)
    return category_query
    
def format_query(category, ptype ):
    '''Category should be provided as a string,  ptype may be page, subcat, or file'''
    categoryF = category_format(category)
    
    ptype_dict = {'page':'0', 'subcat':'14','file':'6'}
    nstype = ptype_dict[ ptype]
    base_url = 'https://en.wikipedia.org/w/api.php'
    action_tag = "?action=query&list=categorymembers&cmlimit=max" ## fetch all category members (pages, subcategories)
    category_tag = '&cmtitle=Category:{}&cmtype={}&cmnamespace={}&format=json'.format( categoryF, ptype, nstype) ## append category to cat_tag
    query = base_url + action_tag + category_tag# + parameters_tag ## concatenate base_url with request tags
    return query

def request_elements( category, ptype, tag = False):
    query = format_query( category, ptype)
    
    r = requests.get( query)  ## request HTTP results
    response = r.json()

    elements_df = pd.DataFrame( response['query']['categorymembers'])
    if tag:
        elements_df['subcategory'] = tag 
    return elements_df


def get_subcategories( category, depth =4, subcategories = []):  ## Restrixt depth to level 4
    
    category_df = request_elements( category, 'subcat')
    
    if category_df.empty:
        
    for subcat in category_df.title.str.replace('Category:', '').tolist():
        
        if subcat not in subcategories:
            subcategories.append( subcat)
            try:
                if depth < 0:
                    break
                else:
                    subcategories = get_subcategories( subcat,depth - 1, subcategories)
            except:
                continue
    return subcategories

## Original
def get_subcategories( category, depth =4, subcategories = []):  ## Restrixt depth to level 4
    
    category_df = request_elements( category, 'subcat')
    for subcat in category_df.title.str.replace('Category:', '').tolist():
        
        if subcat not in subcategories:
            subcategories.append( subcat)
            try:
                if depth < 0:
                    break
                else:
                    subcategories = get_subcategories( subcat,depth - 1, subcategories)
            except:
                continue
    return subcategories

def cleaner(message):
    message = re.sub('\.+', ' ', message)
    message = re.sub('[^a-z0-9 ]',' ', message.lower())
    #message = re.sub('\d+',' NUMBER ',message)
    
    message = ' '.join(i.lemma_ for i in nlp(message)  ## lemma - original word, ## ortho - root
                    if i.orth_ not in STOP_WORDS)
    message = re.sub('\s+',' ',message)
    return message 

## New - apply cleaner
def grab_content( page_id, clean = True):
    try:
        page_content = wikipedia.WikipediaPage(pageid = page_id).content
    except: 
        page_content = ''
    if clean:
        return cleaner(page_content)
    else:
        return page_content


## Original
#def grab_content( page_id):
#    try:
#        page_content = wikipedia.WikipediaPage(pageid = page_id).content
#    except: 
#        page_content = ''
#    return page_content
    
            
def get_pages( category, depth = 4 ):
    ##astype
    print( "\tCollecting nested categories (depth = {})".format(depth ) )
    subcategories = get_subcategories( category, depth, subcategories = [] )
    
    print( "\tGathering associated pageids")
    pages_df_list = []
    #categories_pageid_dict = {}
    
    pages_df = request_elements( category, 'page', category)
    
    pages_df_list.append( pages_df)
    #categories_pageid_dict[category] = pages_df.pageid.tolist()
    
    for subcat in subcategories:
        #tag = category + "/" + subcat
        pages_df = request_elements( subcat, 'page', subcat)
        
        try:
            #categories_pageid_dict[subcat] = pages_df.pageid.tolist()
            pages_df_list.append( pages_df)
        except:
            continue
        
    pages_df = pd.concat( pages_df_list)
    
    pages_df = pages_df.reset_index(drop = True )
    
    pages_df.drop_duplicates().reset_index(drop = True, inplace = True)
    
    pages_df.drop('ns', axis = 1, inplace = True)
    
    pages_df['category'] = category
    pages_df.pageid = pages_df.pageid.apply( lambda x: int(x))
    
    #print( "\tGrabbing text for each pageid, applying cleaner to article and title")
    #pages_df['text'] = pages_df.pageid.apply( grab_content)

    
    #pages_df.text = pages_df.text.apply( cleaner)
    #pages_df.title = pages_df.title.apply( cleaner) 
    
    return pages_df #, categories_pageid_dict
                             


    
    
