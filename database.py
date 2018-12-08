import sqlite3 as sqlite # Database
from sqlite3 import Error # Database error handling
from random import randint # Get random xkcd
from utilities import log_message # Log events

class Database:
    def __init__(self,db_file):
        try:
            self.connection=sqlite.connect(db_file)
            self.cursor=self.connection.cursor()
            self.cursor.execute('CREATE TABLE IF NOT EXISTS xkcds(id INTEGER PRIMARY KEY, name TEXT, uri TEXT, alt TEXT);')
        except Error as e:
            log_message('xkcd database error: '+str(e))
            self.connection=None
            self.cursor=None

    def save(self):
        self.connection.commit()

    def close(self):
        self.cursor.close()
        self.connection.close()

    def count(self):
        self.cursor.execute(f'SELECT COUNT(*) FROM xkcds;') # Number of rows in xkcd table
        return self.cursor.fetchone()[0]

    def insert_xkcd(self,xkcd): # Add an xkcd object to the database
        self.cursor.execute(f"INSERT INTO xkcds VALUES({xkcd.idno},'{xkcd.name}','{xkcd.uri}','{xkcd.alt}');")
        self.save()
    
    def get_list(self):
        self.cursor.execute(f'SELECT name FROM xkcds;')
        return [item[0] for item in self.cursor.fetchall()]

    def get_xkcd(self,name):
        self.cursor.execute(f"SELECT name,uri,alt FROM xkcds WHERE name='{name}';")
        return interpret(self.cursor.fetchone())
        
    def get_random(self): # Get a random xkcd
        self.cursor.execute('SELECT max(id) FROM xkcds;') # The db fills back from the newest
        newest=self.cursor.fetchone()[0] # So we'll have issues if we try to call from the full range
        comic=randint(newest-self.count(),newest) # Pick a random number from count to the number of xkcds
        self.cursor.execute(f'SELECT name,uri,alt FROM xkcds WHERE id={str(comic)};') # Grab the xkcd with this id
        try:
            return interpret(self.cursor.fetchone())
        except TypeError: # In the event we don't have this comic for whatever reason a TypeError is thrown due to a NoneType. We'll just re-roll
            log_message('Missing xkcd #'+str(comic))
            return self.get_random()

    def get_newest(self):
        self.cursor.execute('SELECT name,uri,alt,max(id) FROM xkcds;') # Grab the xkcd with the maximum id, as they are numbered sequentially
        return interpret(self.cursor.fetchone())

    def get_id(self,idno): # Get an xkcd from id
        self.cursor.execute(f'SELECT name,uri,alt FROM xkcds WHERE id={idno};')
        data=self.cursor.fetchone()
        if data: # If we have the xkcd with this id
            return interpret(data)
        else: # Otherwise, show 404 image
            return self.get_xkcd('not available')


def interpret(data):
    name=repair_string(data[0])
    name=capitalise_name(name)
    uri=data[1]
    alt=repair_string(data[2])
    return name,uri,alt

def repair_string(string): # Replace the ' and " placeholders in alt text with appropriate characters
    return string.replace('&#39;',"'").replace('&quot;','"') 

def capitalise_name(name): # Capitalise a comic name
    cap_name=''
    for i in range(0,len(name)):
        if i==0 or name[i-1]==' ':
            cap_name+=name[i].upper()
        else:
            cap_name+=name[i]
    return cap_name
