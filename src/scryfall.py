import random # used to return a random sample of suggestions
import re # Find queries in a message

import requests # Grab card data from scryfall
import discord

class Card:
    colours = {
        'W': (248, 231, 185),
        'U': (14, 104, 171),
        'B': (21, 11, 0),
        'R': (211, 32, 42),
        'G': (0, 115, 62),
        'M': (199, 161, 100),
        'C': (209, 213, 214)
    }

    def __init__(self, names, uris, price, colour_id=None):
        self.names = names
        self.uris = uris
        if len(self.uris) > 1:
            self.dfc = True
        else:
            self.dfc = False
        if price:
            self.price = '$' + price
        else:
            self.price = 'Price N/A'

        self.colour_id = colour_id

    @property
    def name(self):
        return self.names[0]
    
    @property
    def uri(self):
        return self.uris[0]

    @property
    def back_uri(self):
        if self.dfc:
            return self.uris[1]
        else:
            return False
            
    @property
    def back_name(self):
        if self.dfc:
            return self.names[1]
        else:
            return False

    @property
    def embed(self):
        if self.colour_id:
            if len(self.colour_id) > 1:
                colour = discord.Colour.from_rgb(*self.colours['M'])
            elif len(self.colour_id) < 1:
                colour = discord.Colour.from_rgb(*self.colours['C'])
            else:
                colour = discord.Colour.from_rgb(
                    *self.colours[self.colour_id[0]]
                )

            embeds = [discord.Embed(
                title = self.name, 
                description = self.price, 
                colour = colour
            ).set_thumbnail(url = self.uri)]

            if self.dfc:
                embeds.append(discord.Embed(
                    title = self.back_name, 
                    colour = colour
                ).set_thumbnail(url = self.back_uri))
            return embeds
        else:
            embeds = [discord.Embed(
                title = self.name, 
                description = self.price
            ).set_thumbnail(url = self.uri)]
            
            if self.dfc:
                embeds.append(discord.Embed(
                    title = self.back_name
                ).set_thumbnail(url = self.back_uri))
            
            return embeds

    @staticmethod
    def from_scryfall_response(card):
        if card['layout'] in ['transform', 'double_faced_token']:
            names = [card['card_faces'][i]['name'] for i in range(0,2)]
            uris = [card['card_faces'][i]['image_uris']['normal'] for i in range(0,2)]
        else:
            names = [card['name']]
            uris = [card['image_uris']['normal']]

        price = card.get('prices').get('usd')
        colour_id = card['color_identity']

        return Card(names, uris, price, colour_id)

# A query object allows the bot to prearrange api calls and then execute them as necessary
class Query():
    def __init__(self, query=None, ed=None, msg=None):
        self.query = query
        self.ed = ed
        self.msg = msg
        self.card = None

    def resolve(self):
        if self.query == 'random':
            if self.ed:
                found = get_random_from_set(self.ed)
                if found:
                    self.card = found
                else: # Returns false if set doesn't exist
                    self.msg = \
                        f'I\'m afraid I couldn\'t find edition \'{self.ed}\'.'
            else:
                self.card = get_random_card()
        elif self.query == 'best card' or self.query == 'the best card':
            best_cards = [
                'Faithless Looting'
                'Kalonian Hydra',
                'Mystic Remora',
                'Smuggler\'s Copter'
            ]
            self.card = get_fuzzy(random.choice(best_cards))
        else:
            if self.ed: # If the query specified an edition
                found = get_printing(self.query, self.ed)
                if found: # Found is either False, meaning we found nothing
                    if type(found) == str: # str meaning we found some alternatives
                        self.msg = found
                    else: # Or a Card meaning we found the card
                        self.card = found
                else: # We found nothing
                    self.msg = 'I\'m afraid I couldn\'t find ' + \
                        f'"{capitalise(self.query)}" in "{self.ed}".'
            else:
                found = get_fuzzy(self.query)
                if found:
                    self.card = found
                else: # If we didn't find the card, look for alternatives
                    suggs = get_suggs(self.query)
                    if suggs:
                        self.msg = suggs
                    else:
                        self.msg = 'I\'m afraid I couldn\'t find ' + \
                            f'"{capitalise(self.query)}".'
    
    @property
    def found(self):
        if not self.card and not self.msg:
            self.resolve()

        if self.card:
            return self.card
        elif self.msg:
            return self.msg
        else: #If we don't have a card or a message, there's a problem
            return 'Oops, something went wrong when I was looking for ' + \
                f'"{capitalise(self.query)}". Let Owen know!'


