import asyncio
import re

import discord

import commands
import database
import utilities

# pylint: disable=abstract-method


class CampaignCommand(commands.Command):
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)

        # Command argument must be alphanumeric
        self.needs_alnum = kwargs.get("needs_alnum", False)
        # This command needs an active campaign
        self.needs_campaign = kwargs.get("needs_campaign", False)
        # This command can only be used by the DM
        self.needs_dm = kwargs.get("needs_dm", False)
        # This command requires a single mention in message
        self.needs_mention = kwargs.get("needs_mention", False)

        # The campaign switcher object which manages the commands
        self.meta = kwargs.get("meta", None)

    def __str__(self):
        return self.commands[0]

    # CampaignCommands define a different _handle interface to regular commands
    # for the more specialised domain.
    #
    # pylint: disable=arguments-differ
    async def _handle(self, _guild, _campaign, _arg, _target):
        # guild: server the message was sent in
        # campaign: current active campaign on this server
        # arg: the text following the command in the message
        # target: if this is a mention command, the first mention,
        #     else the author.

        raise NotImplementedError()

    async def handle(self, message):
        guild = message.guild
        campaign = await self.meta.get_active_campaign(guild.id)
        arg = message.content[len("--dnd ") + len(self.commands[0]) :].strip()
        target = message.mentions[0] if self.needs_mention else message.author

        return await self._handle(guild, campaign, arg, target)


class Add(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config,
            commands=["add"],
            needs_dm=True,
            needs_campaign=True,
            needs_mention=True,
        )

    async def _handle(self, _guild, campaign, _arg, target):
        if target.id in campaign.players:
            return (
                f"{target.display_name} is already in campaign "
                + f"{campaign.name}."
            )

        campaign.add_player(target.id)
        await self.meta.db.add_campaign(campaign)
        return f"Added {target.display_name} to " + f"{campaign.name}."


class Day(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config, commands=["day"], needs_campaign=True, needs_dm=True
        )

    async def _handle(self, _guild, campaign, arg, _target):
        if arg.lower() == "none":
            campaign.day = -1
            await self.meta.db.add_campaign(campaign)
            return f"Unset the session day for {campaign.name}."

        try:
            day = utilities.parse_weekday(arg)
        except ValueError:
            return f"{arg} is not a valid day of the week."

        campaign.day = day
        await self.meta.db.add_campaign(campaign)
        return f"I have updated the session day for {campaign.name}."


class Delete(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config, commands=["delete"], needs_campaign=True, needs_dm=True
        )

    async def _handle(self, guild, campaign, _arg, _target):
        await self.meta.db.delete_campaign(campaign)
        del self.meta.campaigns[guild.id]
        return f"Deleted the campaign {campaign.name}."


class Join(CampaignCommand):
    def __init__(self, config):
        super().__init__(config, commands=["join"], needs_campaign=True)

    async def _handle(self, _guild, campaign, _arg, target):
        if target.id in campaign.players:
            return f"You are already in campaign {campaign.name}!"

        campaign.add_player(target.id)
        await self.meta.db.add_campaign(campaign)
        return (
            f"Added {target.display_name} to "
            + f"{campaign.name}. Welcome to the party!"
        )


class Leave(CampaignCommand):
    def __init__(self, config):
        super().__init__(config, commands=["leave"], needs_campaign=True)

    async def _handle(self, _guild, campaign, _arg, target):
        worked = campaign.remove_player(target.id)
        if worked:
            await self.meta.db.add_campaign(campaign)
            return f"Removed {target.display_name} from " + f"{campaign.name}."
        else:
            return f"{target.display_name} is not in " + f"{campaign.name}."


class List(CampaignCommand):
    def __init__(self, config):
        super().__init__(config, commands=["list"])

    async def _handle(self, guild, _campaign, _arg, _target):
        campaigns = [
            t[0] for t in await self.meta.db.get_campaign_names(guild.id)
        ]
        if campaigns == []:
            return "There are no campaigns on this server."
        else:
            return "Campaigns on this server:\n\t" + "\n\t".join(campaigns)


