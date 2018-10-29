import discord
from scryfall import get_uri

@client.event
async def on_message(message):
    print(message.content)

    #If we sent this message, do nothing
    if message.author == client.user:
        return

    #If the message contains a card tag
    if '[' in message.content and ']' in message.content:
        
        #Iterate through the message to find all card names
        card_names=[]
        is_query=False
        card_name=''
        for c in message.content:
            if c=='[':
                is_query=True
            elif c==']':
                is_query=False
                card_names.append(card_name)
                card_name=''
            elif is_query:
                card_name+=c

        #Find and send one or more messages for each card.
        for i in range(0,len(card_names)):
            uris=get_uri(card_names[i])
            if uri:
                for uri in uris:
                    img=discord.Embed()
                    img.set_image(url=uri)
                    print('Found '+uri)
                    await client.send_message(message.channel,embed=img)
            else:
                print('Failed to find '+card_names[i])
                await client.send_message(message.channel,content=card_names[i]+' not found :cry:')

    #Handles commands (--)
    if message.content.startswith('--'):
        if message.content.startswith('--hello'):
            msg=f'Greetings, {message.author.mention}'
        elif message.content.startswith('--help'):
            msg='Use [Card Name] to call me!'
        elif message.content.startswith('--easteregg'):
            msg='Smartarse'
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


#Get the client token
with open('token.txt', 'r') as f:
    token = f.read()

#Start the client.
client = discord.Client()
client.run(token)