import re
import time
from database import Database
import datetime

def handle_message(message):
    msg=clean_msg(message.content)
    if msg=='':
        return 'Usage: --remindme in 1 day to do a thing or --remindme on DD/MM/YY to do a different thing.'
    elif msg[0:2]=='in':
        msg=msg[3:] # Remove 'in '
        try:
            multiplier=float(re.search('[0-9.]+',msg).group(0))
        except (AttributeError,ValueError):
            return 'Usage: --remindme in {x} {minutes/hours/days/weeks/months} {to do a thing}'
        period=re.search('[a-zA-Z] ',msg).group(0)
        if period in ['min','mins','mns','minutes']:
            tme=60*multiplier
        elif period in ['hrs','hr','hours','hour']:
            tme=3600*multiplier
        elif period in ['day','days']:
            tme=86400*multiplier
        elif period in ['week','weeks','wk','wks']:
            tme=604800*multiplier
        elif period in ['month','months','mnth','mnths']:
            tme=18144000*multiplier
        else:
            return 'Usage: --remindme in {x} {minutes/hours/days/weeks/months} {to do a thing}'
        msg=msg[len(re.search('[0-9.]+ ?[a-zA-Z] ',msg).group(0)):] # Remove the '1 day' part
        tme+=time.time()

        db=Database('bot.db')
        db.insert_reminder(tme,message.channel.id,message.author.mention,msg)
        
        dtm=datetime.datetime.fromtimestamp(tme)
        return f"I will remind you on {dtm.strftime('%b %d %Y')} at {dtm.strftime('%H:%M')} to {msg}"
    elif msg[0:2]=='on':
        msg=msg[3:]
        try:
            date_string=re.search('[0-9/]+',msg).group(0)
            date=datetime.datetime.strptime(date_string,'%-d/%-m/%y')
        except ValueError:
            return 'Usage: --remindme on DD/MM/YY to do something.'
        

        


def clean_msg(string): # Remove '--remindme', spaces from start
    if string=='':
        return string
    if string[0:10]=='--remindme':
        string=string[10:] # Cut off '--remindme'
    while string!='' and string[0]==' ':
        string=string[1:]
    return string