class Members(CampaignCommand):
    def __init__(self, config):
        super().__init__(config, commands=["members"], needs_campaign=True)

    async def _handle(self, guild, campaign, _arg, _target):
        out = f"Members of campaign {campaign.name}"

        if campaign.day >= 0 and campaign.time >= 0:
            hour = str(campaign.time // 3600)
            minute = str(campaign.time % 3600 // 60)
            while len(minute) < 2:
                minute += "0"

            out += (
                " ("
                + utilities.number_to_weekday(campaign.day)
                + f" at {hour}:{minute})"
            )

        out += ":\n\t"

        dm_string = ""
        if campaign.dm:
            try:
                dm_name = (await utilities.get_member(guild, campaign.dm)).name
                dm_string = "DM: " + dm_name

                if campaign.dm in campaign.players:
                    nick = campaign.nicks[campaign.players.index(campaign.dm)]
                    dm_string += f" ({nick})" if nick else ""

            except Exception as e:
                dm_string = ""
                utilities.log_message(f"Failed to add DM name: {e}")

        out += (dm_string if dm_string else "No DM") + "\n\t"

        member_names = []
        if campaign.players:
            for p, n in zip(campaign.players, campaign.nicks):
                if p == campaign.dm:
                    continue

                try:
                    name = (await utilities.get_member(guild, p)).name
                    name += f" ({n})" if n else ""
                    member_names.append(name)
                except Exception as e:
                    utilities.log_message(f"Failed to add name: {e}")

        if member_names:
            out += "\n\t".join(member_names)
        else:
            out += "No players"

        return out


class New(CampaignCommand):
    def __init__(self, config):
        super().__init__(config, commands=["new"], needs_alnum=True)

    async def _handle(self, guild, campaign, arg, _target):
        if arg in ["help", ""]:
            return "Usage: `--dnd new <name>`."

        if campaign:
            await self.meta.db.add_campaign(campaign)

        if not await self.meta.db.get_campaign(arg, guild.id):
            self.meta.campaigns[guild.id] = Campaign(arg, guild.id)
            await self.meta.db.add_campaign(self.meta.campaigns[guild.id])
            return f"Created new campaign {arg} and set it as active."
        else:
            return f"The campaign {arg} already exists!"


class Nick(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config, commands=["nick", "setnick"], needs_campaign=True
        )

        self.regex = f'^--dnd ({"|".join(self.commands)})'
        self.nick_regex = re.compile(r"^[\w\-,' ]{1,32}$")

    async def handle(self, message):
        campaign = await self.meta.get_active_campaign(message.guild.id)
        arg = re.sub(
            self.regex, "", message.content, count=1, flags=re.IGNORECASE
        ).strip()

        nick = arg
        if message.mentions:
            if len(message.mentions) > 1:
                return (
                    "This command requires a single mention. e.g. "
                    "`--dnd setnick <mention> <name>`."
                )

            target = message.mentions[0]

            if not target.id in campaign.players:
                return (
                    f"{target.display_name} is not in {campaign.name} "
                    "so I cannot set their nickname. The DM can add them "
                    "`--dnd add <mention>` or they can join with `--dnd join`."
                )

            if (
                message.author.id in [campaign.dm, target.id]
                or campaign.dm == None
            ):

                for uid in message.raw_mentions:
                    nick = nick.replace(f"<@{uid}>", "")
                    nick = nick.replace(f"<@!{uid}>", "")
                nick = nick.strip()
            else:
                return "Only the campaign dm can set other players nicknames."
        else:
            target = message.author

            if not target.id in campaign.players:
                return (
                    f"You are not in {campaign.name}, so I cannot set "
                    "your nickname. Join with `--dnd join`."
                )

        if len(nick) == 0:
            return (
                "Usage: `--dnd nick <nickname>` or "
                "`--dnd setnick <mention> <nickname>`."
            )
        if self.nick_regex.match(nick) is None:
            return (
                "A nickname must be 1-32 non-special characters. "
                f'"{nick}" is inadmissable.'
            )

        if not message.author.id in campaign.players:
            return (
                "You must join the campaign with `--dnd join` "
                "before you can set a nickname."
            )
        if utilities.is_guild_owner(message.guild, target.id):
            if target.id == message.author.id:
                return (
                    "You are the server owner which means I can't "
                    "set your nickname."
                )
            else:
                return (
                    f"{target.display_name} is the guild owner which "
                    "means I can't set their nickname"
                )

        try:
            await target.edit(nick=nick)
        except discord.Forbidden as e:
            utilities.log_message(
                f"Failed to set nick of {target.display_name} in "
                f"{message.guild.name} due to: {e}"
            )
            return (
                "I was unable to set your nickname. Either I lack the "
                "permission to do so or you are the server owner."
            )

        campaign.set_nick(target.id, nick)
        await self.meta.db.add_campaign(campaign)
        return (
            f"Set the nickname for {target.name} "
            f"in {campaign.name} to {nick}."
        )


class Notify(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config, commands=["notify"], needs_campaign=True, needs_dm=True
        )

    async def handle(self, message):
        campaign = await self.meta.get_active_campaign(message.guild.id)

        if campaign.channel == message.channel.id:
            campaign.notify = False
            campaign.channel = None
            await self.meta.db.add_campaign(campaign)

            return f"Notifications have been disabled for {campaign.name}."
        else:
            campaign.notify = True
            campaign.channel = message.channel.id
            await self.meta.db.add_campaign(campaign)

            if campaign.day == -1 and campaign.time == -1:
                reminder_string = (
                    " Remember to set a day and time to " + "get notified!"
                )
            elif campaign.day == -1:
                reminder_string = (
                    " A session time has been set, but "
                    + "the session day must be set to enable notifications."
                )
            elif campaign.time == -1:
                reminder_string = (
                    " A session day has been set, but "
                    + "the session time must be set to enable notifications."
                )
            else:
                reminder_string = ""

            return (
                f"Notifications for {campaign.name} "
                + "will be sent in this channel."
                + reminder_string
            )


class Remove(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config,
            commands=["remove"],
            needs_campaign=True,
            needs_dm=True,
            needs_mention=True,
        )

    async def _handle(self, _guild, campaign, _arg, target):
        if target.id not in campaign.players:
            return (
                f"{target.display_name} is not in campaign "
                + f"{campaign.name}."
            )

        campaign.remove_player(target.id)
        await self.meta.db.add_campaign(campaign)
        return f"Removed {target.display_name} from {campaign.name}."


class SetCampaign(CampaignCommand):
    def __init__(self, config):
        super().__init__(config, commands=["campaign"], needs_alnum=True)

    async def _handle(self, guild, campaign, arg, _target):
        if campaign and campaign.name.lower() == arg.lower():
            return f"{campaign.name} is already the active campaign."
        elif arg == "" and campaign:
            return f"The current campaign is {campaign.name}."
        elif arg in ["help", ""]:
            return (
                "Usage: `--dnd campaign <campaign name>` to switch to "
                + "a different campaign. To create a new campaign use "
                + "`--dnd new <campaign name>`."
            )

        new = Campaign.from_db_tup(
            await self.meta.db.get_campaign(arg, guild.id), guild.id
        )

        if new is None:
            msg = f"No campaign named {arg} exists."

            sugg = await self.meta.db.suggest_campaign(f"%{arg}%", guild.id)
            if sugg:
                msg += f' Perhaps you meant "{sugg[0]}"?'

            return msg

        if self.meta.campaigns.get(guild.id) is not None:
            await self.meta.db.add_campaign(self.meta.campaigns[guild.id])
        self.meta.campaigns[guild.id] = new
        await self.meta.db.set_active(new)

        msg = f"The active campaign is now {new.name}."

        try:
            await self.meta.apply_campaign(guild)
        except discord.Forbidden:
            msg += (
                " I lack some permissions on this server, "
                "so roles or nicknames may not be updated."
            )

        return msg


class SetDM(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config,
            commands=["setdm"],
            needs_campaign=True,
            needs_dm=True,
            needs_mention=True,
        )

    async def _handle(self, guild, campaign, _arg, target):
        campaign.dm = target.id
        await self.meta.set_dm(guild)
        await self.meta.db.add_campaign(campaign)
        return f"Set {target.display_name} as the DM for " + f"{campaign.name}."


class Time(CampaignCommand):
    def __init__(self, config):
        super().__init__(
            config, commands=["time"], needs_campaign=True, needs_dm=True
        )

    async def _handle(self, _guild, campaign, arg, _target):
        if arg.lower() == "none":
            campaign.time = -1
            await self.meta.db.add_campaign(campaign)
            return f"Unset the session time for {campaign.name}."

        try:
            time = utilities.parse_time(arg)
        except ValueError as e:
            return f'I couldn\'t parse "{arg}" as a time. {e}'

        campaign.time = time
        await self.meta.db.add_campaign(campaign)
        return f"I have updated the session time for {campaign.name}."


class Campaign:
    def __init__(
        self,
        name,
        server,
        dm=None,
        players=None,
        nicks=None,
        day=-1,
        time=-1,
        notify=False,
        channel=None,
    ):
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

    def add_player(self, player, nick=""):
        self.players.append(player)
        self.nicks.append(nick)

    def remove_player(self, player):
        if player in self.players:
            i = self.players.index(player)
            self.nicks = self.nicks[:i] + self.nicks[i + 1 :]
            self.players.remove(player)
            return True
        return False

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
            [n.replace('"', "") for n in nicks.split(",")] if nicks else [],
            day,
            time,
            bool(notify),
            channel,
        )

        return camp


def parse_player_string(players):
    return [int(p) for p in players.split(",")]


class CampaignSwitcher(commands.Command):
    INSTRUCTIONS = [
        Add,
        SetCampaign,
        Day,
        Delete,
        Join,
        Leave,
        List,
        Members,
        New,
        Nick,
        Notify,
        Remove,
        SetDM,
        Time,
    ]
    DM_COLOUR = discord.Colour.from_rgb(7, 104, 173)

    def __init__(self, config):
        assert config["dnd_campaign"]
        super().__init__(config, commands=["--dnd"])
        self.dm_role = config["dm_role"]
        self.campaigns = {}
        self.db = database.Campaign_Database()
        self.help_message = utilities.load_help()["dnd"]
        config["client"].loop.create_task(self.notify(config["client"]))

        self.options = {}
        for i in CampaignSwitcher.INSTRUCTIONS:
            try:
                option = i(config)
                option.meta = self
                for c in option.commands:
                    self.options[c] = option
            except AssertionError:
                utilities.log_message(f"Campaign option {i} disabled.")

    async def handle(self, message):
        campaign = await self.get_active_campaign(message.guild.id)
        text = message.content[len(self.commands[0]) :].strip()

        option = re.search(
            r"^--dnd (?P<opt>[a-zA-Z]+)", message.content.lower()
        )

        if option == None:
            if campaign is not None:
                return (
                    f"The current campaign is {campaign.name}. "
                    + "See `--dnd help` or `--dnd all` for available operations."
                )
            else:
                return (
                    "Start a campaign with `--dnd new <name>`. "
                    + "See `--dnd help` or `--dnd all` for available operations."
                )

        command = option.group("opt")

        if command == "all":
            return "--dnd " + "\n--dnd ".join(self.options)

        if command == "help":
            return self.help_message

        if not (command in self.options):
            return (
                "That command doesn't exist. "
                + "Try `--dnd all` to see a list of options."
            )

        command = self.options[command]

        if command.needs_alnum and not text.replace(" ", "").isalnum():
            return f"`{command}` only accepts alphanumeric arguments."
        if command.needs_campaign and campaign is None:
            return (
                "No active campaign, "
                + f"start one with `--dnd new <name>` to use `{command}`."
            )
        if command.needs_dm and not (
            campaign.dm is None or message.author.id == campaign.dm
        ):

            return f"Only the DM can use the command `{command}`."
        if command.needs_mention and (
            not message.mentions or len(message.mentions) > 1
        ):

            return (
                "This command requires a single mention. e.g. "
                + f"`--dnd {command} <mention>`."
            )

        return await command.handle(message)

    async def get_active_campaign(self, server):
        if server in self.campaigns:
            return self.campaigns[server]

        campaign = await self.db.get_active_campaign(server)
        if campaign is not None:
            campaign = Campaign.from_db_tup(campaign, server)
            self.campaigns[server] = campaign

        return campaign

    async def update_nicknames(self, guild):
        # guild: the Guild object of the relevant server
        # missing_players = []

        campaign = await self.get_active_campaign(guild.id)
        for p, n in zip(campaign.players, campaign.nicks):
            if not n:
                continue

            member = await utilities.get_member(guild, p)
            if not member:
                # missing_players.append(p)
                continue

            if member.nick != n and not utilities.is_guild_owner(guild, p):

                await member.edit(nick=n)

        # commenting this for now because fetch/get_member seems
        # somewhat unreliable.

        # remove players who have left the server
        # for p in missing_players:
        #     campaign.remove_player(p)

    async def get_dm_role(self, server):
        dm_role = discord.utils.find(
            lambda r: r.name == self.dm_role, server.roles
        )

        if dm_role is None:
            try:
                dm_role = await server.create_role(
                    name=self.dm_role,
                    colour=self.DM_COLOUR,
                    hoist=False,
                    mentionable=True,
                    reason="Created by owen-bot for campaign functionality.",
                )
            except discord.Forbidden:
                return None

        return dm_role

    async def set_dm(self, guild):
        # guild: the Guild object of the relevant server
        dm_role = await self.get_dm_role(guild)

        if not dm_role:
            utilities.log_message(f"Missing role permissions in {guild.name}.")
            return

        campaign = await self.get_active_campaign(guild.id)

        for player in campaign.players:
            member = await utilities.get_member(guild, player)
            if (
                not utilities.is_guild_owner(guild, member.id)
                and dm_role in member.roles
            ):
                await member.remove_roles(dm_role)

        if not campaign.dm:
            return

        try:
            dm = await utilities.get_member(guild, campaign.dm)
            if not utilities.is_guild_owner(guild, dm.id):
                await dm.add_roles(dm_role)
        except AttributeError:
            # didn't find dm for some reason
            utilities.log_message(
                f"Failed to find DM for campaign {campaign.name} in "
                f"{guild.name}."
            )

    async def apply_campaign(self, server):
        # server: the Guild object of the relevant server
        await self.set_dm(server)
        await self.update_nicknames(server)

    async def save_campaigns(self):
        for campaign in self.campaigns.values():
            await self.db.add_campaign(campaign)

    async def notify(self, client, period=60, delta=1800):
        await client.wait_until_ready()

        while not client.is_closed():
            reminders = await self.db.get_reminders(period, delta)
            for name, channel, players in reminders:
                try:
                    mention_string = " ".join(
                        [f"<@{p}>" for p in parse_player_string(players)]
                    )

                    channel = discord.utils.find(
                        lambda c: c.id == channel, client.get_all_channels()
                    )

                    await channel.send(
                        f"A game for {name} begins in "
                        + f"{int(round(delta / 60, 0))} minutes.\n\n"
                        + mention_string
                    )
                except Exception as e:
                    utilities.log_message(
                        "Ran into an issue sending "
                        + f"notification for campaign {name}: {e}"
                    )

            await asyncio.sleep(period)
