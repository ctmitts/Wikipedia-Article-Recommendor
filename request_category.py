from sklearn.metrics.pairwise import pairwise_distances
import pandas as pd
import numpy as np
import re
import requests
import psycopg2 as pg2
from psycopg2.extras import RealDictCursor
import wikipedia
from spacy.en import STOP_WORDS
from spacy.en import English
from datetime import datetime

import pickle

nlp = English()
time_of_one_grab = .661189 ## seconds


def get_json( search_term, query):
    r = requests.get( query)  ## request HTTP results
    response = r.json()
    pageinfo = response['query']['pages']
    if isinstance( search_term, str):
        
        pageid = list(pageinfo.keys())[0]
        text = pageinfo[pageid]['extract']
    elif isinstance( search_term, int):
        pageid = str(search_term)
        text = pageinfo[pageid]['extract']
        
    return text, pageid
    

def get_article( search_term ):# title or page id, Capitalization ignored
    base_url = 'https://en.wikipedia.org/w/api.php'
    if isinstance( search_term, str):
        #search_term = format_search( search_term)
        tag = 'titles={}'.format( search_term)
    elif isinstance( search_term, int):
        tag = 'pageids={}'.format( search_term)
    else:
        print( 'Invalid search term...')
        return ''

    action_tag = "?action=query&prop=extracts&explaintext&{}&format=json".format( tag) 
    query = base_url + action_tag
    
    article_text, pageid = get_json( search_term, query)
    
    return article_text, pageid

def format_search( category):
    category_query = re.sub( '\s', '+', category.lower())
    return category_query

def format_query(category, *ptype ):
    '''Category should be provided as a string,  ptype may be page, subcat, or file'''
    categoryF = format_search(category)
    
    ptype_dict = {'page':'0', 'subcat':'14','file':'6'}
    if len( ptype) < 2:
        nstype = ptype_dict[ ptype]
        #print( 'single' + nstype)
    else:
        p1, p2 = ptype
        ptype = p1 + "|" + p2
        nstype = ptype_dict[ p1 ] + "|" + ptype_dict[ p2 ]
    base_url = 'https://en.wikipedia.org/w/api.php'
    action_tag = "?action=query&list=categorymembers&cmlimit=max" ## fetch all category members (pages, subcategories)
    category_tag = '&cmtitle=Category:{}&cmtype={}&cmnamespace={}&format=json'.format( categoryF, ptype, nstype) ## append category to cat_tag
    query = base_url + action_tag + category_tag# + parameters_tag ## concatenate base_url with request tags
    return query

def request_elements( category, *ptype, tag = False):
    query = format_query( category, *ptype)
    
    r = requests.get( query)  ## request HTTP results
    response = r.json()
    try:
        elements_df = pd.DataFrame( response['query']['categorymembers'])
        if tag:
            elements_df['subcategory'] = tag
        return elements_df
    except:
        return pd.DataFrame()  ## Empty category
    
## Clean and Working
tabulate = lambda x, mod: '\t'*((3-x) + mod)
def get_pages( category, depth=3, category_dict= {}, first_run = True  ):  ## Restrixt depth to level 4
    category_pages_df = request_elements( category, 'page', 'subcat', tag = category)
    if first_run:
        category_dict.clear()
    if category_pages_df.empty:  ## if category page is empty return empty dictionary
        return category_dict
    else:  # otherwise, lets separate the articles and sub-categories
        cat_mask = category_pages_df.title.str.contains( 'Category:')
        category_df = category_pages_df[ cat_mask].copy()       
        pages_df = category_pages_df[~cat_mask].copy()  ## Articles listed under category
        if category_df.empty:   ## IF the category has NO sub-categories, store the pages_df and move on
            pages_df.loc[:, 'category'] = category
            category_dict[category] = pages_df
            return category_dict 
        else:  ## Map sub-categories to a list, create a list to store dataframes for each nested category
            sub_categories = category_df.title.str.replace( 'Category:', '').tolist()  
            category_dict[category] = []
            category_dict[category].append(pages_df)
            ## For each sub-category, add pages from subcategories to their parent category list of pages_dfs
            for i, subcat in enumerate(sub_categories):  
                if depth < 0:
                    break
                else:
                    category_dict = get_pages( subcat, depth - 1, first_run = False)
                    try:
                        if type( category_dict[subcat]) is list: ## subcat has nested categories so its a lit 
                            pages_df_from_category = pd.concat( category_dict[subcat] )  ## Original, keep for reference         
                            pages_df_from_category.loc[:,'category'] = subcat ## Rename the category column to be uniform as super-category
                            category_dict[category].append(pages_df_from_category  ) 
                        else:
                            category_dict[category].append( category_dict[subcat] )
                    except:         
                        continue
            try:
                category_dict[category] = pd.concat( category_dict[category])
                category_dict[category]['category'] = category
                category_dict[category] = category_dict[ category].drop_duplicates( subset = ['category','subcategory','pageid','title'], keep = 'last') #, keep = 'first'  If a nested category is part of multiple children nodes, remove the extra copies for each category
                return category_dict
            except:
                return category_dict
            
