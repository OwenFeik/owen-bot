import difflib
import random
import re

import discord

import bestiary
import spellbook
import utilities
import wordart
import xkcd

# pylint: disable=abstract-method
# Many subclasses ignore the optional _handle abstract method of Command.

class Command():
    def __init__(self, _, **kwargs):
        # Strings used to call this command
        self.commands = kwargs.get('commands', [])
        # This command would like messages it responds to deleted
        self.delete_message = kwargs.get('delete_message', False)
        # This command will send responses itself rather than returning them
        self.will_send = kwargs.get('will_send', False)
        # This command monitors reactions to its messages
        self.monitors_reactions = kwargs.get('monitors_reactions', False)
        # Ids of messages that this command would like to monitor for reactions
        self.reaction_targets = kwargs.get('reaction_targets', [])

    async def _handle(self, _):
        raise NotImplementedError()

    def remove_command_string(self, text):
        argument = text[max([len(c) for c in self.commands if \
            text.lower().startswith(c)]):].strip()
        return argument

    async def handle(self, message):
        return await self._handle(self.remove_command_string(message.content))

    async def handle_reaction(self, reaction, user):
        raise NotImplementedError()

class Pattern(Command):
    def __init__(self, _, **kwargs):
        super().__init__(_, **kwargs)

        regex = kwargs.get('regex')
        if regex is None:
            raise ValueError('Can\'t create a pattern without a regex.')

        # Regular expression to match messages relevant to this command
        self.regex = re.compile(regex)

class About(Command):
    def __init__(self, config):
        super().__init__(config, commands=['--about'])
    
    async def handle(self, _):
        return 'Hi, I\'m Owen\'s bot! I can help you in a variety of ways.' + \
            ' Try `--all` to see what I can do, and message Owen if ' + \
            'anything is acting up.'

class Blackletter(Command):
    def __init__(self, config):
        super().__init__(config, commands=['--bl', '--blackletter'])

    async def handle(self, message):
        self.delete_message = False

        argument = self.remove_command_string(message.content)
        if not argument:
            return 'Usage: `--bl <message>` to create ' + \
                wordart.blackletter('blackletter') + ' text.'

        try:
            argument = wordart.scrub_mentions(argument, message.mentions)
        except ValueError as e:
            return str(e)

        self.delete_message = True
        return wordart.blackletter(argument)

class Creature(Command):
    def __init__(self, config):
        assert config['dnd_bestiary']
        super().__init__(config, commands=['--creature'])
        self.bestiary = bestiary.Bestiary(config['bestiary_url'])
    
    async def _handle(self, argument):
        if argument == '':
            return 'Usage: `--creature <creature name>`.'
        return self.bestiary.handle_command(argument)
        
class Creeper(Pattern):
    def __init__(self, config):
        assert config['creeper']
        super().__init__(config, regex='creeper')

    async def handle(self, _):
        return discord.Embed(
            title='Awww mannn',
            url='https://www.youtube.com/watch?v=cPJUBQd-PNM',
            colour=discord.Colour.from_rgb(13, 181, 13)
        )

class Hello(Command):
    def __init__(self, config):
        super().__init__(config, commands=['--hello'])

    async def handle(self, message):
        return f'Greetings, {message.author.mention}.'

class Help(Command):
    def __init__(self, config):
        super().__init__(config, commands=['--help'])
        self.help_strings = utilities.load_help()

        if not config['dnd_spells']:
            del self.help_strings['spell']
        if not config['kick']:
            del self.help_strings['kick']
        if not config['mcserv']:
            del self.help_strings['minecraft']
        if not config['scryfall']:
            del self.help_strings['mtg']
        if not config['xkcd']:
            del self.help_strings['xkcd']

        self.help_strings['vw'] = self.help_strings['vaporwave']
        self.help_strings['bl'] = self.help_strings['blackletter']
        self.help_strings['wa'] = self.help_strings['wordart']

    async def _handle(self, argument):
        if argument in self.help_strings:
            return self.help_strings[argument]

        suggestion = difflib.get_close_matches(
            argument.lower(), 
            self.help_strings.keys(), 
            1
        )
        if suggestion:
            return f'I couldn\'t find help for `{argument}`.' + \
                f'Perhaps you meant `{suggestion[0]}`?'
        return f'I\'m afraid I can\'t help you with {argument}.'

class JoJo(Pattern):
    WEEB_WORDS = [
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
        word_string = '|'.join(JoJo.WEEB_WORDS)
        super().__init__(config, regex=f'(?i)({word_string})')

    async def handle(self, message):
        return discord.Embed(
            description= message.author.mention + \
                ', there\'s something you should know.'
        ).set_image(url=Weeb.IMAGE_URL)

class No(Command):
    def __init__(self, config):
        super().__init__(config, commands=['--no'])
    
    async def handle(self, message):
        return wordart.no

class Reverse(Command):
    def __init__(self, config):
        super().__init__(config, commands=['--reverse'], delete_message=True)
        self.image_urls = [
            'https://i.imgur.com/yXEiYQ4.png',
            'https://i.imgur.com/CSuB3ZW.png',
            'https://i.imgur.com/3WDcYbV.png',
            'https://i.imgur.com/IxDEdxW.png'
        ]

    async def handle(self, _):
        return discord.Embed().set_image(url=random.choice(self.image_urls))

class Spell(Command):
    def __init__(self, config):
        assert config['dnd_spells']
        super().__init__(config, commands=['--spell'])
        self.sb = spellbook.Spellbook(config['spellbook_url'])
        utilities.log_message('Successfully downloaded spellbook.')

    async def _handle(self, argument):
        if argument == '':
            return 'Usage: `--spell <spell name>`.'
        return self.sb.handle_command(argument)

class VaporWave(Command):
    def __init__(self, config):
        super().__init__(config, commands=['--vw', '--vaporwave'])

    async def handle(self, message):
        self.delete_message = False

        argument = self.remove_command_string(message.content)
        if not argument:
            return 'Usage: `--vw <message>` to create ' + \
                wordart.vaporwave('vaporwave') + ' text.'

        try:
            argument = wordart.scrub_mentions(argument, message.mentions)
        except ValueError as e:
            return str(e)

        self.delete_message = True
        return wordart.vaporwave(argument)

class Weeb(Command):
    IMAGE_URL = 'https://i.imgur.com/mzbvy4b.png'

    def __init__(self, config):
        super().__init__(config, commands=['--weeb'])
    
    async def handle(self, _):
        return discord.Embed().set_image(url=Weeb.IMAGE_URL)

class WordArt(Command):
    def __init__(self, config):
        super().__init__(
            config,
            commands=['--wa', '--wordart'],
            will_send=True
        )

        self.default_emoji = config['wordart_emoji']
        wordart.load_wa_alphabet()
        
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
                    'was probably too long, usually around 4 characters ' + \
                    'is the maximum.'
                )
        else:
            await message.channel.send(
                'Usage: `--wa <message>` to create word art. ' + \
                'Messages must be very short: around 4 characters.'
            )

class XKCD(Command):
    def __init__(self, config):
        assert config['xkcd']
        super().__init__(config, commands=['--xkcd'])

        xkcd.init_db()
        xkcd.start_db_thread(config['xkcd_interval'], config['client'])

    async def _handle(self, argument):
        if argument:
            return await xkcd.get_xkcd(argument)
        return 'Use `--xkcd <comic name>` or `--xkcd <number>` to find an' + \
            'xkcd comic, or `--xkcd random` for a random comic.'
