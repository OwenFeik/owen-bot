import utilities

import discord

async def get_member(guild, member_id):
    member = guild.get_member(member_id)
    if member is None:
        try:
            member = await guild.fetch_member(member_id)
        except discord.Forbmember_idden as e:
            utilities.log_message(
                'Got forbidden when searching for member '
                f'{member_id} in guild "{guild.name}": {e}'
            )
        except discord.HTTPException as e:
            utilities.log_message(
                f'Failed to find member {member_id} in {guild.name}: {e}'
            )
        if member is None:
            raise ValueError('Couldn\'t find a member for this id.')
    return member

def is_guild_owner(guild, member_id):
    return (guild.owner and guild.owner.id == member_id) or \
        guild.owner_id == member_id
