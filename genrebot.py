import random
import twitter
from local_settings import *
import os
import psycopg2
import urlparse
import string

urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])

db = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

cur = db.cursor()

#templates
templates = [('{0} about {1} ', ('genre', 'topic')),
             ('{0} of {1} ', ('genre', 'place')),
             ('{0} about {1} ', ('genre', 'name'))]

#subjecttypes
types = {'place':{'tablename':'places', 'column':'place', 'search':'[place]='},
         'topic':{'tablename':'topics', 'column':'topic', 'search':'[topic]='},
         'name': {'tablename':'names', 'column':'name', 'search':'[namePart_mtxt_s]='},
         'genre': {'tablename':'genres', 'column':'genre', 'search':'[genre]='}}


def randomGenre():
    '''Get one random genre from a list of distinct values from the db. Returns tuple for use in next query.'''
    sql = ("select distinct(genre) "
       "from genres;")
    cur.execute(sql)
    genres = [c for c in cur.fetchall()]
    genre = random.choice(genres)
    print genre
    if genre is not None:
        return genre
    else:
        randomGenre()

def getDistinct(genre, subjecttype):
    '''Get the list of distinct subjects given a random subject type (except genre--addressed in randomGenre)'''
    query = ("select distinct(t.{0}) "
       "from genres g, {1} t "
       "where g.genre = %s "
       "and t.databaseID=g.databaseID ").format(subjecttype['column'], subjecttype['tablename'])
    cur.execute(query, genre)
    distincts = cur.fetchall()
    return distincts

def getOneSubject(genre, subject, subjecttype):
    '''Query the db for the random subject and return a database id, the genre, and subject (useful only if you want to
    set a higher threshold for tweeting generated genres.'''
    values = genre + subject
    sql = ("select g.databaseID, g.genre, t.{0} "
       "from genres g, {1} t "
       "where g.genre = %s "
       "and t.{2} = %s "
       "and t.databaseID=g.databaseID ").format(subjecttype['column'], subjecttype['tablename'], subjecttype['column'])
    cur.execute(sql, values)
    results = cur.fetchall()
    return results

def getGenre(subjecttype):
    '''Given a subject type from the random template, generate a random genre term and random subject term of that subject type.
    Returns a list of tuples.'''
    genre = randomGenre()
#     if len(subjecttypes) == 1:
    subjectlist = getDistinct(genre, subjecttype)
    #there may not be any subjects for any of the items of the random genre, so keep trying until you find records with both.
    if len(subjectlist) > 0:
        randosubject = random.choice(subjectlist)
        print randosubject
        genres = getOneSubject(genre, randosubject, subjecttype)
        if genres > 0:
            return (genre, randosubject)
        else:
            return getGenre(subjecttype)
    else:
        return getGenre(subjecttype)
        
def buildClassmark(subject):  
    letters = string.ascii_letters
    #set values of possible classmark parts
    dewey = str(random.randint(100, 999))
    lcc = random.choice(letters).upper() + random.choice(letters).upper()
    cutter = ' ' + subject[:3]
    colon = random.choice(letters).upper() + str(random.randint(0,9))
    lower = random.choice(letters).lower()
    upper = ''.join(random.sample(letters, 2)).upper()
    digit = str(random.randint(0,9))
    #list of possible separators
    separators = '...:,*+'
    #select number of classmark parts to use and select random sample
    numparts = random.randint(2,3)
    classparts = random.sample([dewey, lcc, colon, lower, digit], numparts)
    #number of separators should be one less than classmark parts, but should end with a space
    sepparts = numparts-1
    seps = random.sample(separators, sepparts)
    seps.append(' ')
    #optional cutter
    numcutter = random.randint(0,1)
    #zip together classmark parts and separators and convert to string, strip trailing space
    zipped = [item for sublist in zip(classparts,seps) for item in sublist]
    classmark = ''.join(zipped).strip()
    if numcutter > 0:
        classmark = classmark + cutter
    return classmark

def composeTweet(genre, template):
    '''Fill out the random template for the tweet text and create a canned search based on the randomly selected terms. Concatenate
    both to compose the full tweet. '''
    print genre
    #make a list ot terms, also strip anything after ' -- ' for each term
    values = [i[0].partition(' -- ')[0] for i in genre]
    genreterm = values
    #zip together the terms and their corresponding types into a list of tuples
    subjects = zip(genreterm, list(template[1]))
    #create tweet text
    templatevalues = [s[0].encode('utf-8', 'ignore') for s in subjects]
    tweettext = template[0].format(templatevalues[0], templatevalues[1]).title()
    #create url
    queries = ['&filters[{0}]={1}'.format(s[1], s[0].encode('utf-8', 'ignore').replace(' ', '%20')) for s in subjects]
    queries = ''.join(queries)
    baseurl = 'http://digitalcollections.nypl.org/search/index?filters[rights]=pd'
    url = baseurl + queries
    classmark = buildClassmark(templatevalues[1])
    tweet = classmark + ' | ' + tweettext + url
    return tweet
    
def genrebotTweet():
    '''Generate a genrebot tweet text'''
    template = random.choice(templates)
    subjecttype = types[template[1][1]]
    genre = getGenre(subjecttype)
    tweet = composeTweet(genre, template)
    return tweet
  
def connect():
    '''Connect to Twitter'''
    api = twitter.Api(consumer_key=MY_CONSUMER_KEY,
                          consumer_secret=MY_CONSUMER_SECRET,
                          access_token_key=MY_ACCESS_TOKEN_KEY,
                          access_token_secret=MY_ACCESS_TOKEN_SECRET)
    return api  

if __name__ == '__main__':
    try:
        tweet = genrebotTweet()
        if DEBUG == False:
            api = connect()
            status = api.PostUpdate(tweet)
        else:
            print tweet
    except:
        exit()
