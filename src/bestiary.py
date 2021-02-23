import difflib

import discord
import requests


class Bestiary:
    def __init__(self, bestiary_url):
        self.build_bestiary(bestiary_url)

    def build_bestiary(self, bestiary_url):
        try:
            self.bestiary = {
                beast["name"].lower(): beast
                for beast in requests.get(bestiary_url).json()
            }
        except:
            raise ValueError

    def get_beast(self, query):
        beast = difflib.get_close_matches(
            query.lower(), self.bestiary.keys(), 1
        )
        if beast:
            return self.bestiary[beast[0]]
        else:
            return None

    def handle_command(self, query):
        beast = self.get_beast(query)
        if beast is None:
            return f'Sorry, I couldn\'t fine "{query}".'
        else:
            return Bestiary.create_embed(beast)

    @staticmethod
    def create_embed(beast):
        MISSING = "N/A"
        ZERO_WIDTH_SPACE = "\u200b"
        HORIZONTAL_LINE = "~~-" + " " * 64 + "-~~"

        e = discord.Embed(title=beast.get("name", MISSING))

        inline_field = lambda n=ZERO_WIDTH_SPACE: e.add_field(
            name=n,
            value=beast.get(n.lower(), MISSING) if n != ZERO_WIDTH_SPACE else n,
            inline=True,
        )
        section_title = lambda n: e.add_field(
            name=n + " |" + HORIZONTAL_LINE,
            value=ZERO_WIDTH_SPACE,
            inline=False,
        )

        inline_field("Size")
        inline_field("Alignment")
        inline_field("Speed")
        inline_field("AC")
        inline_field("HP")
        inline_field("CR")
        section_title("Stats")
        inline_field("STR")
        inline_field("DEX")
        inline_field("CON")
        inline_field("INT")
        inline_field("WIS")
        inline_field("CHA")
        section_title("Details")

        if beast["saves"] is not None:
            e.add_field(
                name="Saving Throws",
                value=", ".join(
                    [
                        f'{s.capitalize()} {beast["saves"][s]}'
                        for s in beast["saves"]
                    ]
                ),
                inline=False,
            )
        if beast["skills"] is not None:
            e.add_field(
                name="Skills",
                value=", ".join(
                    [
                        f'{s.capitalize()} {beast["skills"][s]}'
                        for s in beast["skills"]
                    ]
                ),
                inline=False,
            )
        if beast["languages"] is not None:
            e.add_field(
                name="Languages",
                value=", ".join(beast["languages"]),
                inline=False,
            )

        field_sections = [
            (s, s.lower().replace(" ", "_"))
            for s in ["Traits", "Actions", "Legendary Actions"]
        ]
        if (
            sum(
                [
                    len(beast[k]) if beast[k] != None else 0
                    for _, k in field_sections
                ]
            )
            + len(e.fields)
            < 25
        ):

            for section, key in field_sections:
                if beast[key]:
                    section_title(section)
                    for t in beast[key]:
                        e.add_field(
                            name=t["name"], value=t["text"], inline=False
                        )

            ret = e
        else:
            ret = [e]
            for section, key in field_sections:
                e = discord.Embed(title=section)
                for t in beast[key]:
                    e.add_field(name=t["name"], value=t["text"], inline=False)
                ret.append(e)

        return ret
