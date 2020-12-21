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

    def get_embeds(self, style='thumbnail'):
        embed = discord.Embed(
            title=self.name, 
            description=self.price, 
            colour=self.get_embed_colour()
        )

        if style == 'thumbnail':
            return [embed.set_thumbnail(url=self.uri)]
        elif style == 'full':
            return [embed.set_image(url=self.uri)]

class DoubleFacedCard(Card):
    def __init__(self, names, uris, price, colour_id):
        super().__init__(names[0], uris[0], price, colour_id)

        self.back_name = names[1]
        self.back_uri = names[1]

        self.back_face = Card(
            self.back_name,
            self.back_uri,
            '',
            self.colour_id
        )

    def get_embeds(self, style='thumbnail'):
        embeds = super().get_embeds(style)
        embeds.extend(self.back_face.get_embeds(style))
        return embeds

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

class CardList():
    def __init__(self, cards, message):
        self.cards = cards
        self.message = message

    def get_embed(self):
        return discord.Embed(
            title='Results',
            description=self.message
        )

    @staticmethod
    def from_scryfall_response(data, message):
        return CardList(
            [card_from_scryfall_response(c) for c in data],
            message
        )

class ScryfallRequest():
    BASE_URL = 'https://api.scryfall.com/cards/'
    QUERIES = {
        'name': 'search?q={}',
        'name_ed': 'search?q=e%3D{}+{}',
        'fuzzy': 'named?fuzzy={}',
        'random': 'random',
        'random_ed': 'random?q=e%3D{}',
        'search': 'search?q={}'
    }
    BEST_CARDS = [
        'Faithless Looting',
        'Kalonian Hydra',
        'Mystic Remora',
        'Smuggler\'s Copter',
        'Niv-Mizzet Reborn'
    ]
    ERROR_MESSAGE = 'Something went wrong and I failed to {}'
    FAILURE_MESSAGE = 'I\'m afraid I couldn\'t find {}'
    SUGGEST_MESSAGE = FAILURE_MESSAGE + '. Perhaps you meant one of these?'

    def __init__(self, query, ed, is_search=False, embed_style='thumbnail'):
        self.query = query
        self.ed = ed
        self.result = None
        self.mode = None
        self.is_search = is_search
        self.embed_style = embed_style

    def perform_request(self, query, failure_message, suggest=None):
        self.result = failure_message

        resp = requests.get(ScryfallRequest.BASE_URL + query).json()
        if resp.get('status') == 404:
            if suggest is not None:
                resp = requests.get(
                    ScryfallRequest.QUERIES['search'].format(self.query)
                ).json()

                if resp.get('status') == 404:
                    return self.result
                else:
            else:
                return self.result

        data_type = resp.get('object')

        if data_type == 'card':
            self.result = card_from_scryfall_response(resp)
        elif data_type == 'list':
            cards = resp['data']

            if len(cards) == 1:
                self.result = card_from_scryfall_response(cards[0])
            else:
                message = suggest if suggest is not None else ''
                self.result = CardList.from_scryfall_response(cards, message)

        return self.result

    def get_random_card(self):
        if self.ed:
            return self.perform_request(
                ScryfallRequest.QUERIES['random_ed'].format(self.ed),
                f'I couldn\'t find edition "{self.ed}".'
            )
        return self.perform_request(
            ScryfallRequest.QUERIES['random'],
            ScryfallRequest.ERROR_MESSAGE.format('find a random card.')
        )
    
    def get_best_card(self):
        return self.perform_request(
            ScryfallRequest.QUERIES['fuzzy'].format(
                random.choice(ScryfallRequest.BEST_CARDS)
            ),
            ScryfallRequest.ERROR_MESSAGE.format('find the best card.')
        )

    def get_card_edition(self):
        query_string = f'"{self.query}" in "{self.ed}"'
        return self.perform_request(
            ScryfallRequest.QUERIES['name_ed'].format(self.ed, self.query),
            ScryfallRequest.FAILURE_MESSAGE.format(query_string),
            ScryfallRequest.SUGGEST_MESSAGE.format(query_string)
        )

    def get_card(self):
        return self.perform_request(
            ScryfallRequest.QUERIES['fuzzy'].format(self.query),
            ScryfallRequest.FAILURE_MESSAGE.format(self.query),
            ScryfallRequest.SUGGEST_MESSAGE.format(self.query)
        )

    def get_search_results(self):
        return self.perform_request(
            ScryfallRequest.QUERIES['search'].format(self.query),
            ScryfallRequest.FAILURE_MESSAGE.format('any cards matching this search.')
        )

    def resolve(self):
        if self.is_search:
            self.get_search_results()
        elif self.query.lower() == 'random':
            self.get_random_card()
        elif self.query.lower() in ['best card', 'the best card']:
            self.get_best_card()
        else:
            self.get_card()

        return self.result

    def get_result(self):
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
        r'\[(?P<prefix>(\?!|!\?|[\?!])(?!\]))?'
        r'(?P<query>[\w ,.:!?&\'\/\-\"\(\)]+)(\|(?P<ed>[a-z0-9 \-]+))?\]',
        flags=re.IGNORECASE
    ):
        prefix = q.group('prefix')
        if prefix is None:
            is_search = False
            embed_style = 'thumbnail'
        else:
            embed_style = 'full' if '!' in prefix else 'thumbnail'
            is_search = True if '?' in prefix else False

        query = q.group('name').strip()
        ed = q.group('ed').strip()

        queries.append(ScryfallRequest(query, ed, is_search, embed_style))

    return queries                    
