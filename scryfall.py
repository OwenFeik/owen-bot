import requests # Grab card data from scryfall
import re # Find queries in a message
from card import Card # Pass objects to the bot
from random import choice, shuffle # used to return a random sample of suggestions

# A query object allows the bot to prearrange api calls and then execute them as necessary
class Query():
    def __init__(self,query=None,ed=None,msg=None):
        self.query=query
        self.ed=ed
        self.msg=msg
        self.card=None

    def resolve(self):
        if self.query=='random':
            if self.ed:
                found=get_random_from_set(self.ed)
                if found:
                    self.card=found
                else: # Returns false if set doesn't exist
                    self.msg=f'I\'m afraid I couldn\'t find edition \'{self.ed}\'.'
            else:
                self.card=get_random_card()
        elif self.query=='best card' or self.query=='the best card':
            self.card = get_fuzzy(choice(['Kalonian Hydra', 'Mystic Remora', 'Faithless Looting']))
        else:
            if self.ed: # If the query specified an edition
                found=get_printing(self.query,self.ed)
                if found: # Found is either False, meaning we found nothing
                    if type(found)==str: # str meaning we found some alternatives
                        self.msg=found
                    else: # Or a Card meaning we found the card
                        self.card=found
                else: # We found nothing
                    self.msg=f'I\'m afraid I couldn\'t find \'{capitalise(self.query)}\' in \'{self.ed}\'.'
            else:
                found=get_fuzzy(self.query)
                if found:
                    self.card=found
                else: # If we didn't find the card, look for alternatives
                    suggs=get_suggs(self.query)
                    if suggs:
                        self.msg=suggs
                    else:
                        self.msg=f'I\'m afraid I couldn\'t find \'{capitalise(self.query)}\'.'
    
    @property
    def found(self):
        if not self.card and not self.msg:
            self.resolve()

        if self.card:
            return self.card
        elif self.msg:
            return self.msg
        else: #If we don't have a card or a message, there's a problem
            return f'Oops, something went wrong when I was looking for {capitalise(self.query)}. Let Owen know!'


# Return query objects for each card found in the message
def get_queries(message):
    queries=[]
    for q in re.findall('\[[^\[\]]+\]',message): # Grab all [card tags]
        q=q.replace('[','').replace(']','') # Remove the [] so we can work with the name and set 
        if q=='': # If this search is blank, just ignore it
            continue
        elif '|' in q: # If it has a set filter
            if q.count('|')>1: # Only 1 set filter allowed
                queries.append(Query(msg='Multiple sets specified, when only one is allowed. Please try again.'))
            else:
                q=q.split('|') # Divide into name (q[0]) and set (q[1])
                if not '' in q: # If we have both a name and a set
                    queries.append(Query(q[0],q[1]))
                else:
                    if q[0]=='': # If we only have a set grab a random card from that set
                        queries.append(Query('random',q[1]))
                    else: # If we have no set, just search for the card
                        queries.append(Query(q[0]))
        else:
            queries.append(Query(q)) # Everything is normal, just query for the name

    return queries                    

# Conduct all necessary api calls to return uris immediately
def get_cards(message):
    return [query.found for query in get_queries(message)]

#Get uri of a cardname query
def get_fuzzy(query):
    request='https://api.scryfall.com/cards/named?fuzzy='+query.replace(' ', '+') #Use fuzzy for partial matching
    r=requests.get(request).json() #Get the response as a dictionary
    if 'status' in r and r['status']==404: #If no card found, return false
        return False
    
    return Card.from_scryfall_response(r)

#Get uri of a specific printing of card
def get_printing(query,ed):
    request=f'https://api.scryfall.com/cards/search?q=e%3D{ed}+'+query.replace(' ','+') #Search for cards in specificied ed
    r=requests.get(request).json() #Get data as dictionary
    if 'status' in r and r['status']==404: #If card doesn't exist
        return False #We return a few data types to save on api calls
    elif len(r['data'])>1: #If there are more than 1 matches
        data=[r['data'][i]['name'] for i in range(0,len(r['data']))] #List of card names to print as suggestions
        if len(data)>5: #If there are more than 5 suggestions
            shuffle(data)
            data=data[0:5] #Pick 5 at random
            data.sort()
        msg=f"I couldn't find {capitalise(query)} in {ed.upper()}. Maybe you meant:\n\n" # Make a string for the suggestions
        for sugg in data:
            msg+='\t'+sugg+'\n'
        return msg
    else:
        return Card.from_scryfall_response(r['data'][0])

#Get a random card uri
def get_random_card():
    request='https://api.scryfall.com/cards/random' #Information of a random card
    r=requests.get(request).json() #Get data as json
    return Card.from_scryfall_response(r)

#Get a random card froma set
def get_random_from_set(ed):
    request='https://api.scryfall.com/cards/random?q=e%3D'+ed #Provide ed to get random card from
    r=requests.get(request).json() #Get as dict
    if 'status' in r and r['status']==404: #This means the set wasn't found
        return False
    else: #We found a card
        return Card.from_scryfall_response(r)

#Get suggestions similar to a card name
def get_suggs(query):
    request='https://api.scryfall.com/cards/search?q='+query.replace(' ','+') #Search for the card
    r=requests.get(request).json() #Get data as json
    if 'status' in r and r['status']==404:  #If card not found return false
        return False

    data=[r['data'][i]['name'] for i in range(0,len(r['data']))]
    if len(data)>5: #If there are more than 5 suggestions
        shuffle(data)
        data=data[0:5] #Pick 5 at random
        data.sort()

    msg=f"Couldn't find {capitalise(query)}. Maybe you meant:\n\n" 
    for sugg in data:
        msg+='\t'+sugg+'\n'
    
    return msg

#Capitalise a card name
def capitalise(name):
    out=''
    for i in range(0,len(name)): #For each character
        if (name[i].isalnum() and not name[i-1].isalnum()) or i==0: #If it's a letter preceded by a non-letter
            out+=name[i].capitalize() #Add the capital version to the out string
        else: #Otherwise, just normal character
            out+=name[i] #To out string
    return out

# Remove spaces from the start and end of a string
def clean_query(string):
    if string=='':
        return string
    if string[0]==' ':
        string=string[1:] 
    if string[len(string)-1]==' ':
        string=string[:len(string)-1]
    return string
