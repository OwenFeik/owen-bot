import requests
import difflib
import discord

# More or less copied over from https://github.com/OwenFeik/spells

class Spellbook():
    def __init__(self, spellbook_url):
        self.build_spellbook(spellbook_url)
            
    def build_spellbook(self, spellbook_url):
        try:
            self.spells=[Spell.from_json(spell) for spell in requests.get(spellbook_url).json()]
            self.names=[spell.name for spell in self.spells]
            self._names=[name.lower() for name in self.names] # Used to match queries through difflib
        except:
            raise ValueError

    def get_spell(self,query):
        target=difflib.get_close_matches(query.lower(),self._names,1)
        if target:
            target=self.names[self._names.index(target[0])] # Get the actual name of the spell
        else:
            return None

        for spell in self.spells:
            if spell.name==target:
                return spell
        return None

    def get_spells(self,queries):
        spells=[]
        for spell in queries:
            spells.append(self.get_spell(spell))
        return spells

    def handle_command(self, string):
        spell = self.get_spell(string.strip())
        if spell is None:
            return 'text', f'Sorry, I couldn\'t find {string}.'
        else:
            return 'embed', spell.embed()

class Spell():
    def __init__(self, name, school, level, cast, rnge, components, duration, desc, ritual):
        self.name = name
        self.school = school
        self.level = level
        self.cast = cast
        self.rnge = rnge
        self.components = components
        self.duration = duration
        self.desc = desc
        self.ritual = ritual

    def __str__(self):
        return f'\n{self.name} | {self.school}\n{self.cast} | {self.rnge}{" | Ritual" if self.ritual else ""}\n{self.components} | {self.duration}\n\n{self.desc}\n'

    def embed(self):
        e = discord.Embed (
            title = self.name,
            colour = get_school_colour(self.school),
            description = get_embed_description(self)
        )
        e.add_field(name = 'Casting Time', value = self.cast, inline = True)
        e.add_field(name = 'Range', value = self.rnge, inline = True)
        e.add_field(name = 'Duration', value = self.duration, inline = True)
        e.add_field(name = 'Components', value = self.components, inline = False)
        descs = chunk_spell_desc(self.desc)
        e.add_field(name = 'Description', value = descs[0], inline = False)
        if len(descs) > 1:
            for d in descs[1:]:
                e.add_field(name = u'\u200b', value = d, inline = False)

        return e

    def to_json(self):
        return {
            'name': self.name,
            'school': self.school,
            'level': self.level,
            'cast': self.cast,
            'range': self.rnge,
            'components': self.components,
            'duration': self.duration,
            'description': self.desc,
            'ritual': self.ritual
        }

    @staticmethod
    def from_json(data):
        name = data.get('name', 'N/A')
        school = data.get('school', 'N/A')
        level = data.get('level', -1)
        cast = data.get('cast', 'N/A')
        rnge = data.get('range', 'N/A')
        components = data.get('components', 'N/A')
        duration = data.get('duration', 'N/A')
        desc = data.get('description', 'N/A')
        ritual = data.get('ritual', False)
        
        return Spell(name, school, level, cast, rnge, components, duration, desc, ritual)

def get_school_colour(school):
    return {
        'Abjuration': discord.Colour.blue,
        'Illusion': discord.Colour.purple,
        'Conjuration': discord.Colour.orange,
        'Enchantment': discord.Colour.gold,
        'Evocation': discord.Colour.red,
        'Divination': discord.Colour.lighter_grey,
        'Necromancy': discord.Colour.default,
        'Transmutation': discord.Colour.green
    }.get(school, discord.Colour.default)()

def get_level_prefix(level):
    if level == 0:
        return 'Cantrip'
    elif level == 1:
        return '1st Level'
    elif level == 2:
        return '2nd Level'
    elif level == 3:
        return '3rd Level'
    else:
        return f'{level}th Level'

def get_embed_description(spell):
    prefix = get_level_prefix(spell.level)
    if spell.level == 0:
        # Evocation Cantrip
        description = f'{spell.school} {prefix}'
    else:
        # 3rd Level Evocation
        description = f'{prefix} {spell.school}'
    
    if spell.ritual:
        description += ', Ritual'

    return description

def chunk_spell_desc(desc):
    if len(desc) < 1024:
        return [desc]
    desc = desc.split('\n\n')
    
    i = 0
    while i < len(desc):
        if len(desc[i]) > 1024:
            if '\n' in desc[i]:
                chunks = desc[i].split('\n')
                del desc[i]
                for c in reversed(chunks):
                    desc.insert(i, c)
        i += 1

    return desc