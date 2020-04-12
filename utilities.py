import time # Send log messages with the current time
import json # Load preferences

def log_message(msg): 
    timestring = time.strftime('%d/%m %T')
    print(f'<{timestring}> {msg}')
    
def load_config(): # Load the config file
    try:
        with open('resources/config.json','r') as f:
            return json.load(f) # And return a dictionary with the relevant points
    except FileNotFoundError:
        log_message('No config file found.')
        exit()

def load_help():
    try:
        with open('resources/help.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log_message('No help file found.')
        return {}