def cleaner(message):  ## NEED TO TUNE CLEANER
    message = re.sub('\.+', ' ', message)
    message = re.sub('[^a-z0-9 ]',' ', message.lower())
    message = re.sub('\d+','',message)
    message = re.sub('\s+',' ',message)
    message = ' '.join(i.orth_ for i in nlp(message)  ## lemma - original word, ## ortho - root
                    if i.orth_ not in STOP_WORDS)
    message = ' '.join(message.split())
    return message 

def grab_content( page_id, clean = True):
    try:
        page_content = wikipedia.WikipediaPage(pageid = page_id).content
    except: 
        page_content = ''
    if clean:
        return cleaner(page_content)
    else:
        return page_content
        
## NEW - If we grab the article, pickle the category dfs which are used build each database 

# T
def fill_unique_pages( category, depth = 3, grab = False):
    start = datetime.now()
    print('Gathering page information from Category: {}, pages from nested sub-categories (+{} levels) will be \nincluded as a union for each category.'.format( category, depth))
    category_dict = get_pages( category, depth)  
    n_categories = len( category_dict.keys()) 
    print('\tTotal categories after recursive search: {}'.format( n_categories) )
    
    try:
        category_pages_df = pd.concat( category_dict.values())
    ## Edit, below except clause, everything moved left 1 tab
    except:
        print( 'Nothing to fill.')
        return
    category_pages_df.drop('ns', axis = 1, inplace = True)
    category_pages_df.reset_index( drop = True, inplace = True)
        
    unique_pages_df = category_pages_df.drop_duplicates(subset = ['pageid', 'title']).reset_index( drop = True).copy() 
    categories_df = category_pages_df.drop_duplicates( subset = ['category']).reset_index( drop=True).copy()
    subcategories_df = category_pages_df.drop_duplicates( subset = ['category', 'subcategory']).reset_index(drop=True).copy()
    subcat_page_df = category_pages_df.drop_duplicates( subset = ['subcategory', 'pageid']).reset_index( drop=True).copy()
        
    n_grabs = unique_pages_df.shape[0]
        
    estT = round(time_of_one_grab*n_grabs/60, 2)  ## minutes
    print('\tRequesting {} unique articles - ETA: {} minutes'.format( n_grabs, estT))
    if grab:  ## Grab the text articles and pickle the df_tup for later use
        unique_pages_df.loc[:,'article'] = unique_pages_df.pageid.apply( grab_content, clean = False )  ## Don't clean it yet
        get_article = lambda x: unique_pages_df[ unique_pages_df.pageid == x].article.tolist()[0]
        category_pages_df.loc[:, 'article'] = category_pages_df.pageid.apply( get_article)
        
        unique_pages_df.loc[:,'article'] = unique_pages_df.article.apply( cleaner )  ## Now Clean
        df_tup = (category_pages_df, unique_pages_df, categories_df, subcategories_df, subcat_page_df)
         
        pickle_file = re.sub( ' ', '_', category) + '_dfs.p'
        pickle_path = './docker/postgres/data/' + pickle_file
        ## write pickle (binary)
        with open( pickle_path, 'wb') as f:
            pickle.dump( df_tup, f)
                
        print( 'Category DataFrames are pickled at the following location: {}. Raw text is available in\n category_pages_df in the pickle file'.format( pickle_path) )  
        tag = ''
    else:
        tag = '(article excluded)'
        df_tup = (category_pages_df, unique_pages_df, categories_df, subcategories_df, subcat_page_df)
    totT = round((datetime.now()-start).seconds/60,2) ## minutes
    print('\t\tPage collection {} took a total of {} minutes'.format(tag, totT) )
    return df_tup   
