CREATE DATABASE wikipedia;
\c wikipedia;
CREATE TABLE pages (
    pageid INTEGER,
    title TEXT,
    article TEXT
);
CREATE TABLE categories (
    category_id serial PRIMARY KEY,
    category TEXT
);
CREATE TABLE subcategories (
    subcategory_id serial PRIMARY KEY,
    subcategory TEXT,
    category_id INTEGER
);
CREATE TABLE page_category (
    category_page_id serial Primary KEY,
    pageid INTEGER,
    subcategory_id INTEGER
);


