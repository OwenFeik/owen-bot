import datetime
import enum
import os
import random

import aiosqlite

import utilities


class TransTypes(enum.Enum):
    GETALL = enum.auto()
    GETONE = enum.auto()
    COMMIT = enum.auto()


class Database:
    VERSION = 1

    def __init__(self):
        self.file = None
        self.startup_commands = [f"PRAGMA user_version = {Database.VERSION};"]
        self.connection = None

    # Must be called after all desired interfaces are instantiated
    # or startup commands will not be executed.
    async def make_connection(self, file):
        self.file = file
        run_migration = os.path.isfile(file)
        self.connection = await aiosqlite.connect(self.file)
        if run_migration:
            await self.migrate()
        for command in self.startup_commands:
            await self.execute(command, trans_type=TransTypes.COMMIT)
        utilities.log_message("Established connection and set up database.")

    async def save(self):
        try:
            await self.connection.commit()
        except Exception as e:
            utilities.log_message(f"Database error: {e}")

    async def close(self):
        await self.connection.close()

    async def execute(self, command, args=None, trans_type=TransTypes.GETALL):
        try:
            if args is not None:
                cursor = await self.connection.execute(command, args)
            else:
                cursor = await self.connection.execute(command)

            if trans_type == TransTypes.GETALL:
                return await cursor.fetchall()
            elif trans_type == TransTypes.GETONE:
                return await cursor.fetchone()
            elif trans_type == TransTypes.COMMIT:
                await self.save()
        except Exception as e:
            utilities.log_message(f"Database error: {e}")
            utilities.log_message(f"Ocurred on command: {command}")

    async def migrate(self):
        (from_version,) = await self.execute(
            "PRAGMA user_version;", trans_type=TransTypes.GETONE
        )

        if from_version == Database.VERSION:
            utilities.log_message("Database schema up to date!")
        elif from_version == 0:
            utilities.log_message(
                f"Database at version 0: updating to {Database.VERSION}"
            )
            await self.execute("PRAGMA foreign_keys = OFF;")
            await self.execute(
                "CREATE TABLE _new_campaigns("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "name TEXT COLLATE NOCASE, server INTEGER, "
                "dm INTEGER, players TEXT, nicks TEXT, active INTEGER, "
                "day INTEGER, time INTEGER, notify INTEGER, channel INTEGER, "
                "FOREIGN KEY(dm) REFERENCES users(id), "
                "FOREIGN KEY(server) REFERENCES servers(id), "
                "UNIQUE(name, server));"
            )
            await self.execute(
                "INSERT INTO _new_campaigns("
                "name, server, dm, players, nicks, "
                "active, day, time, notify, channel"
                ") SELECT * FROM campaigns;"
            )
            await self.execute("DROP TABLE campaigns;")
            await self.execute(
                "ALTER TABLE _new_campaigns RENAME TO campaigns;"
            )
            await self.execute("PRAGMA foreign_keys = ON;")
            await self.execute(
                "ALTER TABLE rolls ADD COLUMN campaign INTEGER REFERENCES "
                "campaigns(id) ON DELETE SET NULL;"
            )
            await self.save()
            utilities.log_message("Database migration successful!")
        else:
            utilities.log_message(
                "Don't know how to update database from version "
                f"{from_version} to version {Database.VERSION}. Exiting."
            )
            exit(1)


database = Database()
init_db = database.make_connection


class Interface:
    def __init__(self):
        pass


class Discord_Database(Interface):
    def __init__(self):
        super().__init__()
        for table in ["users", "servers"]:
            database.startup_commands.append(
                f"CREATE TABLE IF NOT EXISTS {table}("
                "id INTEGER PRIMARY KEY, name TEXT);",
            )

    async def insert_user(self, user):
        command = "REPLACE INTO users VALUES(?, ?);"
        user_tuple = (user.id, user.name)
        await database.execute(command, user_tuple, TransTypes.COMMIT)

    async def insert_server(self, server):
        command = "REPLACE INTO servers VALUES(?, ?);"
        server_tuple = (server.id, server.name)
        await database.execute(command, server_tuple, TransTypes.COMMIT)


