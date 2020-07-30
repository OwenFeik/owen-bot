# Requires Python 3.6

import re

import discord

import campaign
import commands
import database
import kick
import mcserv
import roll
import utilities

class Bot():
    instructions = [
        commands.About,
        campaign.CampaignSwitcher,
        commands.Hello,
        commands.Help,
        kick.Kick,
        mcserv.Minecraft,
        commands.No,
        commands.Reverse,
        roll.RollCommand,
        commands.Spell,
        commands.VaporWave,
        commands.Weeb,
        commands.WordArt,
        commands.XKCD
    ]

    patterns = [
        commands.Creeper,
        commands.JoJo,
        commands.Scryfall
    ]

    def __init__(self, client):
        config = utilities.load_config()
        config['client'] = client
        self.client = client
        self.db = database.Discord_Database(config['db_file'])

        self.commands = {}
        for i in self.instructions:
            try:
                cmd = i(config)
                for c in cmd.commands:
                    self.commands[c] = cmd
            except AssertionError:
                utilities.log_message(f'{i} disabled.')

        patterns = self.patterns
        self.patterns = []
        for p in patterns:
            try:
                self.patterns.append(p(config))
            except AssertionError:
                utilities.log_message(f'{p} disabled.')

        self.regex = f"^({'|'.join(self.commands)})"

        self.token = config['token']
        
    def start(self):
        client.run(self.token)

    async def handle_command(self, message):
        if message.author == client.user:
            return

        if message.guild is not None:
            self.db.insert_user(message.author)
            self.db.insert_server(message.guild)
        self.log_message(message)

        cmd = None
        if message.content.startswith('--'):
            if message.content.startswith('--all'):
                await message.channel.send('\n'.join(self.commands))
                return

            match = re.search(self.regex, message.content.lower())
            if match is None:
                await message.channel.send(
                    'I don\'t recognise that command. Try "--all" or "--help".'
                )
                return

            cmd = self.commands[match.group(0)]
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
            if type(resp) == str:
                await message.channel.send(resp)
            elif type(resp) == discord.Embed:
                await message.channel.send(embed=resp)
            else:
                utilities.log_message('Got strange type from command ' + \
                    f'"{message.content}".')
                await message.channel.send(
                    'Ran into an issue with that command.'
                )
        
        if cmd.delete_message:
            try:
                await message.delete()
                utilities.log_message(f'Deleted command message.')
            except discord.errors.Forbidden:
                utilities.log_message('Couldn\'t delete command message; ' + \
                    'insufficient permissions.')
            except discord.errors.NotFound:
                utilities.log_message('Couldn\'t find message to delete. ' + \
                    'Already gone?')

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

client = discord.Client()
bot = Bot(client)

@client.event
async def on_message(message):
    await bot.handle_command(message)

@client.event
async def on_ready():
    utilities.log_message(f'Logged in as {client.user.name},' + \
        f' ID: {client.user.id}')
    utilities.log_message('==== BEGIN LOG ====')
    await client.change_presence(activity=discord.Activity(name='try --help'))

bot.start()
