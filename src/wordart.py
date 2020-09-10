import json
import re

import discord
import emoji
import utilities

wa_alphabet = {}
def load_wa_alphabet():
    try:
        with open('resources/alphabet.json', 'r') as f:
            wa_alphabet.update(json.load(f))
    except FileNotFoundError:
        utilities.log_message('Failed to load wordart alphabet.')

def translate(string, replacement):
    letters = []

    for c in string.lower():
        if not c in wa_alphabet:
            return f'Sorry, character "{c}" not available, ' + \
                'only letters can be used.'
        letters.append(wa_alphabet[c])

    output = ''

    for line in range(5):
        for letter in letters:
            output += letter[line].replace(' ', '      ').replace('?', replacement)
            output += '    '
        output += '\n'

    return output

def handle_wordart_request(string, default_emoji):
    # Matches discord emojis (<:name:000000000000000000>)
    character = re.search(r'<:[\w]+:[\d]{18}>', string) 
    if character:
        character = character.group(0).strip()
        string = string.replace(character, '').strip()
        return translate(string, character)

    for i in range(len(string)):
        if string[i] in emoji.UNICODE_EMOJI:
            character = string[i]

            # unicode variation characters; applied to some emojis.
            if i < len(string) - 1 and 65024 <= ord(string[i + 1]) <= 65039:
                variation = string[i + 1]
                string = string.replace(variation, '').strip()
            else:
                variation = ''

            string = string.replace(character, '').strip()
            
            character += variation
            break
    else:
        character = default_emoji

    return translate(string, character)

def scrub_mentions(argument, mentions):
    other_mentions = re.findall(r'<(@&|#)\d{16,}>', argument)
    if other_mentions:
        raise ValueError('Sorry, I don\'t really like mentions.')

    discord_emoji = re.findall(r'<:[\w\W]+:\d{16,}>', argument)
    if discord_emoji:
        raise ValueError('Sorry, Discord emotes can\'t be translated.')

    user_mentions = re.findall(r'<@!?\d{16,}>', argument)
    for m in user_mentions:
        user_id = int(m[3:-1]) if m.startswith('<@!') else int(m[2:-1])
        user = discord.utils.find(
            lambda m, i=user_id: m.id == i,
            mentions
        )

        if user:
            argument = argument.replace(m, user.display_name)
        else:
            raise ValueError('Sorry, I don\'t really like mentions.')
    
    return argument

def vaporwave(string):
    normal = u' 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~'
    wide = u'　０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ！゛＃＄％＆（）＊＋、ー。／：；〈＝〉？＠［\\］＾＿‘｛｜｝～'
    widemap = dict((ord(x[0]), x[1]) for x in zip(normal, wide))

    return string.translate(widemap)

def blackletter(string):
    normal = u' 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~'
    gothic = u' 0123456789𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~'
    gothicmap = {ord(n): g for n, g in zip(normal, gothic)}

    return string.translate(gothicmap)

# String sent as message.
no = '<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735><:urarakagun:637516402885918735><:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735><:urarakagun:637516402885918735>        <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>        <:urarakagun:637516402885918735><:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735><:urarakagun:637516402885918735><:urarakagun:637516402885918735>'
