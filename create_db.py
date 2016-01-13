import os
import psycopg2
import urlparse
import csvkit

urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])

db = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

#create tables
cur = db.cursor()

#genres table
cur.execute("CREATE TABLE genres (id serial PRIMARY KEY, databaseID integer, genre varchar);")
with open('data/genre.csv','rb') as fin:
    dr = csvkit.unicsv.UnicodeCSVDictReader(fin)
    to_db = [(i['databaseID'], i['genreText']) for i in dr]    
cur.executemany("INSERT INTO genres (databaseID, genre) VALUES(%s, %s);", to_db)

#topics table
cur.execute("CREATE TABLE topics (id serial PRIMARY KEY, databaseID integer, topic varchar);")
with open('data/topicalSubject.csv','rb') as fin:
    dr = csvkit.unicsv.UnicodeCSVDictReader(fin)
    to_db = [(i['databaseID'], i['topicalSubjectText']) for i in dr]
cur.executemany("INSERT INTO topics (databaseID, topic) VALUES (%s, %s);", to_db)

#places table
cur.execute("CREATE TABLE places (id serial PRIMARY KEY, databaseID integer, place varchar);")
with open('data/geographicSubject.csv','rb') as fin:
    dr = csvkit.unicsv.UnicodeCSVDictReader(fin)
    to_db = [(i['databaseID'], i['geographicSubjectText']) for i in dr]   
cur.executemany("INSERT INTO places (databaseID, place) VALUES (%s, %s);", to_db)

#names table
cur.execute("CREATE TABLE names (id serial PRIMARY KEY, databaseID integer, name varchar);")
with open('data/nameSubject.csv','rb') as fin:
    dr = csvkit.unicsv.UnicodeCSVDictReader(fin)
    to_db = [(i['databaseID'], i['nameSubjectText']) for i in dr]
cur.executemany("INSERT INTO names (databaseID, name) VALUES (%s, %s);", to_db)

db.commit()
db.close()