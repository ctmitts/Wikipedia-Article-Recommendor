import request_categories as rc
import database as db
import pandas as pd
from datetime import datetime

def download( *category, depth, pickle = False):
    
    categories = list(*category)
    
    for cat in categories:
        start = datetime.now()
        if pickle:
            pages_df = pd.read_pickle('./docker/postgres/data/{}'.format( pickle) )
        else:
            print( "Collecting Wikipedia pages for Category: {}".format(category) )
            pages_df = rc.get_pages( cat, depth)
        #categories_df = pages_df[['category']].drop_duplicates().copy()
        subcategories_df = pages_df[['subcategory']].drop_duplicates().copy()

        n_pages = pages_df.shape[0]
        print( "Updating pages table: Collecting text for {} articles".format(n_pages) )
        ## Update pages table
        results = pages_df.apply( lambda x: db.update_page_table( x.pageid, x.title), axis = 1)
        #results = pages_df.apply( lambda x: db.update_page_table( x.pageid, x.title, x.text), axis = 1)

        print( "Updating categories table")
        ## Update categories table
        #results = categories_df.apply( lambda x: db.update_category_table( x.category), axis = 1)
        db.update_category_table( cat)

        print("Updating subcategories table")
        results = subcategories_df.apply( lambda x: db.update_sub_category_table( x.subcategory, cat), axis = 1) 
        #results = subcategories_df.apply( lambda x: db.update_sub_category_table( x.subcategory, category), axis = 1) 

        print("Updating page-category (link) table")
        results = pages_df.apply( lambda x: db.update_page_category_table( x.pageid, x.subcategory), axis = 1)
        
        timeduration = datetime.now()-start
        
        print("Article colletion for Category: {} took a total of {} minutes.".format( cat, timeduration) )
        
        



