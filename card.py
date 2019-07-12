from discord import Embed # Used to make messages to send
from utilities import extend_string # Ensure multiple embeds look nice

class Card:
    def __init__(self, names, uris, price):
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
        embeds = [Embed(title = self.name, description = self.price).set_thumbnail(url = self.uri)]
        if self.dfc:
            embeds.append(Embed(title = self.back_name).set_thumbnail(url = self.back_uri))
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

        return Card(names, uris, price)
