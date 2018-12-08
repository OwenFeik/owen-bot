import time # Send log messages with the current time

def log_message(msg):
    print('LOG '+time.strftime('%H:%M',time.localtime(time.time()))+'> '+msg)
    