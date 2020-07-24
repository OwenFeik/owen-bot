import discord

import commands
import database

class CampaignSwitcher(commands.Command):
    def __init__(self, config):
        assert config['dnd_campaign']
        super().__init__(config)
        self.commands = ['--dnd']
        self.campaign = None
        self.db = database.Campaign_Database(config['db_file'])


    def handle(self, message):
        text = message.content[len(self.commands[0]):].strip()
        command = text.split(' ')[0].lower()
        text = text[len(command):].strip()

        if comand == '':
            if self.campaign is not None:
                return f'The current campaign is {self.campaign.name}.'
            else:
                return 'Start a campaign with "--dnd new <name>".'            
        elif command == 'new':
            self.campaign = Campaign(text, message.guild)

        elif command == 

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
