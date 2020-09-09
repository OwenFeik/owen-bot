import asyncio
import difflib
import random

import discord

import scryfall
import spellbook
import utilities
import wordart
import xkcd

class Command():
    def __init__(self, _):
        self.commands = []
        self.delete_message = False
        self.will_send = False
        self.regex = None

    async def _handle(self, _):
        return 'Not implemented.'

    def remove_command_string(self, text):
        argument = text[max([len(c) for c in self.commands if \
            text.startswith(c)]):].strip()
        return argument

    async def handle(self, message):
        return await self._handle(self.remove_command_string(message.content))

class About(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--about']
    
    async def handle(self, _):
        return 'Hi, I\'m Owen\'s bot! I can help you in a variety of ways.' + \
            ' Try "--all" to see what I can do, and message Owen if ' + \
            'anything is acting up.'

class Blackletter(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--bl', '--blackletter']

    async def handle(self, message):
        self.delete_message = False

        argument = self.remove_command_string(message.content)
        if not argument:
            return 'Usage: "--bl <message>" to create ' + \
                wordart.blackletter('blackletter') + ' text.'

        try:
            argument = wordart.scrub_mentions(argument, message.mentions)
        except ValueError as e:
            return str(e)

        self.delete_message = True
        return wordart.blackletter(argument)

class Creeper(Command):
    def __init__(self, config):
        assert config['creeper']
        super().__init__(config)
        self.regex = 'creeper'

    async def handle(self, _):
        return discord.Embed(
            title='Awww mannn',
            url='https://www.youtube.com/watch?v=cPJUBQd-PNM',
            colour=discord.Colour.from_rgb(13, 181, 13)
        )

class Hello(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--hello']

    async def handle(self, message):
        return f'Greetings, {message.author.mention}.'

class Help(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--help']
        self.help_strings = utilities.load_help()

        if not config['dnd_spells']:
            del self.help_strings['spell']
        if not config['kick']:
            del self.help_strings['kick']
        if not config['mcserv']:
            del self.help_strings['minecraft']
        if not config['scryfall']:
            del self.help_strings['magic']
        if not config['xkcd']:
            del self.help_strings['xkcd']

    async def _handle(self, argument):
        if argument in self.help_strings:
            return self.help_strings[argument]

        suggestion = difflib.get_close_matches(
            argument.lower(), 
            self.help_strings.keys(), 
            1
        )
        if suggestion:
            return f'I couldn\'t find {argument}.' + \
                f'Did you mean "{suggestion[0]}"?'
        return f'I\'m afraid I can\'t help you with {argument}.'

class JoJo(Command):
    words = [
        'jojo',
        'stardust',
        'yare',
        'daze',
        'jotaro',
        'joestar',
        'polnareff',
        'jo jo'
    ]

    def __init__(self, config):
        super().__init__(config)
        word_string = '|'.join(self.words)
        self.regex = f'(?i)({word_string})'

    async def handle(self, message):
        return discord.Embed(
            description= message.author.mention + \
                ', there\'s something you should know.'
        ).set_image(url='https://i.imgur.com/mzbvy4b.png')

class No(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--no']
    
    async def handle(self, message):
        return wordart.no

class Reverse(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--reverse']
        self.delete_message = True
        self.image_urls = [
            'https://i.imgur.com/yXEiYQ4.png',
            'https://i.imgur.com/CSuB3ZW.png',
            'https://i.imgur.com/3WDcYbV.png',
            'https://i.imgur.com/IxDEdxW.png'
        ]

    async def handle(self, _):
        return discord.Embed().set_image(url=random.choice(self.image_urls))

class Scryfall(Command):
    def __init__(self, config):
        assert config['scryfall']
        super().__init__(config)
        self.regex = r'\[[^\[\]]+\]'
        self.will_send = True

    async def handle(self, message):
        queries = scryfall.get_queries(message.content)
        for query in queries:
            found = query.found
            if type(found) == str:
                await message.channel.send(found)
            else:
                for face in found.embed:
                    await message.channel.send(embed=face)

class Spell(Command):
    def __init__(self, config):
        assert config['dnd_spells']
        super().__init__(config)
        self.commands = ['--spell']
        self.sb = spellbook.Spellbook(config['spellbook_url'])
        utilities.log_message('Successfully downloaded spellbook.')

    async def _handle(self, argument):
        if argument == '':
            return 'Usage: "--spell <spell name>".'
        return self.sb.handle_command(argument)

class VaporWave(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--vw', '--vaporwave']

    async def handle(self, message):
        self.delete_message = False

        argument = self.remove_command_string(message.content)
        if not argument:
            return 'Usage: "--vw <message>" to create ' + \
                wordart.vaporwave('vaporwave') + ' text.'

        try:
            argument = wordart.scrub_mentions(argument, message.mentions)
        except ValueError as e:
            return str(e)

        self.delete_message = True
        return wordart.vaporwave(argument)

class Weeb(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--weeb']
        self.image_url = 'https://i.imgur.com/mzbvy4b.png'
    
    async def handle(self, _):
        return discord.Embed().set_image(url = self.image_url)

class WordArt(Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--wa', '--wordart']
        self.default_emoji = config['wordart_emoji']
        self.will_send = True
        
    async def handle(self, message):
        self.delete_message = False
        argument = self.remove_command_string(message.content)
        if argument:
            try:
                await message.channel.send(
                    wordart.handle_wordart_request(
                        argument, 
                        self.default_emoji
                    )
                )
                self.delete_message = True
            except discord.HTTPException as e:
                utilities.log_message(f'Error attempting to send wordart: {e}')
                await message.channel.send(
                    'Ran into an error sending this wordart. The message ' + \
                    'was probably too long, usually around 6 characters ' + \
                    'is the maximum.'
                )
        else:
            await message.channel.send(
                'Usage: "--wa <message>" to create word art. ' + \
                'Messages must be very short: around 6 characters.'
            )

class XKCD(Command):
    def __init__(self, config):
        assert config['xkcd']
        super().__init__(config)
        self.commands = ['--xkcd']
        config['client'].loop.create_task(
            self.scheduled_updates(
                config['xkcd_interval'], 
                config['client']
            )
        )

    async def _handle(self, argument):
        if argument:
            return await xkcd.get_xkcd(argument)
        return 'Use "--xkcd <comic name>" or "--xkcd <number>" to find an' + \
            'xkcd comic, or "--xkcd random" for a random comic.'

    async def scheduled_updates(self, period, client):
        await client.wait_until_ready()

        while not client.is_closed():
            await xkcd.update_db()
            await asyncio.sleep(period)
