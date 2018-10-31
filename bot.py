#TODO syntax command
#TODO user joined your channel

import discord
from random import shuffle
from scryfall import get_uri,get_random_uri,get_similar,get_random_from_set,get_printing

#Get the client token
with open('token.txt', 'r') as f:
    token = f.read()

#Start the client.
client = discord.Client()

#Capitalise a card name
def capitalise(name):
    out=''
    for i in range(0,len(name)):
        if (name[i].isalnum() and not name[i-1].isalnum()) or i==0:
            out+=name[i].capitalize()
        else:
            out+=name[i]
    return out

@client.event
async def on_message(message):
    print(message.content)

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
        for c in message.content:
            if c=='[':
                is_query=True
            elif c==']':
                is_query=False
                is_set=False
                if card_name:
                    card_names.append(card_name)
                    card_name=''
                elif set_name:
                    card_names[len(card_names)-1]=[card_names[len(card_names)-1],set_name]
                    set_name=''
            elif c=='|':
                is_query=False
                is_set=True
                card_names.append(card_name)
                card_name=''
            elif is_set:
                set_name+=c
            elif is_query:
                card_name+=c

                #[nightmare|m15]

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
                    uri=get_random_from_set(ed)
                    if uri:
                        img=discord.Embed().set_image(url=uri)
                        await client.send_message(message.channel,embed=img)
                    else: #If we don't get a uri, the search failed and the set doesn't exist.
                        await client.send_message(message.channel,content=f"Couldn't find set {ed} :cry:")
                else:
                    found,data=get_printing(name,ed)
                    if found=='card':
                        for uri in data:
                            img=discord.Embed().set_image(url=uri)
                            print(f'Found {uri}')
                            await client.send_message(message.channel,embed=img)
                    elif found=='suggs':
                        print(f'Failed to find {capitalise(name)} in {ed}')
                        if len(data)>5:
                            data=shuffle(data)[0:5].sort()
                        msg=f"Couldn't find {capitalise(name)}. Maybe you meant:\n" 
                        for name in data:
                            msg+=name+'\n'
                        print('Found alternatives.')
                        await client.send_message(message.channel,content=msg[0:len(msg-1)])
                    else:
                        print(f'Failed to find {capitalise(name)} in {ed}')
                        await client.send_message(message.channel,content=f'{capitalise(name)} not found in {ed} :cry:')

            else:
                if name=='random':
                    img=discord.Embed()
                    img.set_image(url=get_random_uri())
                    await client.send_message(message.channel,embed=img)
                elif name=='best card' or name=='the best card':
                    img=discord.Embed().set_image(url=get_uri('Kalonian Hydra')[0])
                    await client.send_message(message.channel,embed=img)
                    print('Kalonian Hydra is the best card.')
                else:
                    uris=get_uri(name)
                    if uris:
                        for uri in uris:
                            img=discord.Embed().set_image(url=uri)
                            print(f'Found {uri}')
                            await client.send_message(message.channel,embed=img)
                    else:
                        print(f'Failed to find {capitalise(name)}')
                        suggs=get_similar(name)
                        if suggs:
                            if len(suggs)>5:
                                shuffle(suggs)
                                suggs=suggs[0:5]
                            msg=f"Couldn't find {capitalise(name)}. Maybe you meant:\n\n" 
                            for name in suggs:
                                msg+='\t'+name+'\n'
                            print('Found alternatives.')
                            await client.send_message(message.channel,content=msg[0:len(msg)-1])
                        else:
                            await client.send_message(message.channel,content=capitalise(name)+' not found :cry:')

    #Handles commands (--)
    if message.content.startswith('--'):
        if message.content.startswith('--hello'):
            msg=f'Greetings, {message.author.mention}'
        elif message.content.startswith('--help'):
            msg='Use [Card Name] to call me!'
        elif message.content.startswith('--easteregg'):
            msg='Smartarse'
        elif message.content.startswith('--all'):
            msg='All commands:\n--all\n--hello\n--help'
        else:
            msg='OwO, what\'s this? I don\'t understand that! Maybe try --help'
        await client.send_message(message.channel,msg)

#Startup notification
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('---LOG---')

#Connect
client.run(token)