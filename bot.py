import discord
from scryfall import get_uri

TOKEN = 'NTA2MzU4MTk1NDYwMjQzNDU3.Drg-qQ.yeBMOibv_Gk-rRApH7OnS-b2OBI'

client = discord.Client()

@client.event
async def on_message(message):
    print(message.content)

    if message.author == client.user:
        return

    if '[' in message.content and ']' in message.content:
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

        for i in range(0,len(card_names)):
            uri=get_uri(card_names[i])
            if uri:
                img=discord.Embed()
                img.set_image(url=uri)
                await client.send_message(message.channel,embed=img)
            else:
                await client.send_message(message.channel,content='Card not found :\'(')
        
        print(card_names)
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

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run(TOKEN)