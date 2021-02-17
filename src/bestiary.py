import discord
import requests

class Bestiary():
    def __init__(self, bestiary_url):
        self.build_bestiary(bestiary_url)

    def build_bestiary(self, bestiary_url):
        try:
            self.bestiary = {beast['name']: beast for beast in \
                requests.get(bestiary_url).json()}
        except:
            raise ValueError


    def create_embed(self, beast):
        MISSING = 'N/A'
        ZERO_WIDTH_SPACE = '\u200b'
        HORIZONTAL_LINE = '~~-' + ' ' * 32 + '-~~'

        e = discord.Embed(title=beast.get('name', MISSING))

        field = lambda n: e.add_field(
            name=n,
            value=beast.get(n.lower(), MISSING),
            inline=False
        )

        inline_field = lambda n=ZERO_WIDTH_SPACE: e.add_field(
            name=n,
            value=beast.get(n.lower(), MISSING) if n != ZERO_WIDTH_SPACE else n,
            inline=True
        )

        horizontal_line = lambda: e.add_field(
            name=ZERO_WIDTH_SPACE,
            value=HORIZONTAL_LINE,
            inline=False 
        )

        # first line
        inline_field('Size')
        inline_field('Alignment')
        inline_field('Speed')
        
        # second line
        inline_field('AC')
        inline_field()
        inline_field('Health')
        
        horizontal_line()

        # third line
        inline_field('STR')
        inline_field('DEX')
        inline_field('CON')

        # fourth line
        inline_field('INT')
        inline_field('WIS')
        inline_field('CHA')

        horizontal_line()

        e.add_field(
            name='Saving Throws',
            value=', '.join(
                [f'{s.upper()} {beast["save"][s]}' for s in beast['save'] if s]
            )
        )
        e.add_field(
            name='Skills',
            value=', '.join(
                [f'{s.upper()} {beast["skill"][s]}' for s in beast['skill'] if s]
            )
        )
        e.add_field(
            name='Languages',
            value=', '.join(beast.get('languages', []))
        )
        e.add_field(
            name='Challenge',
            value=beast.get('cr')
        )
