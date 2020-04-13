import requests # Pull raw data from xkcd website
import re # Parse xkcd html for relevant data
import asyncio # More efficiently collect xkcds
import discord
from difflib import SequenceMatcher # Get similarly named comics
from database import Database # Database used to hold information on comics
from utilities import log_message # Send messages in the log

class xkcd():
    def __init__(self,idno=0,name='',uri='',alt=''):
        self.idno=idno
        self.name=name
        self.uri=uri
        self.alt=alt

    @staticmethod
    def from_raw_name(name):
        temp=''
        strip=xkcd()
        for c in name:
            if c=='/' and not strip.idno: # / means the comic number has ended. Some titles also have a /, so ignore / after the first
                strip.idno=temp
                temp=''
            elif c=='>': # > is the beginning of the name
                temp=''
            elif c=='<': # < is the end of the name
                strip.name=temp.lower().replace('\'','&#39;') # &#39; is a placeholder for ' for it to work in the database
            else:
                temp+=c
        return strip
    
    def get_uri_alt(self):
        r=requests.get('http://xkcd.com/'+self.idno) # Grab source of comic's page
        src=r.content.decode() # Decode from raw binary
        uri=re.findall('https://imgs.xkcd.com/comics/[a-z0-9._-]+\n',src) # Pull the permalink
        if uri:
            uri=uri[0]
            uri=uri[:len(uri)-1] # Cut off the newline character
            self.uri=uri
        alt=re.findall('<img src="[a-z0-9/._-]+" title="[^"]+"',src) # Pull the alt text
        if alt:
            alt=re.findall('title="[^"]+"',alt[0])[0] # Grab the title section of the line
            alt=alt[7:len(alt)-1] # Trim down to just the text
            self.alt=alt
        
        return self

def get_xkcd(query):
    db=Database('resources/bot.db')
    query=query.lower()
    if query=='random':
        xkcd_tuple = db.get_random_xkcd()
    elif query in ['new','newest']:
        xkcd_tuple = db.get_newest_xkcd()
    elif query.isnumeric():
        xkcd_tuple = db.get_id(query)
    elif list_check(query): # If there is a comic of this name
        xkcd_tuple = db.get_xkcd(query)
    else:
        xkcd_tuple = db.get_xkcd(sugg(query)) # Otherwise find a similar one
    return get_embed(xkcd_tuple)

def get_embed(xkcd_tuple):
    e = discord.Embed(title = xkcd_tuple[0])
    e.set_image(url = xkcd_tuple[1])
    e.set_footer(text = xkcd_tuple[2]) # Alt text
    return e

async def update_db():
    current=get_list() # list of comics currently in the database
    db=Database('resources/bot.db')
    r=requests.get('https://xkcd.com/archive/') # Grab the archive page, a list of all xkcd comics
    raw_names=re.findall('[0-9]{0,4}/" title="[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}">[^<>]+<',r.content.decode()) # Grab sections of html containing names
    xkcds=[]
    for name in raw_names:
        strip=xkcd.from_raw_name(name) # Create an xkcd object from the raw data
        if not strip.name in current: # We only need to add comics we don't have
            xkcds.append(strip)

    loop=asyncio.get_event_loop() # Object used to execute requests with asyncio
    calls=[loop.run_in_executor(None,strip.get_uri_alt) for strip in xkcds] # Create a call for each strip
    for call in calls: # Run calls
        strip=await call # By using async, mitigate waiting on xkcd server
        db.insert_xkcd(strip) # Add to db
        log_message(f'Added new xkcd comic {strip.name}.')
    
    db.close()
    log_message('xkcd database up to date!')

def get_list(): # Grab the list of names of xkcds
    db=Database('resources/bot.db')
    return db.get_xkcd_list()

def list_check(query): # Ensure we have the xkcd of name 'query'
    if query in get_list():
        return True
    return False

def sugg(query):
    best=0.5 # Suggestions must be at least 50% similar
    best_name='not available' # the comic "not available" is our 404 message
    for name in get_list():
        r=SequenceMatcher(a=name,b=query).ratio()
        if r>best:
            best=r
            best_name=name
    return best_name

# Allow this file to be run with a cron job or similar
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(update_db())