# Return query objects for each card found in the message
def get_queries(message):
    queries = []
    for q in re.findall(r'\[[^\[\]]+\]', message): # Grab all [card tags]
        q = q.replace('[','').replace(']','') # Remove the [] so we can work with the name and set 
        if q == '': # If this search is blank, just ignore it
            continue
        elif '|' in q: # If it has a set filter
            if q.count('|') > 1: # Only 1 set filter allowed
                queries.append(Query(msg = 'Multiple sets specified, ' + \
                    'when only one is allowed. Please try again.'))
            else:
                q = q.split('|') # Divide into name (q[0]) and set (q[1])
                if not '' in q: # If we have both a name and a set
                    queries.append(Query(q[0].strip(), q[1].strip()))
                else:
                    if q[0] == '': # If we only have a set grab a random card from that set
                        queries.append(Query('random', q[1]))
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
    request = 'https://api.scryfall.com/cards/named?fuzzy=' + \
        query.replace(' ', '+') # Use fuzzy for partial matching
    
    r = requests.get(request).json() #Get the response as a dictionary
    if 'status' in r and r['status'] == 404: #If no card found, return false
        return False
    
    return Card.from_scryfall_response(r)

#Get uri of a specific printing of card
def get_printing(query, ed):
    request = f'https://api.scryfall.com/cards/search?q=e%3D{ed}+' + \
        query.replace(' ','+') #Search for cards in specificied ed
    r = requests.get(request).json() #Get data as dictionary
    if 'status' in r and r['status'] == 404: #If card doesn't exist
        return False #We return a few data types to save on api calls
    elif len(r['data']) > 1: #If there are more than 1 matches
        data = [r['data'][i]['name'] for i in range(0,len(r['data']))] #List of card names to print as suggestions
        if len(data) > 5: #If there are more than 5 suggestions
            random.shuffle(data)
            data = data[0:5] #Pick 5 at random
            data.sort()
        msg = f"I couldn't find {capitalise(query)} in {ed.upper()}. Maybe you meant:\n\n" # Make a string for the suggestions
        for sugg in data:
            msg += '\t' + sugg + '\n'
        return msg
    else:
        return Card.from_scryfall_response(r['data'][0])

#Get a random card uri
def get_random_card():
    request = 'https://api.scryfall.com/cards/random' #Information of a random card
    r = requests.get(request).json() #Get data as json
    return Card.from_scryfall_response(r)

#Get a random card froma set
def get_random_from_set(ed):
    request = 'https://api.scryfall.com/cards/random?q=e%3D' + ed #Provide ed to get random card from
    r = requests.get(request).json() #Get as dict
    if 'status' in r and r['status'] == 404: #This means the set wasn't found
        return False
    else: #We found a card
        return Card.from_scryfall_response(r)

#Get suggestions similar to a card name
def get_suggs(query):
    request = 'https://api.scryfall.com/cards/search?q=' + \
        query.replace(' ','+') #Search for the card
    r = requests.get(request).json() #Get data as json
    if 'status' in r and r['status'] == 404:  #If card not found return false
        return False

    data = [r['data'][i]['name'] for i in range(0, len(r['data']))]
    if len(data) > 5: #If there are more than 5 suggestions
        random.shuffle(data)
        data = data[0:5] #Pick 5 at random
        data.sort()

    msg = f"Couldn't find {capitalise(query)}. Maybe you meant:\n\n" 
    for sugg in data:
        msg += '\t'+sugg+'\n'
    
    return msg

#Capitalise a card name
def capitalise(name):
    name = name.strip().lower()
    name = name.replace(name[0], name[0].upper(), 1)
    skip = [
        'a',
        'an',
        'at',
        'and',
        'are',
        'but',
        'by',
        'for',
        'from',
        'not',
        'nor',
        'of',
        'or',
        'so',
        'the',
        'with',
        'yet'
    ]

    words = name.split(' ')
    for i in range(1, len(words)):
        c = words[i][0]
        if c.isalpha() and not words[i] in skip or i == len(words) - 1:
            words[i] = words[i].replace(c, c.upper(), 1)
    
    return ' '.join(words)
