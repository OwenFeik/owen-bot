import requests

def get_uri(query):
    request='https://api.scryfall.com/cards/named?fuzzy='+query.replace(' ', '+') #Use fuzzy for partial matching
    r=requests.get(request).json() #Get the response as a dictionary
    if 'status' in r and r['status']==404: #If no card found, return false
        return False
    elif r['layout']=='transform' or r['layout']=='double_faced_token': #If DFC get both faces
        return [r['card_faces'][i]['image_uris']['normal'] for i in range(0,2)]
    return [r["image_uris"]["normal"]] #If normal card, get image