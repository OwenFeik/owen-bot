import requests

def get_uri(query):
    request='https://api.scryfall.com/cards/named?fuzzy='+query.replace(' ', '+')
    r=requests.get(request)
    if 'status' in r.json() and r.json()['status']==404:
        return False
    return r.json()["image_uris"]["normal"]