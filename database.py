import datetime
import random
import sqlite3

import utilities

class Database:
    def __init__(self, db_file):
        try:
            self.connection = sqlite3.connect(db_file)
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            utilities.log_message(f'Database error: {e}')
            self.connection = None
            self.cursor = None

    def save(self):
        try:
            self.connection.commit()
        except sqlite3.Error as e:
            utilities.log_message(f'Database error: {e}')

    def close(self):
        self.cursor.close()
        self.connection.close()

    def execute(self, command, args = None):
        try:
            if args is not None:
                self.cursor.execute(command, args)
            else:
                self.cursor.execute(command)
        except sqlite3.Error as e:
            utilities.log_message(f'Database error: {e}')
            utilities.log_message(f'Occurred on command: {command}')

class Discord_Database(Database):
    def __init__(self, db_file):
        super().__init__(db_file)
        for table in ['users', 'servers']:
            self.execute(
                f'CREATE TABLE IF NOT EXISTS {table}(\
                id INTEGER PRIMARY KEY, name TEXT);'
            )

    def execute(self, command, args = None, integrity = 'error'):
        try:
            if args is not None:
                self.cursor.execute(command, args)
            else:
                self.cursor.execute(command)
        except sqlite3.IntegrityError as e:
            if integrity.startswith('update'):
                data = (args[1], args[0])
                table = integrity[len('update-'):] + 's'
                command = f'UPDATE {table} SET name = ? WHERE id = ?;'
                self.execute(command, data)
            elif integrity != 'ignore':
                utilities.log_message(f'Integrity error {e} on {command}')
                utilities.log_message(f'Data: {args}')
        except sqlite3.Error as e:
            utilities.log_message(f'Database error: {e}')
            utilities.log_message(f'Occurred on command: {command}')

    def insert_user(self, user):
        command = 'INSERT INTO users VALUES(?, ?);'
        user_tuple = (user.id, user.name)
        self.execute(command, user_tuple, 'update-user')
        self.save()

    def insert_server(self, server):
        command = 'INSERT INTO servers VALUES(?, ?);'
        server_tuple = (server.id, server.name)
        self.execute(command, server_tuple, 'update-server')
        self.save()

class Roll_Database(Database):
    def __init__(self, db_file):
        super().__init__(db_file)
        self.execute(
            'CREATE TABLE IF NOT EXISTS rolls(\
            string TEXT, result TEXT, user INTEGER, server INTEGER, \
            FOREIGN KEY(user) REFERENCES users(id), \
            FOREIGN KEY(server) REFERENCES servers(id));'
        )

    def insert_roll(self, roll, user, server):
        rolls_str = ','.join([str(r) for r in roll.rolls])
        dice_str = roll.dice_str() 
        data = (dice_str, rolls_str, user.id, server.id)
        self.execute('INSERT INTO rolls VALUES(?, ?, ?, ?)', data)
        self.save()

    def get_rolls(self, user, server):
        id_tuple = (user.id, server.id)
        self.execute(
            'SELECT string, result FROM rolls WHERE user = ? AND server = ?;',
            id_tuple
        )
        return self.cursor.fetchall()

    def reset_rolls(self, user, server=None):
        if server is not None:
            sql = 'DELETE FROM rolls WHERE user = ? AND server = ?;'
            tup = (user.id, server.id)
        else:
            sql = 'DELETE FROM rolls WHERE user = ?;'
            tup = (user.id,)
        self.execute(sql, tup)
        self.save()

