import json

def translate(string, emoji):
    """string: alpha string to translate. emoji: discord formatted emoji reference: i.e. <:emojiname:000000000000000000>"""
    
    with open('resources/alphabet.json', 'r') as f:
        alphabet = json.load(f)

    letters = []

    for c in string:
        if not c in alphabet:
            return f'Sorry, character {c} not available, only letters can be used.'
        letters.append(alphabet[c])

    output = ''

    for line in range(5):
        for letter in letters:
            output += letter[line].replace('?', emoji).replace(' ', '      ')
            output += '    '
        output += '\n'

    return output

def vaporwave(string):
    normal = u' 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~'
    wide = u'　０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ！゛＃＄％＆（）＊＋、ー。／：；〈＝〉？＠［\\］＾＿‘｛｜｝～'
    widemap = dict((ord(x[0]), x[1]) for x in zip(normal, wide))

    return string.translate(widemap)

# String sent as message.
no = '<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735><:urarakagun:637516402885918735><:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735><:urarakagun:637516402885918735>        <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>        <:urarakagun:637516402885918735><:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735>             <:urarakagun:637516402885918735>\n<:urarakagun:637516402885918735>                     <:urarakagun:637516402885918735>    <:urarakagun:637516402885918735><:urarakagun:637516402885918735><:urarakagun:637516402885918735>'
