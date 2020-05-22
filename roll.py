import re
import random
import operator
import heapq
import discord
import database

def handle_command(string, **kwargs):
    failstr = kwargs.get('failstr', 'Invalid format')
    
    # One of these two must be supplied
    user = kwargs.get('user')
    mention = kwargs.get('mention', user.display_name)

    server = kwargs.get('server')
    db = kwargs.get('database')

    string = string.strip()
    if string == 'stats':
        if type(db) == str:
            db = database.Roll_Database(db)
        
        return True, stats_embed(db.get_rolls(user, server), mention)
    
    try:
        rolls = get_rolls(string)
        assert len(rolls) > 0
    except Exception as e:
        return False, f'{failstr}: {e}'

    if server and user:
        if type(db) == str:
            db = database.Roll_Database(db)
        
        for roll in rolls:
            db.insert_roll(roll, user, server)

    # True; succeeded, supplying an embed
    return True, build_embed(rolls, mention, string)

def build_embed(rolls, mention, string):
    if len(rolls) == 1:
        title = f'{mention} rolled '
        title += 'a die:' if len(rolls[0].rolls) == 1 else 'some dice:'
        message = str(rolls[0])
    else:
        total = 0
        title = f'{mention} rolled `{string.strip()}`'
        message = ''

        pad_desc = max([len(r.desc_str()) for r in rolls])

        for r in rolls:
            message += f'{r.full_str(pad_desc)}\n'
            total = r.apply(total)
        message += f'Grand Total: {clean_number(total)}'

    message = f'```{message}```'

    embed = discord.Embed(
        description = message,
        title = title
    )

    return embed

class Roll():
    def __init__(self, qty, die, adv, disadv, keep, modifiers, operation):
        self.qty = qty
        self.die = die
        self.adv = adv
        self.disadv = disadv
        self.keep = keep
        self.modifiers = modifiers
        self.operation = operation

        if self.qty > 1000:
            raise ValueError('Maximum quantity exceeded.')

        self.resolved = False
        self._rolls = []
        self._total = 0

    def __str__(self):
        return self.desc_str() + self.roll_str()

    def __repr__(self):
        return str(self)

    def full_str(self, pad_desc = 0, pad_roll = 0):
        return self.desc_str(pad_desc) + self.roll_str(pad_roll)

    def desc_str(self, pad_to = 0):
        if (self.adv or self.disadv) and (self.qty == 2):
            string = f"d{self.die}"
        else:
            string = f"{self.qty if self.qty > 1 else ''}d{self.die}"
        string += f"{'a' if self.adv else ''}{'d' if self.disadv else ''}"
        if self.keep >= 0:
            string += f' keep {self.keep}'
        for mod in self.modifiers:
            string += f' {str(mod)}'
        
        while len(string) < pad_to:
            string += ' '

        return string

    def dice_str(self):
        # Used for saving results in database
        return f"{self.qty}d{self.die}"

    def roll_str(self, pad_to = 0):
        string = ''
        if len(self.rolls) > 1:
            string += f"\tRolls: {str(self.rolls)[1:-1]}"
            string += f" \tTotal: {clean_number(self.total)}"
        else:
            string += f"\tRoll: {self.rolls[0]}"
            if self.modifiers:
                string += f" \tTotal: {clean_number(self.total)}"

        while len(string) < pad_to:
            string += ' '

        return string

    @property
    def total(self):
        if not self.resolved:
            self.resolve()
        return self._total

    @property
    def rolls(self):
        if not self.resolved:
            self.resolve()
        return self._rolls

    def resolve(self):
        rolls = [random.randint(1, self.die) for _ in range(self.qty)]

        if self.adv:
            total = max(rolls)
        elif self.disadv:
            total = min(rolls)
        elif self.keep >= 0:
            total = sum(heapq.nlargest(self.keep, rolls))
        else:
            total = sum(rolls)

        total = self.apply_mods(total)

        self._rolls = rolls
        self._total = total
        self.resolved = True

        return rolls, total

    def apply(self, val):
        return self.operation(val, self.total)

    def apply_mods(self, val):
        for mod in self.modifiers:
            val = mod.apply(val)
        return val

    def set_operator(self, opstr):
        self.operation = get_operator(opstr)

    def add_modifier(self, modifier):
        self.modifiers.append(modifier)

