# Requires Python 3.6

import asyncio
import difflib
import re

import discord

import campaign
import commands
import database
import kick
import mcserv
import roller
import scryfall
import utilities

class Bot():
    INSTRUCTIONS = [
        commands.About,
        commands.Blackletter,
        campaign.CampaignSwitcher,
        commands.Hello,
        commands.Help,
        kick.Kick,
        mcserv.Minecraft,
        commands.No,
        commands.Reverse,
        roller.RollCommand,
        commands.Spell,
        commands.VaporWave,
        commands.Weeb,
        commands.WordArt,
        commands.XKCD
    ]

    PATTERNS = [
        commands.Creeper,
        commands.JoJo,
        scryfall.ScryfallHandler
    ]

    def __init__(self, client, loop):
        config = utilities.load_config()
        config['client'] = client
        self.client = client

        self.db = database.Discord_Database()

        self.commands = {}
        for i in Bot.INSTRUCTIONS:
            try:
                cmd = i(config)
                for c in cmd.commands:
                    self.commands[c] = cmd
            except AssertionError:
                utilities.log_message(f'{i} disabled.')

        self.patterns = []
        for p in Bot.PATTERNS:
            try:
                self.patterns.append(p(config))
            except AssertionError:
                utilities.log_message(f'{p} disabled.')

        self.reaction_handlers = []
        for h in self.patterns + list(self.commands.values()):
            if h.monitors_reactions:
                self.reaction_handlers.append(h)

        self.token = config['token']

        loop.run_until_complete(database.init_db(config['db_file']))
        
    def start(self):
        client.run(self.token)

    async def handle_command(self, message):
        if message.author == client.user or message.author.bot:
            return

        if message.guild is not None:
            await self.db.insert_user(message.author)
            await self.db.insert_server(message.guild)
        self.log_message(message)

        cmd = None
        if message.content.startswith('--'):
            match = re.search(r'^--[a-zA-Z]+', message.content.lower())

            if match is None:
                await message.channel.send(
                    'Commands are called via `--<command>`. Try `--all` ' + \
                    'to see a list of commands or `--help` for further assistance.'
                )
                return

            cmd_str = match.group(0)
            if cmd_str == '--all':
                await message.channel.send('\n'.join(self.commands))
                return
            elif cmd_str in self.commands:
                cmd = self.commands[match.group(0)]
            else:
                suggestions = difflib.get_close_matches(cmd_str, self.commands)
                if suggestions:
                    await message.channel.send(
                        f'Command `{cmd_str}` doesn\'t exist. ' + \
                        f'Perhaps you meant `{suggestions[0]}`?'
                    )
                else:
                    await message.channel.send(
                        f'Command `{cmd_str}` doesn\'t exist. Try `--all` ' + \
                        'to see a list of commands.'
                    )
                return
        else:
            for pattern in self.patterns:
                if re.search(pattern.regex, message.content):
                    cmd = pattern
            if cmd is None:
                return

        try:
            resp = await cmd.handle(message)
        except Exception as e:
            utilities.log_message('Ran into issue handling command ' + \
                f'{message.content}: {e}')
            await message.channel.send(
                'Ran into an issue with that command.'
            )
            return

        if not cmd.will_send:
            try:
                if type(resp) == str:
                    await message.channel.send(resp)
                elif type(resp) == discord.Embed:
                    await message.channel.send(embed=resp)
                else:
                    utilities.log_message('Got strange type from command ' + \
                        f'"{message.content}": {type(resp)}.')
                    await message.channel.send(
                        'Ran into an issue with that command.'
                    )
            except Exception as e:
                utilities.log_message(f'Ran into issue sending response: {e}')
                await message.channel.send('Failed to send response. ' + \
                    '@Owen to report.')
        
        if cmd.delete_message:
            try:
                await message.delete()
                utilities.log_message('Deleted command message.')
            except discord.errors.Forbidden:
                utilities.log_message('Couldn\'t delete command message; ' + \
                    'insufficient permissions.')
            except discord.errors.NotFound:
                utilities.log_message('Couldn\'t find message to delete. ' + \
                    'Already gone?')

    async def handle_reaction(self, reaction, user):
        if reaction.me or user == client.user or \
            reaction.message.author != client.user:
            
            return

        for h in self.reaction_handlers:
            if reaction.message.id in h.reaction_targets:
                await h.handle_reaction(reaction, user)

    def log_message(self, message):
        guild_string = message.guild
        if guild_string is None:
            guild_string = 'me'

        if message.content:
            utilities.log_message(message.author.display_name + \
                f' sent "{message.content}" to {guild_string}.')
        else:
            utilities.log_message(message.author.display_name + \
                f' sent an attachment to {guild_string}.')

intents = discord.Intents.default()
intents.members = True
intents.reactions = True

loop = asyncio.get_event_loop()
client = discord.Client(
    loop=loop,
    intents=intents,
    activity=discord.Activity(name='you try --help', type=3)
)
bot = Bot(client, loop=loop)

@client.event
async def on_message(message):
    await bot.handle_command(message)

@client.event
async def on_reaction_add(reaction, user):
    await bot.handle_reaction(reaction, user)

@client.event
async def on_ready():
    utilities.log_message(f'Logged in as {client.user.name},' + \
        f' ID: {client.user.id}')
    utilities.log_message('==== BEGIN LOG ====')

bot.start()
