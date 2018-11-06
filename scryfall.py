import requests
from card import Card

#Get uri of a cardname query
def get_uri(query):
    request='https://api.scryfall.com/cards/named?fuzzy='+query.replace(' ', '+') #Use fuzzy for partial matching
    r=requests.get(request).json() #Get the response as a dictionary
    if 'status' in r and r['status']==404: #If no card found, return false
        return False
    elif r['layout']=='transform' or r['layout']=='double_faced_token': #If DFC get both faces
        names=[r['card_faces'][i]['name'] for i in range(0,2)]
        uris=[r['card_faces'][i]['image_uris']['normal'] for i in range(0,2)]
        price=r.get('usd')
        return Card(names,uris,price)
    
    names=[r['name']]
    uris=[r["image_uris"]["normal"]]
    price=r.get('usd')
    return Card(names,uris,price) #If normal card, get image


#Get uri of a specific printing of card
def get_printing(query,ed):
    request=f'https://api.scryfall.com/cards/search?q=e%3D{ed}+'+query.replace(' ','+') #Search for cards in specificied edition
    r=requests.get(request).json() #Get data as dictionary
    if 'status' in r and r['status']==404: #If card doesn't exist
        return 'fail',False #We return a few data types to save on api calls
    elif len(r['data'])>1: #If there are more than 1 matches
        return 'suggs',[r['data'][i]['name'] for i in range(0,len(r['data']))] #List of card names to print as suggestions
    else:
        card=r['data'][0]
        if card['layout']=='transform' or card['layout']=='double_faced_token': #If its a DFC get both sides
            names=[card['card_faces'][i]['name'] for i in range(0,2)]
            uris=[card['card_faces'][i]['image_uris']['normal'] for i in range(0,2)]
            price=card['usd']

            return 'card',Card(names,uris,price)
        names=[card['name']]
        uris=[card['image_uris']['normal']]
        price=card['usd']
        return 'card',Card(names,uris,price) #Normal card, give card image

#Get a random card uri
def get_random_uri():
    request='https://api.scryfall.com/cards/random' #Information of a random card
    r=requests.get(request).json() #Get data as json
    names=[r['name']]
    uris=[r['image_uris']['normal']]
    price=r.get('usd')
    return Card(names,uris,price) #Return the uri of the image

#Get a random card froma set
def get_random_from_set(ed):
    request='https://api.scryfall.com/cards/random?q=e%3D'+ed #Provide edition to get random card from
    r=requests.get(request).json() #Get as dict
    if 'status' in r and r['status']==404: #This means the set wasn't found
        return False
    else: #We found a card
        names=[r['name']]
        uris=[r['image_uris']['normal']]
        price=r.get('usd')
        return Card(names,uris,price) #Image of the card

#Get suggestions similar to a card
def get_similar(query):
    request='https://api.scryfall.com/cards/search?q='+query.replace(' ','+') #Search for the card
    r=requests.get(request).json() #Get data as json
    if 'status' in r and r['status']==404:  #If card not found return false
        return False
    return [r['data'][i]['name'] for i in range(0,len(r['data']))] #Otherwise, return a list of similar names
