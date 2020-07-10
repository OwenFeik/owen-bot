import json
import re
import emoji

def translate(string, replacement):
    """string: alpha string to translate. emoji: discord formatted emoji reference: i.e. <:emojiname:000000000000000000>"""
    
    with open('resources/alphabet.json', 'r') as f:
        alphabet = json.load(f)

    letters = []

    for c in string.lower():
        if not c in alphabet:
            return f'Sorry, character {c} not available, only letters can be used.'
        letters.append(alphabet[c])

    output = ''

    for line in range(5):
        for letter in letters:
            output += letter[line].replace(' ', '      ').replace('?', replacement)
            output += '    '
        output += '\n'

    return output

def handle_wordart_request(string, default_emoji):
    character = re.search(r'<:[\w]+:[\d]{18}>', string) # Matches discord emojis (<:name:000000000000000000>)
    if character:
        character = character.group(0).strip()
        string = string.replace(character, '').strip()
    else:
        for c in string:
            if c in emoji.UNICODE_EMOJI:
                character = c
                string = string.replace(c, '').strip()
                break
        else:
            character = default_emoji

    return translate(string, character)

def vaporwave(string):
    normal = u' 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~'
    wide = u'　０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ！゛＃＄％＆（）＊＋、ー。／：；〈＝〉？＠［\\］＾＿‘｛｜｝～'
    widemap = dict((ord(x[0]), x[1]) for x in zip(normal, wide))

    return string.translate(widemap)

# String sent as message.
no = '<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735><:urarakagun:637516402885918735><:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735><:urarakagun:637516402885918735>        <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>        <:urarakagun:637516402885918735><:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735><:urarakagun:637516402885918735><:urarakagun:637516402885918735>'
