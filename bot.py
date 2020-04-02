#Requires Python 3.6

import discord #Run bot
import scryfall #API call functions
import time # Use sleep to time some things
import xkcd # Get xkcd comics, update database
import roll # Roll dice
import threading # Update xkcds regularly on seperate thread
import asyncio # Used to run database updates
import utilities # Send formatted log messages, load configuration file
import wordart # Create word out of emojis
import random # Send one of four images at random

client = discord.Client() # Create the client.
config = utilities.load_config()
if config['mcserv']:
    import mcserv # Optional Paramiko dependancy.
    mcserv_handler = mcserv.CommandHandler(config['mcserv_config'])

@client.event
async def on_message(message):
    if message.content:
        print(message.author.name+': '+message.content)
    else:
        print(message.author.name+' sent an attachment.')

    #If we sent this message, do nothing
    if message.author == client.user:
        return

    #Handles card tags
    if config['scryfall'] and '[' in message.content and ']' in message.content:
        queries = scryfall.get_queries(message.content) # A list of query objects
        for query in queries:
            found = query.found # Grab whatever we found, resolving the query in the process
            if type(found) == str: # If it's just a string message, send it
                await message.channel.send(content = found)
            else: # If it's a card object, grab the message and send it
                for face in found.embed:
                    await message.channel.send(embed = face)
    if config['xkcd'] and message.content.startswith('--xkcd'): # If the user wants an xkcd comic
        query = message.content[6:] # Everything except --xkcd
        if query:
            if query[0] == ' ': # They may have put a space before their query
                query = query[1:]
            data = xkcd.get_xkcd(query) # Returns name,uri,alttext
            msg = data[0]
            img = discord.Embed().set_image(url = data[1])
            await message.channel.send(embed = img, content = msg)
            msg = data[2]
            await message.channel.send(content = msg)
        else:
            msg = 'Use "--xkcd comic name" to find an xkcd comic. Approximate names should be good enough.'
            await message.channel.send(msg)
    elif message.content.startswith('--roll'):
        resp = roll.handle_command(message.content[6:], message.author.mention)
        try:
            await message.channel.send(content = resp)
        except discord.errors.HTTPException: # Message was too long for HTTP request
            await message.channel.send(content = 'Sorry, roll too long to send.')
    elif message.content.startswith('--dmroll') or message.content.startswith('--gmroll'):
        result = roll.handle_command(message.content[8:], message.author.nick)
        if result == 'Invalid format.':
            await message.channel.send(result)
        else:
            for member in message.guild.members:
                for role in member.roles:
                    if role.name == config['dm_role']:
                        try:
                            await member.send(result)                            
                            if message.author != member:
                                await message.author.send(result)
                        except discord.errors.HTTPException:
                            await message.channel.send(content = 'Sorry, roll too long to send.')
                        return
            await message.channel.send('No DM found!')
    elif message.content.startswith('--weeb'):
        img = discord.Embed()
        img.set_image(url = 'https://i.imgur.com/mzbvy4b.png')
        await message.channel.send(embed = img)
    elif any(word in message.content.lower() for word in ['jojo', 'stardust', 'yare', 'daze', 'jotaro', 'joestar']):
        img = discord.Embed()
        img.set_image(url = 'https://i.imgur.com/mzbvy4b.png')
        await message.channel.send(content = f'{message.author.mention}, there\'s something you should know.')
        await message.channel.send(embed = img)
    elif message.content.startswith('--reverse'):
        img = discord.Embed() 
        img.set_image(url = random.choice(['https://i.imgur.com/yXEiYQ4.png', 'https://i.imgur.com/CSuB3ZW.png', 'https://i.imgur.com/3WDcYbV.png', 'https://i.imgur.com/IxDEdxW.png']))
        await message.channel.send(embed = img)
    elif message.content.startswith('--vw'):
        string = message.content[4:].strip()
        if string == '':
            await message.channel.send('Usage: --vw message to vaporwave')
        else:
            await message.channel.send(content = wordart.vaporwave(message.content[4:].strip()))
    elif message.content.startswith('--wa'):
        string = message.content[4:].lower().strip()
        if string == '':
            await message.channel.send('Usage: --wa message to create word art.\nMessages must be very short: around 6 characters.')
        else:
            try:
                await message.channel.send(content = wordart.handle_wordart_request(string, config['wordart_emoji']))
            except discord.errors.HTTPException: # Message was too long for HTTP request
                await message.channel.send(content = 'Sorry, message too long.')
    elif config['mcserv'] and message.content.startswith('--minecraft'):
        command = message.content[11:].strip()
        sender = str(message.author)
        response = mcserv_handler.handle_command(command, sender)
        await message.channel.send(content = response)
    elif message.content.startswith('--'): # Handles commands (--)
        if message.content.startswith('--about'): #Info
            msg = "Hi, I'm Owen's bot! I help by finding magic cards for you, among other things! Try --all, and message Owen if anything is acting up."
        elif message.content.startswith('--all'): #List all commands
            msg = 'All commands:\n\n\t--about\n\t--all\n\t--hello\n\t--help\n\t--minecraft\n\t--no\n\t--reverse\n\t--syntax\n\t--vw\n\t--wa\n\t--weeb\n\t--xkcd'
        elif message.content.startswith('--easteregg'): #Easter egg
            msg = 'Smartarse'
        elif message.content.startswith('--hello'): #Hello World
            msg = f'Greetings, {message.author.mention}'
        elif message.content.startswith('--help'): #Offer assistance
            msg = 'Use [Card Name] to call me! Try --all or --syntax for more info.'
        elif message.content.startswith('--syntax'): #Breakdown of bot syntax
            msg = 'Syntax overview:\n\n\tCall a --command.\n\tFind a [card] like this.\n\tFind a specific [printing|like this]\n\tGet a [random] card.'
        elif message.content.startswith('--no'):
            msg = wordart.no
        else: #Otherwise, their command is invalid
            msg = 'What\'s this? I don\'t understand that! Maybe try --help'
        await message.channel.send(msg)
    elif config['creeper'] and 'creeper' in message.content.lower():
        colour = discord.Colour.from_rgb(13, 181, 13)
        embed = discord.Embed(title = 'Awww mannn', url = 'https://www.youtube.com/watch?v=cPJUBQd-PNM', colour = colour) # link to "revenge" Minecraft parody
        await message.channel.send(embed = embed)

