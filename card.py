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

    def __init__(self, names, uris, price, colour_id = None):
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
                colour = discord.Colour.from_rgb(*self.colours[self.colour_id[0]])

            embeds = [discord.Embed(title = self.name, description = self.price, colour = colour).set_thumbnail(url = self.uri)]
            if self.dfc:
                embeds.append(discord.Embed(title = self.back_name, colour = colour).set_thumbnail(url = self.back_uri))
            return embeds
        else:
            embeds = [discord.Embed(title = self.name, description = self.price).set_thumbnail(url = self.uri)]
            if self.dfc:
                embeds.append(discord.Embed(title = self.back_name).set_thumbnail(url = self.back_uri))
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
