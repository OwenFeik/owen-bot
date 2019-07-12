import time # Send log messages with the current time
import json # Load preferences

def log_message(msg): # Send a log message that looks like: LOG 00:00> msg
    print('LOG '+time.strftime('%H:%M',time.localtime(time.time()))+'> '+msg)
    
def load_config(): # Load the config file
    try:
        with open('resources/config.json','r') as f:
            return json.load(f) # And return a dictionary with the relevant points
    except FileNotFoundError:
        print('No config file found.')
        exit()

def extend_string(string, target_length):
    while len(string) < target_length:
        string += ' '
    return string
