#Requires Python 3.6

import discord #Run bot
from scryfall import get_uri,get_random_uri,get_similar,get_random_from_set,get_printing #API call functions
from time import sleep #Play sound for an appropriate length of time
from xkcd import get_xkcd,update_db # Get xkcd comics

#Get the client token
with open('token.txt', 'r') as f:
    token = f.read()

#Start the client.
client = discord.Client()

#Capitalise a card name
def capitalise(name):
    out=''
    for i in range(0,len(name)): #For each character
        if (name[i].isalnum() and not name[i-1].isalnum()) or i==0: #If it's a letter preceded by a non-letter
            out+=name[i].capitalize() #Add the capital version to the out string
        else: #Otherwise, just normal character
            out+=name[i] #To out string
    return out

@client.event
async def on_message(message):
    if message.content:
        print(message.author.name+': '+message.content)
    else:
        print(message.author.name+' sent an attachment.')

    chnl=message.channel

    #If we sent this message, do nothing
    if message.author == client.user:
        return

    #Handles card tags
    if '[' in message.content and ']' in message.content:
        
        #Iterate through the message to find all card names
        card_names=[]
        is_query=False
        is_set=False
        card_name=''
        set_name=''
        for c in message.content: #Iterate through characters in the string
            if c=='[': #Card tags are [] [ is the open tag
                is_query=True
            elif c==']': #Close the card tag
                is_query=False
                is_set=False
                if card_name: #This means either the end of a card name
                    card_names.append(card_name)
                    card_name=''
                elif set_name: #Or the end of the set name.
                    card_names[len(card_names)-1]=[card_names[len(card_names)-1],set_name]
                    set_name=''
            elif c=='|': #This indicates there is a set
                is_query=False
                is_set=True
                card_names.append(card_name) #A set means the end of the card name
                card_name=''
            elif is_set:
                set_name+=c
            elif is_query:
                card_name+=c

        #Find images and send one or more messages for each card.
        for card in card_names:
            #If it's a list, the request specified an edition
            if type(card)==list:
                name=card[0].lower()
                ed=card[1].upper()
            else:
                name=card.lower()
                ed=''
            
            #If an edition was specified
            if ed:
                if name=='random': #If they want random, get random card.
                    data=get_random_from_set(ed)
                    if data:
                        messages=data.message
                        for msg in messages:
                            await client.send_message(chnl,embed=msg[0],content=msg[1])
                    else: #If we don't get a uri, the search failed and the set doesn't exist.
                        await client.send_message(message.channel,content=f"Couldn't find set {ed} :cry:")
                else: #Otherwise, they want a specific card
                    found,data=get_printing(name,ed) #Found is an indicator of what the call found, data is the data
                    if found=='card': #If we found a card
                        messages=data.message
                        for msg in messages:
                            await client.send_message(chnl,embed=msg[0],content=msg[1])
                    elif found=='suggs': #If we got a list of suggestions.
                        print(f'LOG> Failed to find {name} in {ed}')
                        msg=f"Couldn't find {capitalise(name)}. Maybe you meant:\n\n" 
                        for name in data: #Add them to a nicely formatted string
                            msg+='\t'+name+'\n'
                        print('LOG> Found alternatives.')
                        await client.send_message(message.channel,content=msg[0:len(msg-1)]) #Last char is a newline
                    else: #We didn't get a card or a list of suggestions
                        print(f'LOG> Failed to find {name} in {ed}')
                        await client.send_message(message.channel,content=f'{capitalise(name)} not found in {ed} :cry:')

            else: #No edition was specified
                if name=='random': #If they want a random card
                    data=get_random_uri()
                    messages=data.message
                    for msg in messages:
                        await client.send_message(chnl,embed=msg[0],content=msg[1])
                elif name=='best card' or name=='the best card': #Kalonian Hydra is the best card.
                    data=get_uri('Kalonian Hydra')
                    messages=data.message
                    for msg in messages:
                        await client.send_message(chnl,embed=msg[0],content='Kalonian Hydra is the best card.')
                    print('LOG> Kalonian Hydra is the best card.')
                else: #Just a normal card search
                    cards=get_uri(name)
                    if cards: #If we found a card
                        messages=cards.message
                        for msg in messages:
                            await client.send_message(chnl,embed=msg[0],content=msg[1])
                        print(f'LOG> Found {cards.name}')
                    else: #No card was found
                        print(f'LOG> Failed to find {name}')
                        suggs=get_similar(name) #Find a list of similarly named cards
                        if suggs: #If we got some suggestions
                            msg=f"Couldn't find {capitalise(name)}. Maybe you meant:\n\n" 
                            for name in suggs: #Format suggestions nicely
                                msg+='\t'+name+'\n'
                            print('LOG> Found alternatives.')
                            await client.send_message(message.channel,content=msg[0:len(msg)-1])
                        else:
                            await client.send_message(message.channel,content=capitalise(name)+' not found :cry:')

    if message.content.startswith('--xkcd'): # If the user wants an xkcd comic
        query=message.content[6:] # Everything except --xkcd
        if query[0]==' ': # They may have put a space before their query
            query=query[1:]
        if query=='update': # Allow xkcd database to be updated via discord call
            update_db()
        else:    
            data=get_xkcd(query) # Returns name,uri,alttext
            msg=data[0]
            img=discord.Embed().set_image(url=data[1])
            await client.send_message(message.channel,embed=img,content=msg)
            msg=data[2]
            await client.send_message(message.channel,content=msg)
    elif message.content.startswith('--'): # Handles commands (--)
        if message.content.startswith('--about'): #Info
            msg="Hi, I'm Owen's bot! I help by finding magic cards for you and playing noises! Message Owen if anything is acting up."
        elif message.content.startswith('--all'): #List all commands
            msg='All commands:\n\n\t--about\n\t--all\n\t--hello\n\t--help\n\t--syntax'
        elif message.content.startswith('--easteregg'): #Easter egg
            msg='Smartarse'
        elif message.content.startswith('--hello'): #Hello World
            msg=f'Greetings, {message.author.mention}'
        elif message.content.startswith('--help'): #Offer assistance
            msg='Use [Card Name] to call me! Try --all or --syntax for more info.'
        elif message.content.startswith('--syntax'): #Breakdown of bot syntax
            msg='Syntax overview:\n\n\tFind a [card] like this.\n\tFind a specific [printing|like this]\n\tGet a [random] card.\n\tCall a --command.'
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
            print('Played user_joined.mp3 in '+str(new.voice.voice_channel))
            player.start() #Play sound
            sleep(2) #Wait for sound to finish
            await vc.disconnect() #Leave
    else:
        print(old.name+' left '+str(old.voice.voice_channel)) #Announce that someone left
        vc=await client.join_voice_channel(old.voice.voice_channel)
        player=vc.create_ffmpeg_player('user_left.mp3')
        print('Played user_left.mp3 in '+str(old.voice.voice_channel))
        player.start()
        sleep(2)
        await vc.disconnect()
        

#Startup notification
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('---LOG---')

client.run(token) #Connect
