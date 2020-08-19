import json
import re
import time

class Logger():
    def __init__(self):
        self.log_to_file = True
        self.path = 'resources/.log'

    def log(self, msg):
        if not self.log_to_file:
            print(msg)
            return

        with open(self.path, 'a') as f:
            timestring = time.strftime('%d/%m %T')
            f.write(f'<{timestring}> {msg}\n')

    def set_path(self, path):
        self.path = path

logger = Logger()
log_message = logger.log
set_log_file = logger.set_path

def load_config(): # Load the config file
    try:
        with open('resources/config.json', 'r') as f:
            return json.load(f) # And return a dictionary with the relevant points
    except FileNotFoundError:
        log_message('No config file found. Exiting.')
        raise SystemExit

def load_help():
    try:
        with open('resources/help.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log_message('No help file found.')
        return {}

def scrub_message_of_mentions(message):
    text = message.content
    for uid in message.raw_mentions:
        text = text.replace(f'<@{uid}>', '').replace(f'<@!{uid}>', '')
    return text
    
def parse_weekday(string):
    try:
        return {
            'monday': 0,
            'mon': 0,
            '0': 0,
            'tuesday': 1,
            'tue': 1,
            '1': 1,
            'wednesday': 2,
            'wed': 2,
            '2': 2,
            'thursday': 3,
            'thur': 3,
            '3': 3,
            'friday': 4,
            'fri': 4,
            '4': 4,
            'saturday': 5,
            'sat': 5,
            '5': 5,
            'sunday': 6,
            'sun': 6,
            '6': 6
        }[string.strip().lower()]
    except KeyError:
        raise ValueError('Not a valid day of the week.')

def time_range_check(h = 0, m = 0, s = 0):
    message = 'Hours value must be in the range [0, 24].'
    try:
        assert 0 <= h <= 24
        message = 'Minutes value must be in the range [0, 60].'
        assert 0 <= m <= 60
        message = 'Seconds value must be in the range [0, 60].'
        assert 0 <= s <= 60
    except AssertionError:
        raise ValueError(message)

def parse_time(string):
    string = string.strip().lower()

    if re.match(r'^\d{1,2}:\d{1,2}(:\d{1,2})?$', string):
        hours, minutes, *seconds = string.split(':')
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds[0]) if seconds else 0
        time_range_check(hours, minutes, seconds)
        return hours * 3600 + minutes * 60 + seconds
    elif string.isnumeric():
        hours = int(string)
        time_range_check(hours)
        return hours * 3600
    elif re.match(r'^\d{1,2}:\d{1,2}(:\d{1,2})? ?(pm|am)$', string):
        string, period = string[:-2], string[-2:]
        hours, minutes, *seconds = string.split(':')
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds[0]) if seconds else 0
        time_range_check(hours, minutes, seconds)
        return hours * 3600 + minutes * 60 + \
            (0 if period == 'am' else 3600 * 12)
    elif re.match(r'^\d{1,2} ?(pm|am)$', string):
        string, period = string[:-2], string[-2:]
        hours = int(string.strip())
        time_range_check(hours)
        return hours * 3600 + (0 if period == 'am' else 3600 * 12)
    else:
        raise ValueError('Not a valid time format.')

def capitalise(name):
    name = name.strip().lower()
    name = name.replace(name[0], name[0].upper(), 1)
    skip = [
        'a',
        'an',
        'at',
        'and',
        'are',
        'but',
        'by',
        'for',
        'from',
        'not',
        'nor',
        'of',
        'or',
        'so',
        'the',
        'with',
        'yet'
    ]

    words = name.split(' ')
    for i in range(1, len(words)):
        c = words[i][0]
        if c.isalpha() and not words[i] in skip or i == len(words) - 1:
            words[i] = words[i].replace(c, c.upper(), 1)
    
    return ' '.join(words)