class Modifier():
    def __init__(self, val, opstr):
        self.val = val
        self.opstr = opstr
        self.operation = get_operator(opstr)

    def __str__(self):
        return f'{self.opstr} {self.val}'

    def apply(self, val):
        return self.operation(val, self.val)

    @staticmethod
    def from_string(string):
        return Modifier(int(string[1:]), string[0])

def get_operator(opstr):
    return {
        '+': operator.add, 
        '-': operator.sub, 
        '*': operator.mul, 
        '/': operator.truediv
    }[opstr]

def clean_number(num):
    if num // 1 == num:
        return int(num)
    return round(num, 2)

def get_rolls(string):
    rolls = []
    regex = r'(?P<op>[+-/*]?)? *(?P<n>\d+(?= +\d))? *(?P<qty>\d*)d' + \
        r'(?P<die>\d+) *(?P<advstr>[ad]*)' + \
        r'(?P<mods>( *(k *\d+|[+-/*] *\d+(?!d)))*)'
    
    for roll in re.finditer(regex, string):
        n = roll.group('n')
        if n in [None, '']:
            n = 1
        else:
            n = int(n)

        qty = roll.group('qty')
        if qty in [None, '']:
            qty = 1
        else:
            qty = int(qty)

        die = int(roll.group('die'))

        advstr = roll.group('advstr')
        advscore = advstr.count('a') - advstr.count('d')
        adv = advscore > 0
        disadv = advscore < 0
        if adv and qty == 1:
            qty = 2

        modstr = roll.group('mods')
        mods = []
        keep = -1
        if not modstr in [None, '']:
            modstr = modstr.replace(' ', '') + 'k'
            # Add k to ensure last term is added
            # won't cause an error in a properly formatted string

            q = ''
            o = ''
            for c in modstr:
                if c in ['k', '+', '-', '*', '/']:
                    if o == 'k' and q:
                        if keep > 0:
                            raise ValueError('Multiple keep values provided.')
                        keep = int(q)
                    elif o:
                        mods.append(Modifier(int(q), o))
                    o = c
                    q = ''
                else:
                    q += c

        op = roll.group('op')
        if op in [None, ''] or n > 1:
            op = get_operator('+')
        else:
            op = get_operator(op)

        for _ in range(n):
            rolls.append(Roll(qty, die, adv, disadv, keep, mods, op))

    return rolls

def stats_embed(data, mention):
    results = {}
    for string, result in data:
        qty, die = string.split('d')
        die = int(die)
        rolls = [int(r) for r in result.split(',')]
        if die in results:
            results[die].extend(rolls)
        else:
            results[die] = rolls

    embed = discord.Embed(
        description = f'Roll stats for {mention}'
    )
    for die in [4, 6, 8, 10, 12, 20]:
        rolls = results.get(die, [])
        die_avg = (die + 1) / 2
        avg = round(sum(rolls) / len(rolls), 1) if rolls else 0
        delta = round(avg - die_avg, 1) if rolls else 0
        delta_string = f'+{delta}' if delta > 0 else \
            str(delta) if delta < 0 else 'avg'

        embed.add_field(
            name = f'd{die} ({len(rolls)} rolled)',
            value = f'```{avg} ({delta_string})```',
            inline = True
        )

        try:
            del results[die]
        except KeyError:
            pass

    other = 0
    for r in results:
        other += len(results[r])
    embed.set_footer(text = f'{other} other die rolled.')

    return embed