class Roll_Database(Interface):
    def __init__(self):
        super().__init__()
        database.startup_commands.append(
            "CREATE TABLE IF NOT EXISTS rolls("
            "string TEXT, result TEXT, "
            "user INTEGER, server INTEGER, campaign INTEGER, "
            "FOREIGN KEY(user) REFERENCES users(id), "
            "FOREIGN KEY(server) REFERENCES servers(id), "
            "FOREIGN KEY(campaign) REFERENCES campaigns(id) ON DELETE SET NULL"
            ");"
        )

    async def get_active_campaign(self, user, server):
        campaign = await database.execute(
            "SELECT id, name FROM campaigns WHERE "
            "server = ? AND active = 1 AND players LIKE ?;",
            (server, f"%{user.id}%"),
            TransTypes.GETONE,
        )

        try:
            campaign_id, campaign_name = campaign
        except TypeError:
            raise ValueError("User is not in a campaign on server.")

        return campaign_id, campaign_name

    async def insert_roll(self, roll, user, server):
        try:
            campaign_id, _ = await self.get_active_campaign(user, server.id)
        except ValueError:
            campaign_id = None

        rolls_str = ",".join([str(r) for r in roll.rolls])
        dice_str = roll.dice_str()
        data = (dice_str, rolls_str, user.id, server.id, campaign_id)
        await database.execute(
            "INSERT INTO rolls VALUES(?, ?, ?, ?, ?);", data, TransTypes.COMMIT
        )

    async def get_rolls(self, user, server):
        id_tuple = (user.id, server.id)
        return await database.execute(
            "SELECT string, result FROM rolls WHERE user = ? AND server = ?;",
            id_tuple,
            TransTypes.GETALL,
        )

    async def get_campaign_rolls(self, user, server):
        campaign_id, campaign_name = await self.get_active_campaign(
            user, server.id
        )

        return (
            await database.execute(
                "SELECT string, result FROM rolls "
                "WHERE user = ? AND server = ? AND campaign = ?;",
                (user.id, server.id, campaign_id),
                TransTypes.GETALL,
            ),
            campaign_name,
        )

    async def reset_rolls(self, user, server=None):
        if server is not None:
            sql = "DELETE FROM rolls WHERE user = ? AND server = ?;"
            tup = (user.id, server.id)
        else:
            sql = "DELETE FROM rolls WHERE user = ?;"
            tup = (user.id,)

        await database.execute(sql, tup, TransTypes.COMMIT)


class Campaign_Database(Interface):
    def __init__(self):
        super().__init__()
        database.startup_commands.append(
            "CREATE TABLE IF NOT EXISTS campaigns("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT COLLATE NOCASE, server INTEGER, "
            "dm INTEGER, players TEXT, nicks TEXT, active INTEGER, "
            "day INTEGER, time INTEGER, notify INTEGER, channel INTEGER, "
            "FOREIGN KEY(dm) REFERENCES users(id), "
            "FOREIGN KEY(server) REFERENCES servers(id), "
            "UNIQUE(name, server));"
        )

    async def set_active(self, campaign):
        await database.execute(
            "UPDATE campaigns SET active = CASE\n"
            "    WHEN name = ? AND server = ? THEN 1\n"
            "    WHEN name != ? AND server = ? THEN 0\n"
            "    WHEN server != ? THEN active\n"
            "END;",
            (
                campaign.name,
                campaign.server,
                campaign.name,
                campaign.server,
                campaign.server,
            ),
            TransTypes.COMMIT,
        )

    async def add_campaign(self, campaign, active=True):
        await database.execute(
            "REPLACE INTO campaigns("
            "name, server, dm, players, nicks, active, "
            "day, time, notify, channel"
            ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (
                campaign.name,
                campaign.server,
                campaign.dm,
                ",".join(str(p) for p in campaign.players),
                ",".join(f'"{n}"' for n in campaign.nicks),
                int(active),
                campaign.day,
                campaign.time,
                1 if campaign.notify else 0,
                campaign.channel,
            ),
            TransTypes.COMMIT,
        )

    async def delete_campaign(self, campaign):
        await database.execute(
            "DELETE FROM campaigns WHERE name = ? AND server = ?;",
            (campaign.name, campaign.server),
            TransTypes.COMMIT,
        )

    async def get_campaign(self, name, server):
        return await database.execute(
            "SELECT name, dm, players, nicks, day, time, notify, channel "
            "FROM campaigns WHERE name = ? AND server = ?;",
            (name, server),
            TransTypes.GETONE,
        )

    async def suggest_campaign(self, name, server):
        return await database.execute(
            "SELECT name FROM campaigns WHERE name LIKE ? AND server = ?;",
            (name, server),
            TransTypes.GETONE,
        )

    async def get_active_campaign(self, server):
        return await database.execute(
            "SELECT name, dm, players, nicks, day, time, notify, channel "
            "FROM campaigns WHERE server = ? AND active = 1;",
            (server,),
            TransTypes.GETONE,
        )

    async def get_campaign_names(self, server):
        return await database.execute(
            "SELECT name FROM campaigns WHERE server = ?;",
            (server,),
            TransTypes.GETALL,
        )

    async def get_reminders(self, period, delta):
        now = datetime.datetime.now()
        notif_time = now.hour * 3600 + now.minute * 60 + now.second + delta
        return await database.execute(
            "SELECT name, channel, players FROM campaigns "
            "WHERE notify = 1 AND day = ? AND time - ? < ? AND time - ? > 0;",
            (now.weekday(), notif_time, period, notif_time),
            TransTypes.GETALL,
        )


