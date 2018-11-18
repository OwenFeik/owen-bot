import requests # Pull raw data from xkcd website
import re # Parse xkcd html for relevant data
from difflib import SequenceMatcher # Get similarly named comics
from database import Database # Database used to hold information on comics

def get_xkcd(query):
    db=Database('xkcd.db')
    query=query.lower()
    if list_check(query): # If there is a comic of this name
        return db.get_xkcd(query)
    return db.get_xkcd(sugg(query)) # Otherwise find a similar one

def update_db():
    current=get_list() # list of comics currently in the database
    db=Database('xkcd.db')
    r=requests.get('https://xkcd.com/archive/') # Grab the archive page, a list of all xkcd comics
    raw_names=re.findall('[0-9]{0,4}/" title="[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}">[a-zA-Z ]+<',r.content.decode()) # Grab sections of html containing names
    for name in raw_names:
        temp=''
        data=[]
        for c in name:
            if c=='/': # / means the comic number has ended
                data.append(temp)
                temp=''
            elif c=='>': # > is the beginning of the name
                temp=''
            elif c=='<': # < is the end of the name
                data.append(temp.lower())
            else:
                temp+=c

        if not (data[1] in current): # If we don't have this comic
            r=requests.get('https://xkcd.com/'+str(data[0])) # Get the individual comic page
            src=r.content.decode()
            uri=re.findall('https://imgs.xkcd.com/comics/[a-z_.]+\n',src) # Pull the permalink
            if uri:
                uri=uri[0]
                uri=uri[:len(uri)-1] # Cut off the newline character
                data.append(uri)
            else:
                data.append('')
            alt=re.findall('<img src="[a-z/._]+" title="[^"]+"',src) # Pull the alt text
            if alt:
                alt=re.findall('title="[^"]+"',alt[0])[0] # Grab the title section of the line
                alt=alt[7:len(alt)-1] # Trim down to just the text
                data.append(alt)
            else:
                data.append('')
            db.insert_xkcd(data[0],data[1],data[2],data[3]) # Add the (id,name,uri) to the database
            print(f'Added new xkcd comic {data[1]}.')
    db.close()

def get_list():
    db=Database('xkcd.db')
    return db.get_list()

def list_check(query):
    if query in get_list():
        return True
    return False

def sugg(query):
    best=0.5 # Suggestions must be at least 50% similar
    best_name='not available' # the comic not available is our 404 message
    for name in get_list():
        r=SequenceMatcher(a=name,b=query).ratio()
        if r>best:
            best=r
            best_name=name
    return best_name