class Campaign_Database(Database):
    def __init__(self, db_file):
        super().__init__(db_file)
        self.execute(
            'CREATE TABLE IF NOT EXISTS campaigns(\
            name TEXT COLLATE NOCASE, server INTEGER, \
            dm INTEGER, players TEXT, nicks TEXT, active INTEGER, \
            day INTEGER, time INTEGER, notify INTEGER, channel INTEGER, \
            FOREIGN KEY(dm) REFERENCES users(id), \
            FOREIGN KEY(server) REFERENCES servers(id), \
            PRIMARY KEY(name, server));'
        )

    def set_active(self, campaign):
        self.execute(
            'UPDATE campaigns SET active = CASE \
                WHEN name = ? AND server = ? THEN 1 \
                WHEN name != ? AND server = ? THEN 0 \
                WHEN server != ? THEN active \
            END',
            (
                campaign.name,
                campaign.server,
                campaign.name,
                campaign.server,
                campaign.server
            )
        )
        self.save()

    def add_campaign(self, campaign, active=True):
        self.execute(
            'REPLACE INTO campaigns VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', 
            (
                campaign.name, 
                campaign.server, 
                campaign.dm,
                ','.join(str(p) for p in campaign.players),
                ','.join(f'"{n}"' for n in campaign.nicks),
                int(active),
                campaign.day,
                campaign.time,
                1 if campaign.notify else 0,
                campaign.channel
            )
        )
        self.save()

    def delete_campaign(self, campaign):
        self.execute(
            'DELETE FROM campaigns WHERE name = ? AND server = ?;',
            (campaign.name, campaign.server)
        )
        self.save()

    def get_campaign(self, name, server):
        self.execute(
            'SELECT name, dm, players, nicks, day, time, notify, channel \
            FROM campaigns WHERE name = ? AND server = ?;',
            (name, server)
        )
        return self.cursor.fetchone()

    def get_active_campaign(self, server):
        self.execute(
            'SELECT name, dm, players, nicks, day, time, notify, channel \
            FROM campaigns WHERE server = ? AND active = 1;',
            (server,)
        )
        return self.cursor.fetchone()

    def get_campaign_names(self, server):
        self.execute(
            'SELECT name FROM campaigns WHERE server = ?;',
            (server,)
        )
        return self.cursor.fetchall()

    def get_reminders(self, period, delta):
        now = datetime.datetime.now()
        notif_time = now.hour * 3600 + now.minute * 60 + now.second + delta 
        self.execute(
            'SELECT name, channel, players FROM campaigns \
            WHERE notify = 1 AND day = ? AND time - ? < ? AND time - ? > 0;',
            (
                now.weekday(),
                notif_time,
                period,
                notif_time
            )
        )
        return self.cursor.fetchall()

class XKCD_Database(Database):
    def __init__(self, db_file):
        super().__init__(db_file)
        
        command = 'CREATE TABLE IF NOT EXISTS xkcds(\
            id INTEGER PRIMARY KEY, name TEXT, uri TEXT, alt TEXT);'
        self.execute(command)

    def xkcd_count(self):
        self.cursor.execute(f'SELECT COUNT(*) FROM xkcds;') # Number of rows in xkcd table
        return self.cursor.fetchone()[0]

    def insert_xkcd(self,xkcd): # Add an xkcd object to the database
        self.cursor.execute(f"INSERT INTO xkcds VALUES({xkcd.idno},'{xkcd.name}','{xkcd.uri}','{xkcd.alt}');")
        self.save()
    
    def get_xkcd_list(self):
        self.cursor.execute(f'SELECT name FROM xkcds;')
        return [item[0] for item in self.cursor.fetchall()]

    def get_xkcd(self,name):
        self.cursor.execute(f"SELECT id,name,uri,alt FROM xkcds WHERE name='{name}';")
        return interpret_xkcd(self.cursor.fetchone())
        
    def get_random_xkcd(self): # Get a random xkcd
        self.cursor.execute('SELECT max(id) FROM xkcds;') # The db fills back from the newest
        newest=self.cursor.fetchone()[0] # So we'll have issues if we try to call from the full range
        comic=random.randint(newest-self.xkcd_count(),newest) # Pick a random number from count to the number of xkcds
        self.cursor.execute(f'SELECT id,name,uri,alt FROM xkcds WHERE id={str(comic)};') # Grab the xkcd with this id
        try:
            return interpret_xkcd(self.cursor.fetchone())
        except TypeError: # In the event we don't have this comic for whatever reason a TypeError is thrown due to a NoneType. We'll just re-roll
            utilities.log_message('Missing xkcd #'+str(comic))
            return self.get_random_xkcd()

    def get_newest_xkcd(self):
        self.cursor.execute('SELECT id,name,uri,alt,max(id) FROM xkcds;') # Grab the xkcd with the maximum id, as they are numbered sequentially
        return interpret_xkcd(self.cursor.fetchone())

    def get_id(self,idno): # Get an xkcd from id
        self.cursor.execute(f'SELECT id,name,uri,alt FROM xkcds WHERE id={idno};')
        data=self.cursor.fetchone()
        if data: # If we have the xkcd with this id
            return interpret_xkcd(data)
        else: # Otherwise, show 404 image
            return self.get_xkcd('not available')


def interpret_xkcd(data): # Clean up the data for sending in discord
    name=f'{repair_string(data[1])} | {str(data[0])}' # Title + id line
    name=capitalise_name(name)
    uri=data[2]
    alt=repair_string(data[3])
    return name,uri,alt

def repair_string(string): # Replace the ' and " placeholders in alt text with appropriate characters
    return string.replace('&#39;',"'").replace('&quot;','"') 

def capitalise_name(name): # Capitalise a comic name
    cap_name=''
    for i in range(0,len(name)):
        if i==0 or name[i-1]==' ':
            cap_name+=name[i].upper()
        else:
            cap_name+=name[i]
    return cap_name
