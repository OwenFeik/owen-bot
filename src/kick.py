import time

import discord

import commands

class Kick(commands.Command):
    def __init__(self, config):
        super().__init__(config)
        self.commands = ['--kick']
        self.interval = config['kick_interval']
        self.votes = []
        self.cooldown = []

    async def handle(self, message):
        self.scrub_votes()
        self.scrub_cooldown()
        
        if not message.mentions:
            return 'Usage: "--kick <mention>" e.g. "--kick @BadPerson".'
        if len(message.mentions) > 1:
            return 'I can only kick one person at a time!'
        target = message.mentions[0]

        if type(target) != discord.Member:
            return 'Sorry, I can\'t find voice information for ' + \
                f'{target.display_name}.'

        if self.on_cooldown(target):
            return f'{target.display_name} has been kicked too recently. ' + \
                'I only kick people at most once every '+ \
                f'{self.interval // 60} minutes.'

        if target.voice is None:
            return f'{target.display_name} isn\'t in a voice channel.'
        if message.author.voice is None:
            return 'You can\'t kick people you aren\'t ' + \
                'in a voice channel with!'

        channel = target.voice.channel
        if channel is None or channel != message.author.voice.channel:
            return 'You can\'t kick people you aren\'t ' + \
                'in a voice channel with!'

        voice_members = sum([1 if not m.bot else 0 for m in channel.members])
        if voice_members < 3:
            return 'Sorry, I don\'t kick people from voice channels ' + \
                'with less than 3 members.'
        required_votes = int(voice_members / 2 + 1)

        self.add_vote(target, message.author, channel)
        vote_count = self.vote_count(target, channel)

        if vote_count >= required_votes:
            try:
                await target.move_to(None, 
                    reason='Democracy is a beautiful thing.')
                self.cooldown.append((target, time.time()))
            except discord.Forbidden:
                return 'Tragically, I don\'t have permission to do that.'
            
            self.scrub_votes(target)
            return 'The council has spoken. ' + \
                f'{target.mention} has been disconnected.'
        else:
            needed_votes = required_votes - vote_count
            return f'Vote received! {needed_votes} more votes required.'            
    
    def add_vote(self, target, sender, channel):
        vote = Vote(target, sender, channel)
        self.votes = [v for v in self.votes if not v.redundant(vote)]
        self.votes.append(vote)

    def scrub_cooldown(self):
        t = time.time()
        self.cooldown = [(tg, tm) for tg, tm in self.cooldown if \
            t - tm < self.interval]

    def on_cooldown(self, user):
        for c in self.cooldown:
            if user in c:
                return True
        return False

    def scrub_votes(self, user=None):
        t = time.time()
        self.votes = [v for v in self.votes if not v.expired(self.interval, t)]
        if user is not None:
            self.votes = [v for v in self.votes if v.target != user.id]

    def vote_count(self, target, channel):
        count = 0
        for v in self.votes:
            if v.target == target.id and v.channel == channel.id:
                count += 1

        return count

class Vote():
    def __init__(self, target, sender, channel):
        self.target = target if type(target) == int else target.id
        self.sender = sender if type(sender) == int else sender.id
        self.channel = channel if type(channel) == int else channel.id
        self.created = time.time()

    def __repr__(self):
        return f'<Vote to kick {self.target} at {self.created}' + \
            f' from {self.sender} in {self.channel}>'

    def redundant(self, other):
        return (
            self.target == other.target and \
            self.sender == other.sender and \
            self.channel == other.channel
        )

    def expired(self, interval, t=None):
        if t is None:
            t = time.time()
        return t - self.created > interval
