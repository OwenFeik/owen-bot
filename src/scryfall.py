import random # used to return a random sample of suggestions
import re # Find queries in a message

import requests # Grab card data from scryfall
import discord

import utilities

class Card:
    EMBED_COLOURS = {
        'W': discord.Colour.from_rgb(248, 231, 185),
        'U': discord.Colour.from_rgb(14, 104, 171),
        'B': discord.Colour.from_rgb(21, 11, 0),
        'R': discord.Colour.from_rgb(211, 32, 42),
        'G': discord.Colour.from_rgb(0, 115, 62),
        'M': discord.Colour.from_rgb(199, 161, 100),
        'C': discord.Colour.from_rgb(209, 213, 214)
    }

    def __init__(self, name, uri, price, colour_id):
        self.name = name
        self.uri = uri
        self.price = price

        self.colour_id = colour_id if colour_id else []

    def get_embed_colour(self):
        if len(self.colour_id) > 1:
            return Card.EMBED_COLOURS['M']
        elif len(self.colour_id) == 0:
            return Card.EMBED_COLOURS['C']
        else:
            return Card.EMBED_COLOURS[self.colour_id[0]]

    def get_embeds(self):
        return [
            discord.Embed(
                title=self.name, 
                description=self.price, 
                colour=self.get_embed_colour()
            ).set_thumbnail(url=self.uri)
        ]

class DoubleFacedCard(Card):
    def __init__(self, names, uris, price, colour_id):
        super().__init__(names[0], uris[0], price, colour_id)

        self.back_name = names[1]
        self.back_uri = names[1]

    def get_embeds(self):
        return [
            discord.Embed(
                title=self.name,
                description=self.price,
                colour=self.get_embed_colour()
            ).set_thumbnail(url=self.uri),
            discord.Embed(
                title=self.back_name,
                colour=self.get_embed_colour()
            ).set_thumbnail(url=self.uri)
        ]

def get_price_string(data):
    price = data['prices']['usd']
    if price is None:
        price = data['prices']['usd_foil']
        if price is None:
            return 'Price N/A'
        return f'${price} (foil)'
    return f'${price}'

def card_from_scryfall_response(data):
        price = get_price_string(data)
        colour_id = data['color_identity']

        if 'card_faces' in data and 'image_uris' in data['card_faces'][0]:
            names = [data['card_faces'][i]['name'] for i in range(0,2)]
            uris = [data['card_faces'][i]['image_uris']['normal'] \
                for i in range(0, 2)]
            return DoubleFacedCard(names, uris, price, colour_id)
        else:
            name = data['name']
            uri = data['image_uris']['normal']
            return Card(name, uri, price, colour_id)

class ScryfallRequest():
    BASE = 'https://api.scryfall.com/cards/'
    MODES = {
        'random': 'random',
        'random_ed': 'random?q=e%3D{}',
        'name': 'search?q={}',
        'name_ed': 'search?q=e%3D{}+{}',
        'fuzzy': 'named?fuzzy={}',
    }
    BEST_CARDS = [
        'Faithless Looting',
        'Kalonian Hydra',
        'Mystic Remora',
        'Smuggler\'s Copter',
        'Niv-Mizzet Reborn'
    ]

    def __init__(self, query, ed):
        self.query = query
        self.ed = ed
        self.result = None

    def perform_request(self, url, failure_message):
        self.result = failure_message

        resp = requests.get(url).json()
        if resp.get('status') == 404:
            return self.result

        data = resp.get('data')


    def get_random_card(self):
        if self.ed:
            return self.perform_request(
                ScryfallRequest.MODES['random_ed'].format(self.ed),
                f'I couldn\'t find edition "{self.ed}".'
            )
        return self.perform_request(
            ScryfallRequest.MODES['random'],
            'Something went wrong and I failed to find a random card.'
        )
    
    def get_best_card(self):
        return self.perform_request(
            ScryfallRequest.MODES['fuzzy'].format(
                random.choice(ScryfallRequest.BEST_CARDS)
            ),
            'Something went wrong and I failed to find the best card.'
        )

    def get_card_edition(self):
        return self.perform_request(
            ScryfallRequest.MODES['name_ed'].format(self.ed, self.query),
            f'I\'m afraid I couldn\'t find "{self.query}" in "{self.ed}".'
        )

    def get_card(self):
        return self.perform_request(
            ScryfallRequest.MODES['fuzzy'].format(self.query),
            f'I\'m afraid I couldn\'t find "{self.query}".'
        )

    def resolve(self):
        if self.query == 'random':
            self.get_random_card()
        elif self.query in ['best card', 'the best card']:
            self.get_best_card()
        elif self.ed:
            self.get_card_edition()
        else:
            self.get_card()

        return self.result

    @property
    def found(self):
        if self.result is None:
            self.resolve()

        if self.result is None:
            utilities.log_message(
                'Failed to find card while searching scryfall for '
                f'"{self.query}".'
            )
            return 'Oops, something went wrong when I was looking for ' + \
                f'"{utilities.capitalise(self.query)}". Let Owen know!'

        return self.result

# Return query objects for each card found in the message
def get_queries(message):
    queries = []
    message = re.sub(r'(?<!\\)`.*(?<!\\)`', '', message)
    for q in re.finditer(
        r'\[(?P<name>[\w ,.:!?&\'\/\-\"\(\)]+)(\|(?P<ed>[a-z0-9 \-]+))?\]',
        message.lower()
    ):
        name = q.group('name')
        ed = q.group('ed')

        queries.append(ScryfallRequest(name, ed))

    return queries                    
