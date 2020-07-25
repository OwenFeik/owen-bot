import discord

import commands
import database

class CampaignSwitcher(commands.Command):
    def __init__(self, config):
        assert config['dnd_campaign']
        super().__init__(config)
        self.commands = ['--dnd']
        self.campaigns = {}
        self.db = database.Campaign_Database(config['db_file'])

    async def handle(self, message):
        campaign = await self.get_campaign(message.guild)

        text = message.content[len(self.commands[0]):].strip()
        command = text.split(' ')[0].lower()
        arg = text[len(command):].strip()

        if not arg.isalnum():
            return 'Only alphanumeric characters can be used in names. ' + \
                f'{arg} is inadmissable.'

        if command == '':
            if self.campaign is not None:
                return f'The current campaign is {self.campaign.name}.'
            else:
                return 'Start a campaign with "--dnd new <name>".'            
        elif command == 'new':
            self.campaign = Campaign(arg, message.guild)
        
        if self.campaign is None:
            return f'No active campaign, \
                start one with "--dnd new <name>" to use {command}.'
        
        if command == 'nick':
            self.campaign.set_nick(message.author.id, arg)
            await message.author.edit(nick=arg)
            return f'Set the nickname for {message.author.display_name} ' + \
                f'in {self.campaign.name} to {arg}.'
        elif command == 'join':
            self.campaign.add_player(message.author.id)
            return f'Added {message.author.display_name} to ' + \
                f'{self.campaign.name}. Welcome to the party!'
        elif command == 'leave':
            self.campaign.remove_player(message.author.id)
            return f'Removed {message.author.display_name} from ' + \
                f'{self.campaign.name}.'
        elif command == 'setdm':
            if self.campaign.dm is not None and \
                message.author.id != self.campaign.dm:
                
                return 'Only the current DM can set a new DM.'
            
            if not message.mentions or len(message.mentions) > 1:
                return 'Usage: "--setdm <mention>".'
            
            self.campaign.dm = message.mentions[0].id
            return f'Set {message.mentions[0].display_name} as the DM for ' + \
                f'{self.campaign.name}.'

    async def get_campaign(self, server):
        if server.id in self.campaigns:
            return self.campaigns[server.id]
        
        campaign = self.db.get_active_campaign(server.id)
        if campaign is not None:
            name, dm, players, nicks = campaign
            campaign = Campaign(
                name, 
                server.id, 
                dm, 
                [int(p) for p in players.split(',')],
                [n for n in nicks.split(',')]
            )
            self.campaigns[server.id] = campaign

        return campaign        

    async def update_nicknames(self, server):
        for p, n in zip(self.campaign.players, self.campaign.nicks):
            member = await server.get_member(p)
            await member.edit(nick=n)

    async def set_dm(self, server, user):
        dm_role = discord.utils.find(
            lambda r: r.name == self.dm_role, 
            server.roles
        )

        for member in server.members:
            if dm_role in member.roles:
                await member.remove_roles(dm_role)

        await user.add_roles(dm_role)


    async def apply_campaign(self, server):
        await self.set_dm(server, server.get_member(self.campaign.dm))
        await self.update_nicknames(server)

class Campaign():
    def __init__(self, name, server, dm=None, players=None, nicks=None):
        # str: name of the campaign
        self.name = name 
        # int: discord id of the server
        self.server = server 
        # int: discord id of the dm
        self.dm = dm 
        # [int]: discord ids of the players
        self.players = players if players is not None else []
        # [str]: nicks of the players for campaign
        self.nicks = nicks if nicks is not None else []

    def add_player(self, player, nick=None):
        self.players.append(player)
        self.nicks.append(nick)

    def remove_player(self, player):
        i = self.players.index(player)
        self.nicks = self.nicks[:i] + self.nicks[i + 1:]
        self.players.remove(player)

    def set_nick(self, player, nick):
        self.nicks[self.players.index(player)] = nick
