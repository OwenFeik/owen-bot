#Requires Python 3.6

import discord #Run bot
from scryfall import get_queries #API call functions
from time import sleep #Play sound for an appropriate length of time
from xkcd import get_xkcd,update_db # Get xkcd comics
from threading import Timer,Thread # Update xkcds every 24 hours
import asyncio # Used to run database updates

client = discord.Client() #Create the client.

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
    if '[' in message.content and ']' in message.content:
        queries=get_queries(message.content) # A list of query objects
        for query in queries:
            found=query.found # Grab whatever we found, resolving the query in the process
            if type(found)==str: # If it's just a string message, send it
                await client.send_message(message.channel,content=found)
            else: # If it's a card object, grab the message and send it
                found=found.message
                for face in found:
                    await client.send_message(message.channel,embed=face[0],content=face[1])

    if message.content.startswith('--xkcd'): # If the user wants an xkcd comic
        query=message.content[6:] # Everything except --xkcd
        if query:
            if query[0]==' ': # They may have put a space before their query
                query=query[1:]
            data=get_xkcd(query) # Returns name,uri,alttext
            msg=data[0]
            img=discord.Embed().set_image(url=data[1])
            await client.send_message(message.channel,embed=img,content=msg)
            msg=data[2]
            await client.send_message(message.channel,content=msg)
        else:
            msg='Use "--xkcd comic name" to find an xkcd comic. Approximate names should be good enough.'
            await client.send_message(message.channel,msg)
    elif message.content.startswith('--'): # Handles commands (--)
        if message.content.startswith('--about'): #Info
            msg="Hi, I'm Owen's bot! I help by finding magic cards for you and playing noises! Message Owen if anything is acting up."
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
        await client.send_message(message.channel,msg)


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
            vc=await client.join_voice_channel(new.voice.voice_channel) #Join the voice channel they joined
            player=vc.create_ffmpeg_player('user_joined.mp3') #Create player
            print('LOG> Played user_joined.mp3 in '+str(new.voice.voice_channel))
            player.start() #Play sound
            sleep(2) #Wait for sound to finish
            await vc.disconnect() #Leave
    else:
        if old.voice.voice_channel.voice_members: # Only play sound if the channel still has people in it
            print(old.name+' left '+str(old.voice.voice_channel)) #Announce that someone left
            vc=await client.join_voice_channel(old.voice.voice_channel)
            player=vc.create_ffmpeg_player('user_left.mp3')
            print('LOG> Played user_left.mp3 in '+str(old.voice.voice_channel))
            player.start()
            sleep(2)
            await vc.disconnect()

def update_xkcds_schedule(): # This will update the xkcd database regularly.
    asyncio.new_event_loop().run_until_complete(update_db())
    next_day_event=Timer(3600,update_xkcds_schedule)
    next_day_event.start()

#Startup notification
@client.event
async def on_ready():
    Thread(target=update_xkcds_schedule).start() # Daily event to update xkcd database
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('---LOG---')

try:
    with open('token.txt', 'r') as f: #Get the client token
        token = f.read()
    client.run(token) #Connect
except FileNotFoundError:
    print('Create a token.txt file with your bots authtoken!')
