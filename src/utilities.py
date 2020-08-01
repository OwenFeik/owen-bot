import json
import re
import time

def log_message(msg): 
    timestring = time.strftime('%d/%m %T')
    print(f'<{timestring}> {msg}')
    
def load_config(): # Load the config file
    try:
        with open('resources/config.json','r') as f:
            return json.load(f) # And return a dictionary with the relevant points
    except FileNotFoundError:
        log_message('No config file found. Exiting.')
        exit()

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
        text = text.replace(f'<@{uid}>', '')
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

def parse_time(string):
    string = string.strip().lower()

    if re.match(r'^\d{1,2}:\d{1,2}(:\d{1,2})?$', string):
        hours, minutes, *_ = string.split(':')
        return int(hours) * 3600 + int(minutes) * 60
    elif string.isnumeric() and (0 < int(string) < 24):
        return int(string) * 3600
    elif re.match(r'^\d{1,2}:\d{1,2}(:\d{1,2})? ?(pm|am)$', string):
        string, period = string[:-2], string[-2:]
        hours, minutes, *_ = string.split(':')
        return int(hours) * 3600 + int(minutes) * 60 + \
            (0 if period == 'am' else 3600 * 12)
    elif re.match(r'^\d{1,2} ?(pm|am)$', string):
        string, period = string[:-2], string[-2:]
        hours = int(string.strip())
        return hours * 3600 + (0 if period == 'am' else 3600 * 12)
    else:
        raise ValueError('Not a valid time format.')
