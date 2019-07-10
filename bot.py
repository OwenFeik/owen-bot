#Requires Python 3.6

import discord #Run bot
from scryfall import get_queries #API call functions
from time import sleep #Play sound for an appropriate length of time
import xkcd # Get xkcd comics, update database
from threading import Timer,Thread # Update xkcds every 24 hours
import asyncio # Used to run database updates
from utilities import log_message,load_config # Send formatted log messages

client=discord.Client() # Create the client.
config=load_config()

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
        queries=get_queries(message.content) # A list of query objects
        for query in queries:
            found=query.found # Grab whatever we found, resolving the query in the process
            if type(found)==str: # If it's just a string message, send it
                await message.channel.send(content=found)
            else: # If it's a card object, grab the message and send it
                found=found.embed
                for face in found:
                    # await message.channel.send(embed=face[0],content=face[1])
                    await message.channel.send( embed = face)

    if config['xkcd'] and message.content.startswith('--xkcd'): # If the user wants an xkcd comic
        query=message.content[6:] # Everything except --xkcd
        if query:
            if query[0]==' ': # They may have put a space before their query
                query=query[1:]
            data=xkcd.get_xkcd(query) # Returns name,uri,alttext
            msg=data[0]
            img=discord.Embed().set_image(url=data[1])
            await message.channel.send(embed=img,content=msg)
            msg=data[2]
            await message.channel.send(content=msg)
        else:
            msg='Use "--xkcd comic name" to find an xkcd comic. Approximate names should be good enough.'
            await message.channel.send(msg)
    elif message.content.startswith('--'): # Handles commands (--)
        if message.content.startswith('--about'): #Info
            msg="Hi, I'm Owen's bot! I help by finding magic cards for you! Message Owen if anything is acting up."
        elif message.content.startswith('--all'): #List all commands
            msg='All commands:\n\n\t--about\n\t--all\n\t--hello\n\t--help\n\t--syntax\n\t--xkcd'
        elif message.content.startswith('--easteregg'): #Easter egg
            msg='Smartarse'
        elif message.content.startswith('--hello'): #Hello World
            msg=f'Greetings, {message.author.mention}'
        elif message.content.startswith('--help'): #Offer assistance
            msg='Use [Card Name] to call me! Try --all or --syntax for more info.'
        elif message.content.startswith('--syntax'): #Breakdown of bot syntax
            msg='Syntax overview:\n\n\tCall a --command.\n\tFind a [card] like this.\n\tFind a specific [printing|like this]\n\tGet a [random] card.'
        else: #Otherwise, their command is invalid
            msg='OwO, what\'s this? I don\'t understand that! Maybe try --help'
        await message.channel.send(msg)


@client.event
async def on_voice_state_update(old,new): #When a user joins a voice channel
    if new==client.user: #If it was this, ignore
        return
    
    chnl=new.voice.voice_channel #Voice channel person joined

    if chnl: #If they didn't leave a channel
        if chnl==old.voice_channel: #If they are in the same channel
            if new.voice.self_deaf:
                print(new.name+' deafened themself')
            elif new.voice.self_mute:
                print(new.name+' muted themself')
        else:
            print(new.name+' joined '+str(chnl)) #Print the channel and user
            if config['announcer']:    
                vc=await client.join_voice_channel(new.voice.voice_channel) #Join the voice channel they joined
                player=vc.create_ffmpeg_player('resources/user_joined.mp3') #Create player
                log_message('Played user_joined.mp3 in '+str(new.voice.voice_channel))
                player.start() #Play sound
                sleep(2) #Wait for sound to finish
                await vc.disconnect() #Leave
    else:
        if old.voice.voice_channel.voice_members: # Only play sound if the channel still has people in it
            print(old.name+' left '+str(old.voice.voice_channel)) #Announce that someone left
            if config['announcer']:
                vc=await client.join_voice_channel(old.voice.voice_channel)
                player=vc.create_ffmpeg_player('resources/user_left.mp3')
                log_message('Played user_left.mp3 in '+str(old.voice.voice_channel))
                player.start()
                sleep(2)
                await vc.disconnect()


def update_xkcds_schedule(period): # This will update the xkcd database regularly.
    asyncio.new_event_loop().run_until_complete(xkcd.update_db())
    next_day_event=Timer(period,update_xkcds_schedule,period)
    next_day_event.start()

#Startup notification
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('---LOG---')
    if config['xkcd']:
        Thread(target=update_xkcds_schedule,args=[config['xkcd_interval']]).start() # Regular event to update xkcd database

client.run(config['token']) #Connect