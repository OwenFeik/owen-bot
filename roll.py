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

    if is_legal_roll(string):
        rolls = [Roll(string)]        
    else:
        try:
            tokens = parse_roll(string)
            rolls = process_tokens(tokens)
            assert len(rolls) > 0
        except Exception as e:
            # False, failed to parse roll, returning error message
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
    def __init__(self, string):
        self.string = string

        self.adv = self.disadv = False
        adv_str = re.search(r'[ad]+$', string)
        if adv_str:
            adv_str = adv_str.group(0)
            advscore = adv_str.count('a') - adv_str.count('d')

            self.adv = advscore > 0
            self.disadv = advscore < 0

            string = re.sub(r'[ad]+$', '', string)

        self.keep = -1 # How many values to keep from the roll: -1 -> all
        keep_str = re.search(r'k\d+$', string)
        if keep_str:
            keep_str = keep_str.group(0)
            self.keep = int(keep_str[1:])

            string = re.sub(r'k\d+$', '', string)

        qty, die = string.split('d')
        self.qty = int(qty) if len(qty) > 0 else 1
        self.die = int(die)

        if (self.adv or self.disadv) and self.qty == 1:
            self.qty = 2

        if self.qty > 1000:
            raise ValueError('Maximum quantity exceeded.')

        self.modifiers = []

        self.operation = operator.add
        self.resolved = False
        
        self._rolls = []
        self._total = 0

    def __str__(self):
        return self.desc_str() + self.roll_str()

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
            string += f"\t Rolls: {str(self.rolls)[1:-1]}"
            string += f" \tTotal: {clean_number(self.total)}"
        else:
            string += f"\t Roll: {self.rolls[0]}"
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

def is_legal_roll(string):
    return bool(re.match(r'^\d*d\d+(k\d+|[ad]+)?$', string))

def parse_roll(string):
    terms = []
    term = ''

    is_operator = lambda s: s in ['+', '-', '*', '/']
    is_int = lambda s: s.isnumeric()
    is_simple_roll = lambda s: bool(re.match(r'^\d*d\d+$', s))
    prev_is_int = lambda: terms and is_int(terms[-1])
    prev_is_simple_roll = lambda: terms and is_simple_roll(terms[-1]) 
    prev_is_legal_roll = lambda: terms and is_legal_roll(terms[-1])

    for c in string.strip().lower().replace('keep', 'k'):
        isnumber = term.isnumeric()
        isroll = bool(re.match(r'^\d*d\d*$', term))
        issimpleroll = is_simple_roll(term)
        isadvroll = bool(re.match(r'^\d*d\d+[ad]+$', term))
        iskeeproll = bool(re.match(r'^\d*d\d+k\d*$', term))
        islegalroll = is_legal_roll(term)
        isanyroll = isroll or issimpleroll or isadvroll or iskeeproll or islegalroll 
        isempty = term == ''

        if c.isnumeric():
            if isnumber or isroll or iskeeproll or isempty:
                term += c
            else:
                print(term)
                raise ValueError(f'Anomalous digit: {c}.')
        elif is_operator(c):
            if isanyroll or isnumber:
                terms.append(term)
                terms.append(c)
                term = ''
            elif (prev_is_int() or prev_is_legal_roll()) and isempty:
                terms.append(c)
            else:
                raise ValueError(f'Anomalous operator: {c}.')
        elif c == 'd':
            if isnumber or issimpleroll or isadvroll or isempty:
                term += c
            else:
                raise ValueError(f'Anomalous d.')
        elif c in ['a', 'k']:
            if prev_is_simple_roll() and isempty:
                term = terms[-1]
                term += c
                del terms[-1]
            elif c == 'a' and (issimpleroll or isadvroll):
                term += c
            elif c == 'k' and issimpleroll:
                term += c
            else:
                raise ValueError(f'Anomalous character: {c}.')
        elif c == ' ':
            if islegalroll or isnumber:
                terms.append(term)
                term = ''
        else:
            raise ValueError(f'Illegal character: {c}.')
    if term:
        terms.append(term)

    return terms

def process_tokens(tokens):
    rolls = []
    roll = None
    op = None
    const = None
    modqueue = []

    operators = ['+', '-', '/', '*']

    for arg in tokens:
        if is_legal_roll(arg):
            if op:
                o = op
                n = 1
                op = None
            elif const:
                o = '+'
                n = const
                const = None
            else:
                o = '+'
                n = 1
            
            for _ in range(n):
                roll = Roll(arg)
                rolls.append(roll)
                roll.set_operator(o)
                for m in modqueue:
                    roll.add_modifier(m)
            modqueue = []
        elif arg in operators:
            if const:
                modqueue.append(Modifier(const, arg))
                const = None
            else:
                op = arg
        elif arg.isnumeric():
            if roll and op:
                roll.add_modifier(Modifier(int(arg), op))
                op = None
            else:
                const = int(arg)
        else:
            raise ValueError
    
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
        avg = round(sum(rolls) / len(rolls), 1) if rolls else 0

        embed.add_field(
            name = f'd{die} ({len(rolls)} rolled)',
            value = f'```{avg} ({avg - ((die + 1) / 2)})```',
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
