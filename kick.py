import time
import asyncio

import discord

class CommandHandler():
    def __init__(self, interval=600, required_votes=3, 
        kick_message='Democracy is a beautiful thing.'):

        self.interval = interval
        self.required_votes = required_votes
        self.votes = [] # [(id, time, sender), (id, time, sender)]
        self.kick_message = kick_message

    async def handle_command(self, message):
        self.scrub_votes()
        if message.mentions:
            if len(message.mentions) > 1:
                return 'I can only kick one person at a time!'
            user = message.mentions[0]

            self.add_vote(user.id, message.author.id)
            vote_count = self.vote_count(user.id)
            if vote_count >= self.required_votes:
                try:
                    await user.move_to(None, reason=self.kick_message)
                except discord.Forbidden:
                    return 'Tragically, I don\'t have permission to do that.'
                
                self.scrub_votes(user)
                return 'The council has spoken. ' + \
                    f'{user.mention} has been disconnected.'
            else:
                needed_votes = self.required_votes - vote_count
                return f'Vote received! {needed_votes} more votes required.'
        else:
            return 'Usage: "--kick <mention>" e.g. "--kick @BadPerson".'
    
    def add_vote(self, target_id, author_id):
        self.votes = [v for v in self.votes if \
            not (v[0] != target_id and v[2] != author_id)]
        self.votes.append((target_id, time.time(), author_id))

    def scrub_votes(self, user_id=None):
        t = time.time()
        self.votes = [v for v in self.votes if t - v[1] < self.interval]
        if user_id is not None:
            self.votes = [v for v in self.votes if v[0] != user_id]

    def vote_count(self, user_id):
        count = 0
        for v in self.votes:
            if v[0] == user_id:
                count += 1

        return count
