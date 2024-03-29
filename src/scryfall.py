import random  # used to return a random sample of suggestions
import re

import requests  # Grab card data from scryfall
import discord

import commands
import utilities


class Card:
    EMBED_COLOURS = {
        "W": discord.Colour.from_rgb(248, 231, 185),
        "U": discord.Colour.from_rgb(14, 104, 171),
        "B": discord.Colour.from_rgb(21, 11, 0),
        "R": discord.Colour.from_rgb(211, 32, 42),
        "G": discord.Colour.from_rgb(0, 115, 62),
        "M": discord.Colour.from_rgb(199, 161, 100),
        "C": discord.Colour.from_rgb(209, 213, 214),
    }

    def __init__(
        self, name, uri, art_uri, price, colour_id, ed, embed_style="thumbnail"
    ):
        self.name = name
        self.uri = uri
        self.art_uri = art_uri
        self.price = price
        self.colour_id = colour_id if colour_id else []
        self.ed = ed
        self.embed_style = embed_style
        self.description = f"{self.ed} {self.price}"

    def __repr__(self):
        return (
            f"<Card name: {self.name} price: {self.price} uri: {self.uri} "
            f"ed: {self.ed}>"
        )

    def get_embed_colour(self):
        if len(self.colour_id) > 1:
            return Card.EMBED_COLOURS["M"]
        elif len(self.colour_id) == 0:
            return Card.EMBED_COLOURS["C"]
        else:
            return Card.EMBED_COLOURS[self.colour_id[0]]

    def set_embed_style(self, style):
        self.embed_style = style

    def get_embed(self, style=None):
        if style is not None:
            self.set_embed_style(style)

        if self.embed_style == "art":
            return discord.Embed(
                title=f"{self.name} ({self.ed})",
                colour=self.get_embed_colour(),
            ).set_image(url=self.art_uri)

        embed = discord.Embed(
            title=self.name,
            description=self.description,
            colour=self.get_embed_colour(),
        )

        if self.embed_style == "thumbnail":
            return embed.set_thumbnail(url=self.uri)
        elif self.embed_style == "full":
            return embed.set_image(url=self.uri)
        else:
            raise ValueError(f"Unknown card embed style: {self.embed_style}.")


class BackFace(Card):
    def __init__(self, name, uri, art_uri, front_face):
        super().__init__(
            name,
            uri,
            art_uri,
            "",
            front_face.colour_id,
            front_face.ed,
            front_face.embed_style,
        )
        self.front_face = front_face
        self.other_face = front_face
        self.description = ""


class DoubleFacedCard(Card):
    def __init__(
        self,
        names,
        uris,
        art_uris,
        price,
        colour_id,
        ed,
        embed_style="thumbnail",
    ):
        super().__init__(
            names[0], uris[0], art_uris[0], price, colour_id, ed, embed_style
        )
        self.back_face = BackFace(names[1], uris[1], art_uris[1], self)
        self.other_face = self.back_face

    def __repr__(self):
        return (
            f"<DoubleFaced{super().__repr__()[1:-1]} "
            f"back_face: {self.back_face}>"
        )

    def set_embed_style(self, style):
        super().set_embed_style(style)
        self.back_face.set_embed_style(style)

    def get_embeds(self, style=None):
        return [self.get_embed(style), self.back_face.get_embed(style)]


def get_price_string(data):
    price = data["prices"]["usd"]
    if price is None:
        price = data["prices"]["usd_foil"]
        if price is None:
            return "Price N/A"
        return f"${price} (foil)"
    return f"${price}"


def card_from_scryfall_response(data, art_crop=False):
    price = get_price_string(data)
    colour_id = data["color_identity"]
    ed = data["set"].upper()

    if "card_faces" in data and "image_uris" in data["card_faces"][0]:
        names = [data["card_faces"][i]["name"] for i in range(0, 2)]

        uris = []
        art_uris = []
        for i in range(0, 2):
            uris.append(data["card_faces"][i]["image_uris"]["normal"])
            art_uris.append(data["card_faces"][i]["image_uris"]["art_crop"])

        return DoubleFacedCard(names, uris, art_uris, price, colour_id, ed)
    else:
        name = data["name"]
        uri = data["image_uris"]["normal"]
        art_uri = data["image_uris"]["art_crop"]
        return Card(name, uri, art_uri, price, colour_id, ed)