@client.event
async def on_voice_state_update(old, new): #When a user joins a voice channel
    if new == client.user: #If it was this, ignore
        return
    
    chnl = new.voice.voice_channel #Voice channel person joined

    if chnl: #If they didn't leave a channel
        if chnl == old.voice_channel: #If they are in the same channel
            if new.voice.self_deaf:
                print(new.name + ' deafened themself')
            elif new.voice.self_mute:
                print(new.name + ' muted themself')
        else:
            print(new.name + ' joined ' + str(chnl)) #Print the channel and user
            if config['announcer']:    
                vc = await client.join_voice_channel(new.voice.voice_channel) #Join the voice channel they joined
                player = vc.create_ffmpeg_player('resources/user_joined.mp3') #Create player
                utilities.log_message('Played user_joined.mp3 in ' + str(new.voice.voice_channel))
                player.start() #Play sound
                time.sleep(2) #Wait for sound to finish
                await vc.disconnect() #Leave
    else:
        if old.voice.voice_channel.voice_members: # Only play sound if the channel still has people in it
            print(old.name + ' left ' + str(old.voice.voice_channel)) #Announce that someone left
            if config['announcer']:
                vc = await client.join_voice_channel(old.voice.voice_channel)
                player = vc.create_ffmpeg_player('resources/user_left.mp3')
                utilities.log_message('Played user_left.mp3 in ' + str(old.voice.voice_channel))
                player.start()
                time.sleep(2)
                await vc.disconnect()

def update_xkcds_schedule(period): # This will update the xkcd database regularly.
    while True:
        asyncio.new_event_loop().run_until_complete(xkcd.update_db())
        time.sleep(period)

#Startup notification
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('---LOG---')
    if config['xkcd']:
        threading.Thread(target = update_xkcds_schedule, args = [config['xkcd_interval']]).start() # Regular event to update xkcd database

client.run(config['token']) #Connect
