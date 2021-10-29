import discord
import roll

import commands
import database
import utilities


class RollCommand(commands.Command):
    # pylint: disable=abstract-method

    def __init__(self, config):
        super().__init__(
            config,
            commands=["--roll", "--dmroll", "--gmroll"],
            delete_message=True,
            will_send=True,
        )
        self.dm_role = config["dm_role"]
        self.failstr = "Invalid format"
        self.db = database.Roll_Database()

    async def handle(self, message):
        self.delete_message = True
        self.will_send = True

        user = message.author
        mention = user.display_name
        server = message.guild
        channel = message.channel

        string = message.content.lower().strip()
        for c in self.commands:
            if string.startswith(c):
                command = c
                break
        string = string.replace(command, "", 1).strip()

        if "stats" in string:
            await self.handle_stats(string, user, server, mention, channel)
            return

        try:
            rolls = roll.get_rolls(string)
            assert len(rolls) > 0
        except Exception as e:
            self.delete_message = False
            await channel.send(f"{self.failstr}. {e}")
            return

        if server and user:
            for r in rolls:
                for dice_str, values in r.roll_info():
                    await self.db.insert_roll(
                        dice_str, ",".join(map(str, values)), user, server
                    )

        e = build_embed(rolls, mention, string)
        if command == "--roll":
            try:
                await channel.send(embed=e)
            except discord.errors.HTTPException as e:
                await channel.send(
                    "Ran into an error. The message may have been too long."
                )

        elif command in ["--dmroll", "--gmroll"]:
            dm = await self.get_dm(message.guild.members)
            if dm is None:
                self.delete_message = False
                await channel.send(
                    f'Couldn\'t find a member with the role "{self.dm_role}".'
                )

            try:
                await dm.send(embed=e)
                if user != dm:
                    await user.send(embed=e)
            except discord.errors.HTTPException as e:
                self.delete_message = False
                await channel.send("Ran into an error.")
                utilities.log_message(f"Error sending roll: {e}")
                return

    async def handle_stats(self, string, user, server, mention, channel):
        if string == "stats":
            e = stats_embed(await self.db.get_rolls(user, server), mention)
            await channel.send(embed=e)
        elif string == "campaign stats":
            try:
                rolls, campaign_name = await self.db.get_campaign_rolls(
                    user, server
                )
            except ValueError:
                self.delete_message = False
                await channel.send(
                    f"{mention} is not in an active campaign on this server."
                )
                return

            e = stats_embed(rolls, f"{mention} in {campaign_name}")
            await channel.send(embed=e)
        elif string == "reset stats":
            self.delete_message = False
            await self.db.reset_rolls(user)
            await channel.send("Your stored rolls have been deleted.")
        elif string == "reset server stats":
            self.delete_message = False
            if server == None:
                await channel.send("I don't track stats in DMs sorry.")
            await self.db.reset_rolls(user, server)
            await channel.send(
                f"Your stored rolls on {server.name} have been deleted."
            )
        else:
            self.delete_message = False
            await channel.send("I didn't understand that. Try `--help roll`.")

    async def get_dm(self, members):
        for member in members:
            for role in member.roles:
                if role.name == self.dm_role:
                    return member
        return None


def build_embed(rolls, mention, string):
    if len(rolls) == 1:
        title = f"{mention} rolled "

        # [("dice_str", [rolls])]
        info = rolls[0].roll_info()

        title += (
            "a die:"
            if len(info) == 1 and len(info[0][1]) == 1
            else "some dice:"
        )
        message = rolls[0].full_str()
    else:
        title = f"{mention} rolled `{string.strip()}`"
        message = roll.rolls_string(rolls)

    message = f"```{message}```"

    embed = discord.Embed(description=message, title=title)

    return embed


def stats_embed(data, mention):
    results = {}
    for string, result in data:
        _, die = string.split("d")
        die = int(die)
        rolls = [int(r) for r in result.split(",")]
        if die in results:
            results[die].extend(rolls)
        else:
            results[die] = rolls

    embed = discord.Embed(description=f"Roll stats for {mention}")
    for die in [4, 6, 8, 10, 12, 20]:
        rolls = results.get(die, [])
        die_avg = (die + 1) / 2
        avg = round(sum(rolls) / len(rolls), 1) if rolls else 0
        delta = round(avg - die_avg, 1) if rolls else 0
        delta_string = (
            f"+{delta}" if delta > 0 else str(delta) if delta < 0 else "avg"
        )

        embed.add_field(
            name=f"d{die} ({len(rolls)} rolled)",
            value=f"```{avg} ({delta_string})```",
            inline=True,
        )

        try:
            del results[die]
        except KeyError:
            pass

    other = 0
    for r in results:
        other += len(results[r])
    embed.set_footer(text=f"{other} other die rolled.")

    return embed
