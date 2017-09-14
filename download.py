import request_category as rc
import database as db

import pandas as pd
import numpy as np
import re

import pickle
from datetime import datetime
from pathlib import Path


##  NEW  
## - update_page_table:  Doesn't grab content anymore
## - fill_unique_pages:  Grabs content
def download( *category, depth, pckle = False):  ## pickle = True -->  Search data folder for category pickle file
    
    categories = list(*category)
    
    for cat in categories:
        start = datetime.now()
        pickle_path = './pickles/' + re.sub( ' ', '_', cat) + '_dfs.p'
        pickle_file = Path( pickle_path)
        if pckle and pickle_file.is_file(): ## pckle = True and file exists at pickle_path
            pickle_file_name = pickle_path.split('pickles/')[1]
            ## Load pickle
            with open( pickle_path, 'rb') as f:
                df_tup = pickle.load( f)
                print( "Pickle file exists, ({}) and it's loaded!".format( pickle_file_name))
        else:  ## Gather page information for categories and nested categories
            print( 'No pickle yet')
            df_tup = rc.fill_unique_pages(cat, depth = depth, grab = True)  ## A pickle file will be created with grab = True 
        
        category_pages_df, unique_pages_df, categories_df, subcategories_df, subcat_page_df = df_tup
        n_pages = unique_pages_df.shape[0]
        
        print( "\t\t\tUpdating pages table" )  ## :\n\t\t\t\tCollecting text for {} articles".format(n_pages)
        results = unique_pages_df.apply( lambda x: db.update_page_table( x.pageid, x.title, x.article), axis = 1)
        #results = pages_df.apply( lambda x: db.update_page_table( x.pageid, x.title, x.text), axis = 1)
        
        print( "\t\t\tUpdating categories table")
        ## NOTICE:  set(category_pages_df.category.unique()) == set(category_pages_df.subcategory.unique())
        #categories_df = pd.DataFrame({'category':category_pages_df.category.unique() }) 
        results = categories_df.apply( lambda x: db.update_category_table( x.category), axis = 1)

        print("\t\t\tUpdating subcategories table")
        #subcategories_df = category_pages_df.drop_duplicates( subset = ['category', 'subcategory']).copy()
        results = subcategories_df.apply( lambda x: db.update_sub_category_table( x.subcategory, x.category), axis = 1)      
        
        print("\t\t\tUpdating page-category (link) table")
        #subcat_page_df = category_pages_df.drop_duplicates( subset = ['subcategory', 'pageid']).copy()
        ## TEST
        results = subcat_page_df.apply( lambda x: db.update_page_category_table( x.pageid, x.subcategory, x.category), axis = 1)
        #results = category_pages_df.apply( lambda x: db.update_page_category_table( x.pageid, x.subcategory, x.category), axis = 1)
        timeduration = round((datetime.now()-start).seconds/60,2) ## minutes
        
        print("\t\t\tDownloading Article colletion, update of database tables took a total of {} minutes.".format(timeduration) )
        print("_"*75)

