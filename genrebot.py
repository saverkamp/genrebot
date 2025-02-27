import random
import twitter
import os
import psycopg2
import urlparse
import string
import requests
import math
from datetime import datetime

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
    '''Get one random genre from a list of weighted, distinct values from the db. Returns tuple for use in next query.'''
    #get list of all genres and their counts
    sql = ("select genre, count(genre) "
       "from genres "
       "group by genre;")
    cur.execute(sql)
    genres = [c for c in cur.fetchall()]
    #create new list of genres, weighting higher those with more record instances
    weightedgenres = []
    #round number of genre instances to nearest log and add respective number of times to genre list
    weights = {100000:25, 10000:15, 1000:5, 100:1, 10:1, 1:1}
    for g in genres:
        weight = int(10**math.ceil(math.log10(g[1])))
        to_add = [(g[0],)] * weights[weight]
        weightedgenres.extend(to_add)
    #choose one genre
    genre = random.choice(weightedgenres)
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
    separators = '....::*+'
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
    # make a list ot terms, also strip anything after ' -- ' for each term and replace
    # with * for wildcard search in url
    values = [i[0].replace(' -- ', '*').partition('*') for i in genre]
    values = [v[0]+v[1] for v in values]
    genreterm = values
    #zip together the terms and their corresponding types into a list of tuples
    subjects = zip(genreterm, list(template[1]))
    #create tweet text, stripping * for tweet text
    templatevalues = [s[0].encode('utf-8', 'ignore').replace('*', '') for s in subjects]
    tweettext = template[0].format(templatevalues[0], templatevalues[1])
    #create url
    queries = ['&filters[{0}]={1}'.format(s[1], s[0].encode('utf-8', 'ignore').replace(' ', '+')) for s in subjects]
    queries = ''.join(queries)
    baseurl = 'http://digitalcollections.nypl.org/search/index?filters[rights]=pd'
    url = baseurl + queries + '&keywords='
    #make sure the url returns results, otherwise return "Failed"
    if checkResults(url) == True:
        classmark = buildClassmark(templatevalues[1])
        tweet = classmark + ' | ' + tweettext + url
    else:
        tweet = 'Failed'
    return tweet

def checkResults(url):
    '''Check the search results page to make sure there's something there'''
    page = requests.get(url)
    if page.content.find('<div class="found">') != -1:
        results = True
    else:
        results = False
    return results
    
def genrebotTweet(tries=0):
    '''Generate a genrebot tweet text'''
    template = random.choice(templates)
    subjecttype = types[template[1][1]]
    genre = getGenre(subjecttype)
    tweet = composeTweet(genre, template)
    #only try 10 times at a url that returns results before giving up
    if tweet != 'Failed':
        return tweet
    else:
        if tries == 10:
            exit()
        else:
            tries += 1
            return genrebotTweet(tries)
  
def connect():
    '''Connect to Twitter'''
    api = twitter.Api(consumer_key=os.environ["MY_CONSUMER_KEY"],
                          consumer_secret=os.environ["MY_CONSUMER_SECRET"],
                          access_token_key=os.environ["MY_ACCESS_TOKEN_KEY"],
                          access_token_secret=os.environ["MY_ACCESS_TOKEN_SECRET"])
    print api.VerifyCredentials()
    return api  

if __name__ == '__main__':
    try:
        # hacky method to run this only every two hours
        if datetime.now().hour % 2 == 0:
            tweet = genrebotTweet()
            if os.environ["DEBUG"] == 'False':
                api = connect()
                status = api.PostUpdate(tweet)
                print status.text.encode('utf-8')
            else:
                print tweet
        else:
            exit()
    except:
        exit()
