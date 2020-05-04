import requests
import difflib
import discord

# More or less copied over from https://github.com/OwenFeik/spells

class Spellbook():
    def __init__(self, spellbook_url):
        self.build_spellbook(spellbook_url)
            
    def build_spellbook(self, spellbook_url):
        try:
            self.spells = {spell['name']: Spell.from_json(spell) \
                for spell in requests.get(spellbook_url).json()}

            alt_names = {}
            for spell in self.spells.values():
                if spell.alt_names:
                    for name in spell.alt_names:
                        alt_names[name] = spell
            self.spells.update(alt_names)

            self.names = list(self.spells.keys())
            self._names = [name.lower() for name in self.names] # Used to match queries through difflib
        except:
            raise ValueError

    def get_spell(self,query):
        target = difflib.get_close_matches(query.lower(), self._names, 1)
        if target:
            return self.spells[self.names[self._names.index(target[0])]]
        else:
            return None

    def get_spells(self,queries):
        spells = []
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
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', 'N/A')
        self.school = kwargs.get('school', 'N/A')
        self.level = kwargs.get('level', -1)
        self.cast = kwargs.get('cast', 'N/A')
        self.rnge = kwargs.get('range', 'N/A')
        self.components = kwargs.get('components', 'N/A')
        self.duration = kwargs.get('duration', 'N/A')
        self.desc = kwargs.get('description', 'N/A')
        self.ritual = kwargs.get('ritual', False)
        self.classes = kwargs.get('classes', [])
        self.subclasses = kwargs.get('subclasses', [])
        self.alt_names = kwargs.get('alt_names', [])

    def __str__(self):
        return f'\n{self.name} | {self.school}\
            \n{self.cast} | {self.rnge}{" | Ritual" if self.ritual else ""}\n\
            {self.components} | {self.duration}\n\n{self.desc}\n'

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
        e.add_field(name = 'Classes', value = ', '.join(self.classes), inline = False)

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
            'ritual': self.ritual,
            'classes': self.classes,
            'subclasses': self.subclasses,
            'alt_names': self.alt_names
        }

    @staticmethod
    def from_json(data):
        return Spell(**data)

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