class CardList:
    def __init__(self, cards, message, total_cards=None, in_order=False):
        self.cards = cards
        self.message = message
        self.total_cards = (
            total_cards if total_cards is not None else len(self.cards)
        )
        self._results = None
        self.in_order = in_order

    @property
    def results(self):
        if self._results is None:
            if len(self.cards) > 5:
                if self.in_order:
                    return self.cards[:5]
                else:
                    results = self.cards[:]
                    random.shuffle(results)
                    self._results = sorted(results[:5], key=lambda c: c.name)
            else:
                self._results = self.cards
        return self._results

    def get_embed(self):
        e = discord.Embed(
            title=self.message,
            description="\n".join([c.name for c in self.results]),
        )
        e.set_footer(text=f"{len(self.results)} of {self.total_cards} results.")

        return e

    def select_option(self, index):
        if index >= len(self.results):
            raise IndexError(
                f"Can't select option {index + 1} as list has "
                f"only {len(self.results)} entries."
            )
        else:
            return self.results[index]

    @staticmethod
    def from_scryfall_response(data, message, in_order=False):
        return CardList(
            [card_from_scryfall_response(c) for c in data.get("data")],
            message,
            data.get("total_cards"),
            in_order,
        )


class ScryfallRequest:
    BASE_URL = "https://api.scryfall.com/cards/"
    QUERIES = {
        "name": "search?q={}",
        "name_ed": "search?q=e%3D{}+{}",
        "fuzzy": "named?fuzzy={}",
        "random": "random",
        "random_ed": "random?q=e%3D{}",
        "search": "search?q={}",
    }
    BEST_CARDS = [
        "Faithless Looting",
        "Kalonian Hydra",
        "Mystic Remora",
        "Smuggler's Copter",
        "Niv-Mizzet Reborn",
    ]
    ERROR_MESSAGE = "Something went wrong and I failed to {}"
    FAILURE_MESSAGE = "I'm afraid I couldn't find {}"
    SUGGEST_MESSAGE = FAILURE_MESSAGE + ". Perhaps you meant one of these?"
    SCRYFALL_ORDER_KEYWORD = "order:"

    def __init__(self, query, ed, is_search=False, embed_style="thumbnail"):
        self.query = query
        self.ed = ed
        self.result = None
        self.mode = None
        self.is_search = is_search
        self.embed_style = embed_style

    def __repr__(self):
        return (
            f'<ScryfallRequest query: "{self.query}", ed: "{self.ed}", '
            f"result: {self.result}, is_search: {self.is_search}, "
            f"embed_style: {self.embed_style}>"
        )

    def format_query(self, query_type, *args):
        return ScryfallRequest.QUERIES[query_type].format(
            *map(requests.utils.quote, args)
        )

    def perform_request(self, query, failure_message, suggest=None):
        self.result = failure_message

        resp = requests.get(ScryfallRequest.BASE_URL + query).json()
        if resp.get("status") == 404:
            if suggest is not None:
                resp = requests.get(
                    ScryfallRequest.BASE_URL
                    + self.format_query("search", self.query)
                ).json()

                if resp.get("status") == 404:
                    return self.result
            else:
                return self.result

        data_type = resp.get("object")

        if data_type == "card":
            self.result = card_from_scryfall_response(
                resp, self.embed_style == "art"
            )
            self.result.set_embed_style(self.embed_style)
        elif data_type == "list":
            cards = resp["data"]

            if len(cards) == 1:
                self.result = card_from_scryfall_response(
                    cards[0], self.embed_style == "art"
                )
                self.result.set_embed_style(self.embed_style)
            else:
                message = suggest if suggest is not None else ""
                self.result = CardList.from_scryfall_response(
                    resp,
                    message,
                    in_order=ScryfallRequest.SCRYFALL_ORDER_KEYWORD in query,
                )

        return self.result

    def get_random_card(self):
        if self.ed:
            return self.perform_request(
                self.format_query("random_ed", self.ed),
                f'I couldn\'t find edition "{self.ed}".',
            )
        return self.perform_request(
            ScryfallRequest.QUERIES["random"],
            ScryfallRequest.ERROR_MESSAGE.format("find a random card."),
        )

    def get_best_card(self):
        return self.perform_request(
            self.format_query(
                "fuzzy", random.choice(ScryfallRequest.BEST_CARDS)
            ),
            ScryfallRequest.ERROR_MESSAGE.format("find the best card."),
        )

    def get_card(self):
        if self.ed:
            query_string = f'"{self.query}" in "{self.ed}"'
            return self.perform_request(
                self.format_query("name_ed", self.ed, self.query),
                ScryfallRequest.FAILURE_MESSAGE.format(query_string),
                ScryfallRequest.SUGGEST_MESSAGE.format(query_string),
            )
        return self.perform_request(
            self.format_query("fuzzy", self.query),
            ScryfallRequest.FAILURE_MESSAGE.format(self.query),
            ScryfallRequest.SUGGEST_MESSAGE.format(self.query),
        )

    def get_search_results(self):
        return self.perform_request(
            self.format_query("search", self.query),
            ScryfallRequest.FAILURE_MESSAGE.format(
                "any cards matching this search."
            ),
        )

    def resolve(self):
        if self.is_search:
            self.get_search_results()
        elif self.query.lower() == "random":
            self.get_random_card()
        elif self.query.lower() in ["best card", "the best card"]:
            self.get_best_card()
        else:
            self.get_card()

        return self.result

    def get_result(self):
        if self.result is None:
            self.resolve()

        if self.result is None:
            utilities.log_message(
                "Failed to find card while searching scryfall for "
                f'"{self.query}".'
            )
            return (
                "Oops, something went wrong when I was looking for "
                + f'"{utilities.capitalise(self.query)}". Let Owen know!'
            )

        return self.result


