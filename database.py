import psycopg2 as pg2
from psycopg2.extras import RealDictCursor
import re
import pandas as pd
import request_category as rc

def connect_to_db():
    con = pg2.connect(host='postgres',
                      dbname='wikipedia',
                      user='postgres')
    cur = con.cursor(cursor_factory=RealDictCursor)
    return con, cur

def query_to_dictionary(query, fetch_res=True):
    con, cur = connect_to_db()
    cur.execute(query)
    if fetch_res:
        results = cur.fetchall()
    else:
        results = None
    con.close()
    return results

def query_to_dataframe(query):
    return pd.DataFrame(query_to_dictionary(query))

def clear_table( *tables):
    for table in tables:
        query = """BEGIN;DELETE FROM {};COMMIT;""".format( table)
        query_to_dictionary(query, fetch_res = False )

## New
#def update_page_table(pageid, title):
#    clean_text = rc.grab_content( pageid)
#    clean_title = re.sub('[^a-z0-9 ]','', title.lower())
#    #cleaned_text = rc.cleaner( text)
#    query = """BEGIN;
#               INSERT INTO pages (pageid, title, article) VALUES ({}, '{}', '{}');
#               COMMIT;""".format(pageid, clean_title, clean_text )
#    query = re.sub( "\s+", " ", query)
#    return query_to_dictionary( query, fetch_res = False)

## Original
def update_page_table(pageid, title, text):
    clean_title = re.sub('[^a-z0-9 ]','', title.lower())
    query = """BEGIN;
               INSERT INTO pages (pageid, title, article) VALUES ({}, '{}', '{}');
               COMMIT;""".format(pageid, clean_title, text )
    query = re.sub( "\s+", " ", query)
    return query_to_dictionary( query, fetch_res = False)

def update_category_table(category):
    query = """BEGIN;
               INSERT INTO categories (category) VALUES ('{}');
               COMMIT;""".format(category )
    #ALTER TABLE category category_id SERIAL PRIMARY KEY;
    query = re.sub( "\s+", " ", query)
    return query_to_dictionary( query, fetch_res = False)

    
def update_sub_category_table(subcategory, category):
    #clean_subcategory = re.sub('[^a-z0-9 ]',' ', subcategory.lower())
    query = """BEGIN;
               INSERT INTO subcategories (subcategory, category_id) 
               VALUES ('{}',(SELECT category_id FROM categories WHERE category = '{}'));
               COMMIT;""".format(subcategory, category )
    #ALTER TABLE category category_id SERIAL PRIMARY KEY;
    query = re.sub("\s+", " ", query)
    return query_to_dictionary( query, fetch_res = False)

## Original
#def update_page_category_table( pageid, subcategory):
#    query = """BEGIN;
#               INSERT INTO page_category (pageid, subcategory_id) 
#               VALUES ({}, (SELECT subcategory_id FROM subcategories WHERE subcategory = '{}'));
#               COMMIT;""".format( pageid, subcategory)
#    query = re.sub("\s+", " ", query)
#    return query_to_dictionary( query, fetch_res = False)

def update_page_category_table( pageid, subcategory, category, display = False):
    query_for_category_id = """SELECT category_id
                            FROM categories
                            WHERE category = '{}'""".format( category)

    query_for_subcategory_id = """SELECT subcategory_id 
                              FROM subcategories
                              WHERE subcategory = '{}'
                              AND category_id = ({})""".format( subcategory, query_for_category_id)
    query = """BEGIN;
               INSERT INTO page_category (pageid, subcategory_id) 
               VALUES ({}, ({}));
               COMMIT;""".format( pageid, query_for_subcategory_id)
    #query = """BEGIN;
    #           INSERT INTO page_category (pageid, subcategory_id) 
    #           VALUES ({}, (SELECT subcategory_id FROM subcategories WHERE subcategory = '{}'));
    #           COMMIT;""".format( pageid, subcategory)
    query = re.sub("\s+", " ", query)
    if display:
        return query
    else:
        return query_to_dictionary( query, fetch_res = False)

def category_query( *category, df = False):
    innerquery = """SELECT stuff.category, stuff.subcategory, pc.pageid
                    FROM (SELECT category, subcategory, subcategory_id 
                          FROM subcategories sc 
                          JOIN categories c 
                          ON sc.category_id = c.category_id
                          WHERE category IN ({}) ) as stuff
                    JOIN page_category pc
                    ON stuff.subcategory_id = pc.subcategory_id""".format(*category)
    innerquery = re.sub( "\s+"," ", innerquery)
    if df:
        return query_to_dataframe( innerquery + ";")
    else:
        return innerquery

def page_query( *category):
    innerquery = category_query( *category)
    outerquery ="""SELECT category, subcategory, p.pageid, p.title
                   FROM ({}) as crap
                   JOIN pages p
                   ON crap.pageid = p.pageid;""".format( innerquery)
    outerquery = re.sub( "\s+", " ", outerquery)
    return query_to_dataframe( outerquery)


def query_pages_by_category( category, limit = False):
    inner_query = """SELECT stuff.category, stuff.subcategory, pc.pageid 
              FROM ( SELECT category, subcategory, subcategory_id 
                     FROM subcategories sc 
                         JOIN categories c 
                         ON sc.category_id = c.category_id 
                     WHERE category = '{}' ) as stuff 
              JOIN page_category pc 
              ON stuff.subcategory_id = pc.subcategory_id""".format( category)

    if limit:
        limit = ' LIMIT {}'.format( limit)
    else: 
        limit = ''

    pages_query = """SELECT crap.category, crap.subcategory, crap.pageid, p.title, p.article
                        FROM ({}) as crap
                        INNER JOIN pages p
                        ON crap.pageid = p.pageid{}""".format( inner_query, limit) 
    pages_query = re.sub( "\s+"," ", pages_query)  
    return pages_query


def get_data(*categories, unique = False):  
    queries = []
    for category in categories:
        cat_query = query_pages_by_category( category)
        
        queries.append( cat_query)
    if len( categories) > 1:  ## Only works for n_categories = 2 
        pages_query = """SELECT b.category, b.subcategory, b.title, b.pageid, b.article
                 FROM (({}) UNION ({}) ) as b;""".format( queries[0], queries[1])
    else: 
        pages_query = cat_query + ";"
    pages_df = query_to_dataframe( pages_query)
    empty_mask =  pages_df.article == ''
    nonempty_pages_df = pages_df[~empty_mask].reset_index(drop = True).copy()
    nonempty_pages_df.index = nonempty_pages_df.pageid
    
    if unique:
        nonempty_pages_df.drop_duplicates(subset = ['pageid', 'title'],inplace = True)
        nonempty_pages_df.reset_index( drop = True, inplace= True) 
    
    nonempty_pages_df.drop( ['pageid'], axis = 1, inplace = True)
    return nonempty_pages_df