class XKCD_Database(Interface):
    def __init__(self):
        super().__init__()
        database.startup_commands.append(
            "CREATE TABLE IF NOT EXISTS xkcds("
            "id INTEGER PRIMARY KEY, name TEXT, uri TEXT, alt TEXT);",
        )

    async def xkcd_count(self):
        data = await database.execute(
            "SELECT COUNT(*) FROM xkcds;", trans_type=TransTypes.GETONE
        )
        return data[0]

    async def insert_xkcd(self, xkcd):
        await database.execute(
            "INSERT INTO xkcds VALUES(?, ?, ?, ?);",
            (xkcd.idno, xkcd.name, xkcd.uri, xkcd.alt),
            TransTypes.COMMIT,
        )

    async def get_xkcd_list(self):
        data = await database.execute(
            "SELECT name FROM xkcds;", trans_type=TransTypes.GETALL
        )
        return [item[0] for item in data]

    async def get_xkcd(self, name):
        return self.interpret_xkcd(
            await database.execute(
                "SELECT id, name, uri, alt FROM xkcds WHERE name = ?;",
                (name,),
                TransTypes.GETONE,
            )
        )

    async def get_random_xkcd(self):
        newest = (
            await database.execute(
                "SELECT max(id) FROM xkcds;", trans_type=TransTypes.GETONE
            )
        )[0]
        comic = random.randint(newest - await self.xkcd_count(), newest)
        try:
            return self.interpret_xkcd(
                await database.execute(
                    "SELECT id, name, uri, alt FROM xkcds WHERE id = ?;",
                    (str(comic),),
                    TransTypes.GETONE,
                )
            )
        except TypeError:
            utilities.log_message(f"Missing xkcd #{comic}.")
            return await self.get_random_xkcd()

    async def get_newest_xkcd(self):
        return self.interpret_xkcd(
            await database.execute(
                "SELECT id, name, uri, alt, max(id) FROM xkcds;",
                trans_type=TransTypes.GETONE,
            )
        )

    async def get_id(self, idno):
        data = await database.execute(
            "SELECT id, name, uri, alt FROM xkcds WHERE id = ?;",
            (idno,),
            TransTypes.GETONE,
        )
        if data:
            return self.interpret_xkcd(data)
        else:
            return await self.get_xkcd("not available")

    def interpret_xkcd(self, data):
        repair_string = lambda s: s.replace("&#39;", "'").replace("&quot;", '"')

        name = f"{repair_string(data[1])} | {str(data[0])}"
        name = utilities.capitalise(name)
        uri = data[2]
        alt = repair_string(data[3])
        return name, uri, alt