# All prefixes which can be constructed from the prefix characters
#   - @ or art_crop
#   - ! or full art
#   - ? or is_search
POSSIBLE_PREFIXES = (
    r"@\?!|@!\?|!@\?|!\?@|\?!@|\?@!|@\?|@!|\?@|!@|\?!|!\?|[\?!@]"
)
QUERY_REGEX = re.compile(
    rf"\[(?P<prefix>{POSSIBLE_PREFIXES})?"
    r"(?P<query>[\w *+,.:=!?&\'\/\-\"\(\)<>{}]+)"
    r"(\|(?P<ed>[a-z0-9 \-]+))?\]",
    flags=re.IGNORECASE,
)


# Return query objects for each card found in the message
def get_queries(message):
    queries = []
    message = re.sub(r"(?<!\\)`.*(?<!\\)`", "", message)
    for q in re.finditer(QUERY_REGEX, message):
        prefix = q.group("prefix")
        if prefix is None:
            is_search = False
            embed_style = "thumbnail"
        else:
            is_search = True if "?" in prefix else False
            embed_style = (
                "art"
                if "@" in prefix
                else ("full" if "!" in prefix else "thumbnail")
            )

        query = q.group("query").strip()
        ed = q.group("ed")
        if ed:
            ed = ed.strip()

        queries.append(ScryfallRequest(query, ed, is_search, embed_style))

    return queries


