import time
import asyncio

import discord

class CommandHandler():
    def __init__(self, interval=600, required_votes=3, 
        kick_message='Democracy is a beautiful thing.'):

        self.interval = interval
        self.required_votes = required_votes
        self.votes = [] # [(id, time), (id, time), (id, time)]
        self.kick_message = kick_message

    async def handle_command(self, message):
        self.scrub_votes()
        if message.mentions:
            if len(message.mentions) > 1:
                return 'I can only kick one person at a time!'
            user = message.mentions[0]

            self.votes.append((user.id, time.time()))
            vote_count = self.vote_count(user) 
            if vote_count >= self.required_votes:
                try:
                    await user.move_to(None, reason=self.kick_message)
                except discord.Forbidden:
                    return 'Tragically, I don\'t have permission to do that.'
                
                self.scrub_votes(user)
                return 'The council has spoken.' + \
                    f'{user.mention} has been disconnected.'
            else:
                needed_votes = self.required_votes - vote_count
                return f'Vote received! {needed_votes} more votes required.'
        else:
            return 'Usage: "--kick <mention>" e.g. "--kick @BadPerson".'
            
    def scrub_votes(self, user=None):
        t = time.time()
        self.votes = [v for v in self.votes if t - v[1] < self.interval]
        if user:
            self.votes = [v for v in self.votes if v[0] != user.id]

    def vote_count(self, user):
        count = 0
        for v in self.votes:
            if v[0] == user.id:
                count += 1

        return count
