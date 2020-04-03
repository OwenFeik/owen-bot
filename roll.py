import re
import random
import operator

def handle_command(string, mention):
    arguments = string.strip().split()
    rolls = []
    roll = None
    op = '+'

    operators = ['+', '-', '/', '*']

    try:
        for arg in arguments:
            die = re.search(r'[0-9]*d[0-9]+[ADad]*', arg)
            if die:
                die = die.group(0)
                if die == arg:
                    roll = Roll(arg)
                    rolls.append(roll)
                    roll.set_operator(op)
                else:
                    arg.replace(die, '')
                    if arg[0] in operators:
                        op = arg[0]
                        arg = arg[1:]
                    roll = Roll(die)
                    rolls.append(roll)
                    roll.set_operator(op)

                    mods = re.findall('[+-/*][0-9]+', arg)
                    for mod in mods:
                        roll.add_modifier(Modifier.from_string(mod))
                    keep = re.search('k[0-9]+', arg)
                    if keep:
                        roll.keep = int(keep.group(0)[1:])
                
                op = '+'                
            elif arg in operators:
                op = arg
            elif arg.isnumeric():
                roll.add_modifier(Modifier(int(arg), op))
                op = '+'
            elif re.match(r'^k[0-9]+$', arg):
                roll.keep = int(arg[1:])
            elif re.match(r'^[+-/*][0-9]+$', arg):
                roll.add_modifier(Modifier(int(arg[1:]), arg[0]))
            elif arg.strip() == '':
                pass
            else:
                raise ValueError
    except Exception as e:
        return 'Invalid format.'

    if len(rolls) == 1:
        message = f'{mention} rolled {str(rolls[0])}'
    else:
        total = 0
        message = f'{mention} rolled `{string.strip()}`:\n'
        for r in rolls:
            message += f'{str(r)}\n'
            total = r.apply(total)
        message += f'Grand Total: {int_if_whole(total)}'

    return message

class Roll():
    def __init__(self, string):
        self.string = string
        self.adv = self.disadv = False

        advscore = 0
        while string[-1].upper() in ['A', 'D']:
            if string[-1].upper() == 'A':
                advscore += 1
            else:
                advscore -= 1
            string = string[:-1]

        self.adv = advscore > 0
        self.disadv = advscore < 0

        qty, die = string.split('d')
        self.qty = int(qty) if len(qty) > 0 else 1
        self.die = int(die)

        self.keep = -1 # How many values to keep from the roll: -1 -> all
        self.modifiers = []

        self.operation = operator.add
        self.resolved = False
        
        self._rolls = []
        self._total = 0

    def __str__(self):
        string = f'`{self.string}'
        for mod in self.modifiers:
            string += f' {str(mod)}'
        if self.keep >= 0:
            string += f' keep {self.keep}'
        string += f"`\t Roll{'s' if len(self.rolls) > 1 else ''}: {str(self.rolls)[1:-1]} \tTotal: {int_if_whole(self.total)}"

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
        if (self.adv or self.disadv) and self.qty == 1:
            self.qty = 2

        rolls = []
        for _ in range(0, self.qty):
            result = random.randint(1, self.die)
            rolls.append(result)

        if self.keep >= 0 and self.keep < self.qty:
            kept_rolls = rolls[:]
            for _ in range(0, self.qty - self.keep):
                kept_rolls.pop(kept_rolls.index(min(kept_rolls)))
        else:
            kept_rolls = rolls

        if (self.adv or self.disadv):
            total = max(kept_rolls) if self.adv else min(kept_rolls)
        else:
            total = sum(kept_rolls)

        for mod in self.modifiers:
            total = mod.apply(total)
        
        self._rolls = rolls
        self._total = total
        self.resolved = True

        return rolls, total

    def apply(self, val):
        return self.operation(val, self.total)

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

def int_if_whole(num):
    if num // 1 == num:
        return int(num)
    return num