class ScryfallHandler(commands.Pattern):
    # pylint: disable=abstract-method

    ART_EMOJIS = [
        "paintbrush",
        "artist_palette",
        "adult::artist_palette",
        "man_artist",
        "woman_artist",
    ]
    ENLARGE_EMOJIS = [
        "magnifying_glass_tilted_left",
        "magnifying_glass_tilted_right",
        "microscope",
    ]
    SHRINK_EMOJIS = ["telescope", "pinching_hand"]
    EMBED_EMOJI_MAPPING = {
        "art": ART_EMOJIS,
        "full": ENLARGE_EMOJIS,
        "thumbnail": SHRINK_EMOJIS,
    }
    REMOVE_EMOJIS = [
        "cross_mark",
        "heavy_multiplication_x",
        "cross_mark_button",
    ]
    MESSAGE_CACHE_SIZE = 20  # number of messages to remember in each channel.
    BAD_QUERY_MESSAGE = "Illegal character in search string."

    def __init__(self, config):
        assert config["scryfall"]
        super().__init__(
            config,
            regex=r"\[[^\[\]]+\]",
            will_send=True,
            monitors_reactions=True,
        )
        self.sent = {}
        self.sent_channels = {}

    async def handle(self, message):
        async with message.channel.typing():
            results = [q.get_result() for q in get_queries(message.content)]
        if results:
            for result in results:
                await self.send(result, message.channel)
        else:
            await self.send(ScryfallHandler.BAD_QUERY_MESSAGE, message.channel)

    async def handle_reaction(self, reaction, _):
        if reaction.message.id not in self.sent:
            return

        emoji = utilities.get_emoji_name(reaction.emoji)
        embed_style = None
        for key in ScryfallHandler.EMBED_EMOJI_MAPPING.keys():
            if emoji in ScryfallHandler.EMBED_EMOJI_MAPPING[key]:
                embed_style = key
                break

        index = (
            int(emoji[-1:]) - 1
            if emoji.startswith("keycap_") and 0 < int(emoji[-1]) < 6
            else None
        )
        remove_message = emoji in ScryfallHandler.REMOVE_EMOJIS

        utilities.log_message(f'Scryfall message reacted to with "{emoji}".')

        if remove_message:
            await reaction.message.delete()
            utilities.log_message("Deleted message.")
            return

        message, sent = self.sent[reaction.message.id]
        if isinstance(sent, CardList) and index is not None:
            try:
                card = sent.select_option(index)
            except IndexError:
                return

            if type(card) == Card:
                await reaction.message.edit(embed=card.get_embed())
                self.log_sent(reaction.message, card)
            elif type(card) == DoubleFacedCard:
                await reaction.message.delete()
                await self.send(card, reaction.message.channel)

            utilities.log_message("Option selected from scryfall card list.")
            await reaction.clear()
            return

        if embed_style is None:
            return
        elif embed_style == sent.embed_style:
            await reaction.clear()
            return

        if isinstance(sent, Card):
            await reaction.message.edit(embed=sent.get_embed(embed_style))
        else:
            utilities.log_message(f"Strange scryfall sent type: {type(sent)}")
            return

        if type(sent) in [DoubleFacedCard, BackFace]:
            for message, content in self.sent.values():
                if content is sent.other_face:
                    await message.edit(embed=content.get_embed(embed_style))

        await reaction.clear()
        utilities.log_message("Scryfall embed size edited.")

    def log_sent(self, message, content):
        self.sent[message.id] = (message, content)
        self.reaction_targets.append(message.id)

        if message.channel.id not in self.sent_channels:
            self.sent_channels[message.channel.id] = []
        self.sent_channels[message.channel.id].append(message.id)
        if (
            len(self.sent_channels[message.channel.id])
            > ScryfallHandler.MESSAGE_CACHE_SIZE
        ):

            message_id = self.sent_channels[message.channel.id].pop(0)

            try:
                del self.sent[message_id]
            except KeyError:
                pass

            try:
                self.reaction_targets.remove(message_id)
            except ValueError:
                pass

    async def send(self, content, channel):
        if type(content) == str:
            await channel.send(embed=discord.Embed(title=content))
        elif type(content) == discord.Embed:
            await channel.send(embed=content)
        elif type(content) in [Card, CardList]:
            self.log_sent(
                await channel.send(embed=content.get_embed()), content
            )
        elif type(content) == DoubleFacedCard:
            front, back = content.get_embeds()
            self.log_sent(await channel.send(embed=front), content)
            self.log_sent(await channel.send(embed=back), content.back_face)
        else:
            raise TypeError(f"Can't send {content} in {channel}.")
