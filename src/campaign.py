import asyncio
import time

import discord

import commands
import database
import utilities

class CampaignSwitcher(commands.Command):
    def __init__(self, config):
        assert config['dnd_campaign']
        super().__init__(config)
        self.commands = ['--dnd']
        self.dm_role = config['dm_role']
        self.campaigns = {}
        self.db = database.Campaign_Database(config['db_file'])
        self.help_message = utilities.load_help()['dnd']
        config['client'].loop.create_task(self.notify(config['client']))

    async def handle(self, message):
        server = message.guild.id
        campaign = self.get_active_campaign(server)
        text = message.content[len(self.commands[0]):].strip()
        command = text.split(' ')[0].lower()
        arg = text[len(command):].strip()

        if command == '':
            if campaign is not None:
                return f'The current campaign is {campaign.name}. ' + \
                    'See "--dnd help" or "--dnd all" for available operations.'
            else:
                return 'Start a campaign with "--dnd new <name>".'            

        options = [
            'add',
            'all',
            'campaign',
            'day',
            'delete',
            'help',
            'join', 
            'leave',
            'list',
            'members', 
            'new', 
            'nick',
            'notify',
            'remove', 
            'setdm',
            'setnick',
            'time'
        ]
        if not (command in options):
            return 'That command doesn\'t exist. ' + \
                'Try "--dnd all" to see a list of options.'

        if command == 'all':
            return '--dnd ' + '\n--dnd '.join(options)

        name_check = lambda n: n.replace(' ', '').isalnum() 

        if command == 'new':
            if not name_check(arg):
                return 'Only alphanumeric characters can be used in ' + \
                    f'campaign names. "{arg}" is inadmissable.'

            if campaign:
                self.db.add_campaign(campaign)

            if not self.db.get_campaign(arg, server):
                self.campaigns[server] = Campaign(arg, server)
                self.db.add_campaign(self.campaigns[server])
                return f'Created new campaign {arg} and set it as active.'
            else:
                return f'The campaign {arg} already exists!'
        elif command == 'help':
            return self.help_message
        elif command == 'list':
            campaigns = [t[0] for t in self.db.get_campaign_names(server)]
            if campaigns == []:
                return 'There are no campaigns on this server.'
            else:
                return 'Campaigns on this server:\n\t' + '\n\t'.join(campaigns)
        elif command == 'campaign':
            if not name_check(arg):
                return 'Only aplhanumeric characters can be used in ' + \
                    f'campaign names. "{arg}" cannot be a campaign.'

            if campaign is not None and campaign.name.lower() == arg.lower():
                return f'{campaign.name} is already the active campaign.'

            new = Campaign.from_db_tup(
                self.db.get_campaign(arg, server),
                server
            )

            if new is None:
                return f'No campaign named {arg} exists.'

            if self.campaigns.get(server) is not None:
                self.db.add_campaign(self.campaigns[server])
            self.campaigns[server] = new
            self.db.set_active(new)
            await self.apply_campaign(message.guild)
            return f'The active campaign is now {new.name}.'

        if campaign is None:
            return f'No active campaign, ' + \
                f'start one with "--dnd new <name>" to use {command}.'

        if command == 'members':
            out = f'Members of campaign {campaign.name}:\n\t'
            if campaign.dm:
                dm_name = message.guild.get_member(campaign.dm).display_name
                out += f'DM: {dm_name if dm_name else ""}\n\t'
            else:
                out += f'No DM\n\t'

            if campaign.players:
                member_names = []
                for p, n in zip(campaign.players, campaign.nicks):
                    name = message.guild.get_member(p).display_name
                    name += (f' ({n})' if n else '') 
                    member_names.append(name)
                
                out += '\n\t'.join(member_names)
            else:
                out += 'No players'

            return out
        elif command == 'nick':
            if not name_check(arg):
                return 'Only alphanumeric characters can be used in ' + \
                    f'nicknames. "{arg}" is inadmissable.'
            if message.guild.owner and \
                message.author.id == message.guild.owner.id:
                
                return f'{target.display_name} is the guild owner ' + \
                    f'which means I can\'t set their nickname.'

            campaign.set_nick(message.author.id, arg)
            await message.author.edit(nick=arg)
            self.db.add_campaign(campaign)
            return f'Set the nickname for {message.author.display_name} ' + \
                f'in {campaign.name} to {arg}.'
        elif command == 'join':
            if message.author.id in campaign.players:
                return f'You are already in campaign {campaign.name}!'

            campaign.add_player(message.author.id)
            self.db.add_campaign(campaign)
            return f'Added {message.author.display_name} to ' + \
                f'{campaign.name}. Welcome to the party!'
        elif command == 'leave':
            campaign.remove_player(message.author.id)
            self.db.add_campaign(campaign)
            return f'Removed {message.author.display_name} from ' + \
                f'{campaign.name}.'


        if not (campaign.dm is None or message.author.id == campaign.dm):
            return f'Only the DM can use the command {command}.'

        if command == 'day':
            if arg.lower() == 'none':
                campaign.day = -1
                self.db.add_campaign(campaign)
                return f'Unset the session day for {campaign.name}.'

            try:
                day = utilities.parse_weekday(arg)
            except ValueError:
                return f'{arg} is not a valid day of the week.'

            campaign.day = day
            self.db.add_campaign(campaign)
            return f'I have updated the session day for {campaign.name}.'
        elif command == 'time':
            if arg.lower() == 'none':
                campaign.time = -1
                self.db.add_campaign(campaign)
                return f'Unset the session time for {campaign.name}.'

            try:
                time = utilities.parse_time(arg)
            except ValueError:
                return f'I couldn\'t parse "{arg}" as a time. Please use ' + \
                    'the format "H:M" when setting session time.'

            campaign.time = time
            self.db.add_campaign(campaign)
            return f'I have updated the session time for {campaign.name}.'
        elif command == 'notify':
            if campaign.channel == message.channel.id:
                campaign.notify = False
                campaign.channel = None
                self.db.add_campaign(campaign)

                return f'Notifications have been disabled for {campaign.name}.'
            else:
                campaign.notify = True
                campaign.channel = message.channel.id
                self.db.add_campaign(campaign)

                if campaign.day == -1 and campaign.time == -1:
                    reminder_string = ' Remember to set a day and time to ' + \
                        'get notified!'
                elif campaign.day == -1:
                    reminder_string = ' A session time has been set, but ' + \
                        'the session day must be set to enable notifications.'
                elif campaign.time == -1:
                    reminder_string = ' A session day has been set, but ' + \
                        'the session time must be set to enable notifications.'
                else:
                    reminder_string = ''

                return f'Notifications for {campaign.name} ' + \
                    'will be sent in this channel.' + reminder_string
        elif command == 'delete':
            self.db.delete_campaign(campaign)
            del self.campaigns[server]
            return f'Deleted the campaign {campaign.name}.'

        if not message.mentions or len(message.mentions) > 1:
            return 'This command requires a single mention. e.g. ' + \
                '"--dnd <command> <mention>".'
        target = message.mentions[0]

        if command == 'setdm':    
            campaign.dm = target.id
            await self.set_dm(message.guild)
            self.db.add_campaign(campaign)
            return f'Set {target.display_name} as the DM for ' + \
                f'{campaign.name}.'
        elif command == 'add':
            if target.id in campaign.players:
                return f'{target.display_name} is already in campaign ' + \
                    f'{campaign.name}.' 

            campaign.add_player(target.id)
            self.db.add_campaign(campaign)
            return f'Added {target.display_name} to ' + \
                f'{campaign.name}.'
        elif command == 'remove':
            if target.id not in campaign.players:
                return f'{target.display_name} is not in campaign ' + \
                    f'{campaign.name}.'

            campaign.remove_player(target.id)
            self.db.add_campaign(campaign)
            return f'Removed {target.display_name} from {campaign.name}.'
        elif command == 'setnick':
            if target.id not in campaign.players:
                return f'{target.display_name} isn\'t in the ' + \
                    f'current campaign ({campaign.name}).'
            if message.guild.owner and target.id == message.guild.owner.id:
                return f'{target.display_name} is the guild owner ' + \
                    f'which means I can\'t set their nickname.'

            nick = arg
            for uid in message.raw_mentions:
                nick = nick.replace(f'<@{uid}>', '')
                nick = nick.replace(f'<@!{uid}>', '')

            campaign.set_nick(
                message.mentions[0].id, 
                nick.strip()
            )
            self.db.add_campaign(campaign)
            await self.update_nicknames(message.guild)
            return f'Updated the nickname of {target.display_name}.'

    def get_active_campaign(self, server):
        if server in self.campaigns:
            return self.campaigns[server]
        
        campaign = self.db.get_active_campaign(server)
        if campaign is not None:
            campaign = Campaign.from_db_tup(campaign, server) 
            self.campaigns[server] = campaign

        return campaign        

    async def update_nicknames(self, server):
        # server: the Guild object of the relevant server
        missing_players = []

        campaign = self.get_active_campaign(server.id)
        for p, n in zip(campaign.players, campaign.nicks):
            if not n:
                continue

            member = server.get_member(p)
            if not member:
                missing_players.append(p)
                continue

            if member.nick != n and p != server.ownerID:
                await member.edit(nick=n)

        # remove players who have left the server
        for p in missing_players:
            campaign.remove_player(p)

    async def set_dm(self, server):
        # server: the Guild object of the relevant server

        dm_role = discord.utils.find(
            lambda r: r.name == self.dm_role, 
            server.roles
        )

        for member in server.members:
            if dm_role in member.roles:
                await member.remove_roles(dm_role)

        campaign = self.get_active_campaign(server.id)
        if not campaign.dm:
            return

        try:
            await server.get_member(campaign.dm).add_roles(dm_role)
        except AttributeError: # dm has left the server
            campaign.dm = None

    async def apply_campaign(self, server):
        # server: the Guild object of the relevant server
        await self.set_dm(server)
        await self.update_nicknames(server)

    def save_campaigns(self):
        for campaign in self.campaigns.values():
            self.db.add_campaign(campaign)

    async def notify(self, client, period=60, delta=1800):
        await client.wait_until_ready()

        while not client.is_closed():
            for name, channel, players in self.db.get_reminders(period, delta):
                try:
                    mention_string = \
                        ' '.join([f'<@{p}>' for p in parse_player_string(players)])

                    channel = discord.utils.find(
                        lambda c: c.id == channel, 
                        client.get_all_channels()
                    )

                    await channel.send(
                        f'A game for {name} begins in ' + \
                        f'{int(round(delta / 60, 0))} minutes.\n\n' + \
                        mention_string
                    )
                except:
                    utilities.log_message('Ran into an issue sending ' + \
                        f'notification for campaign {name}.')
                    
            await asyncio.sleep(period)

class Campaign():
    def __init__(self, name, server, dm=None, players=None, nicks=None,
        day=-1, time=-1, notify=False, channel=None):
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
        # int: day of the week, -1 -> unset
        self.day = day
        # int: seconds into the day, -1 -> unset
        self.time = time
        # bool: whether to notify before given day / time
        self.notify = notify
        # int: discord id of the channel to notify in
        self.channel = channel

    def add_player(self, player, nick=''):
        self.players.append(player)
        self.nicks.append(nick)

    def remove_player(self, player):
        i = self.players.index(player)
        self.nicks = self.nicks[:i] + self.nicks[i + 1:]
        self.players.remove(player)

    def set_nick(self, player, nick):
        self.nicks[self.players.index(player)] = nick

    @staticmethod
    def from_db_tup(tup, server):
        if tup is None:
            return None

        name, dm, players, nicks, day, time, notify, channel = tup

        camp = Campaign(
            name, 
            server, 
            dm, 
            parse_player_string(players) if players else [],
            [n.replace('"', '') for n in nicks.split(',')] if nicks else [],
            day,
            time,
            bool(notify),
            channel
        )

        return camp

def parse_player_string(players):
    return [int(p) for p in players.split(',')]
