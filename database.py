import psycopg2 as pg2
from psycopg2.extras import RealDictCursor
import re
import pandas as pd
import request_categories as rc

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

## New
def update_page_table(pageid, title):
    clean_text = rc.grab_content( pageid)
    clean_title = re.sub('[^a-z0-9 ]',' ', title.lower())
    #cleaned_text = rc.cleaner( text)
    query = """BEGIN;
               INSERT INTO pages (pageid, title, article) VALUES ({}, '{}', '{}');
               COMMIT;""".format(pageid, clean_title, clean_text )
    query = re.sub( "\s+", " ", query)
    return query_to_dictionary( query, fetch_res = False)

## Original
#def update_page_table(pageid, title, text):
#    query = """BEGIN;
#               INSERT INTO pages (pageid, title, article) VALUES ({}, '{}', '{}');
#               COMMIT;""".format(pageid, title, text )
#    query = re.sub( "\s+", " ", query)
#    return query_to_dictionary( query, fetch_res = False)

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

def update_page_category_table( pageid, subcategory):
    query = """BEGIN;
               INSERT INTO page_category (pageid, subcategory_id) 
               VALUES ({}, (SELECT subcategory_id FROM subcategories WHERE subcategory = '{}'));
               COMMIT;""".format( pageid, subcategory)
    query = re.sub("\s+", " ", query)
    return query_to_dictionary( query, fetch_res = False)

def category_query( *category, df = False):
    innerquery = """SELECT stuff.category, stuff.subcategory, pc.pageid
                    FROM (SELECT category, subcategory, subcategory_id 
                          FROM subcategories sc 
                          JOIN categories c 
                          ON sc.category_id = c.category_id
                          WHERE category IN {} ) as stuff
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


