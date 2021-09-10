import asyncio  # More efficiently collect xkcds
import concurrent.futures
import difflib  # Get similarly named comics
import re  # Parse xkcd html for relevant data
import sys
import threading
import time

import discord
import requests  # Pull raw data from xkcd website

import database
import utilities  # Send messages in the log


class xkcd:
    def __init__(self, idno=0, name="", uri="", alt=""):
        self.idno = idno
        self.name = name
        self.uri = uri
        self.alt = alt

    @staticmethod
    def from_raw_name(name):
        temp = ""
        strip = xkcd()
        for c in name:
            # / means the comic number has ended. Some titles also have a /, so
            # ignore / after the first
            if c == "/" and not strip.idno:
                strip.idno = temp
                temp = ""
            elif c == ">":  # > is the beginning of the name
                temp = ""
            elif c == "<":  # < is the end of the name
                strip.name = temp.lower().replace(
                    "'", "&#39;"
                )  # &#39; is a placeholder for ' for it to work in the database
            else:
                temp += c
        return strip

    def get_uri_alt(self):
        r = requests.get(
            f"http://xkcd.com/{self.idno}"
        )  # Grab source of comic's page
        src = r.content.decode()  # Decode from raw binary

        uri = re.search(
            r"https://imgs\.xkcd\.com/comics/[\w.()-]+", src
        )  # Pull the permalink
        if uri:
            uri = uri.group(0)
            self.uri = uri

        alt = re.search(
            r"<img src=\"[^\"]+\" title=\"[^\"]+\"", src
        )  # Pull the alt text
        if alt:
            alt = re.search('title="[^"]+"', alt.group(0)).group(
                0
            )  # Grab the title section of the line
            alt = alt[7 : len(alt) - 1]  # Trim down to just the text
            self.alt = alt

        return self


async def get_xkcd(query):
    db = database.XKCD_Database()
    query = query.lower()
    if query == "random":
        xkcd_tuple = await db.get_random_xkcd()
    elif query in ["new", "newest"]:
        xkcd_tuple = await db.get_newest_xkcd()
    elif query.isnumeric():
        xkcd_tuple = await db.get_id(query)
    elif await list_check(query):
        xkcd_tuple = await db.get_xkcd(query)
    else:
        xkcd_tuple = await db.get_xkcd(await sugg(query))
    return get_embed(xkcd_tuple)


def get_embed(xkcd_tuple):
    e = discord.Embed(title=xkcd_tuple[0])
    e.set_image(url=xkcd_tuple[1])
    e.set_footer(text=xkcd_tuple[2])  # Alt text
    return e


async def update_db(loop):
    current = await get_list()  # list of comics currently in the database
    db = database.XKCD_Database()
    r = requests.get(
        "https://xkcd.com/archive/"
    )  # Grab the archive page, a list of all xkcd comics
    raw_names = re.findall(
        r'[0-9]{0,4}/" title="[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}">[^<>]+<',
        r.content.decode(),
    )  # Grab sections of html containing names
    xkcds = []
    for name in raw_names:
        strip = xkcd.from_raw_name(
            name
        )  # Create an xkcd object from the raw data
        if (
            not strip.name in current
        ):  # We only need to add comics we don't have
            xkcds.append(strip)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        calls = [
            loop.run_in_executor(executor, strip.get_uri_alt) for strip in xkcds
        ]

    strips = await asyncio.gather(*calls)

    for strip in strips:  # Run calls
        await db.insert_xkcd(strip)  # Add to db
        utilities.log_message(f"Added new xkcd comic {strip.name}.")

    utilities.log_message("xkcd database up to date!")


async def get_list():  # Grab the list of names of xkcds
    db = database.XKCD_Database()
    return await db.get_xkcd_list()


async def list_check(query):  # Ensure we have the xkcd of name 'query'
    if query in await get_list():
        return True
    return False


async def sugg(query):
    best = 0.5  # Suggestions must be at least 50% similar
    best_name = "not available"  # the comic "not available" is our 404 message
    for name in await get_list():
        r = difflib.SequenceMatcher(a=name, b=query).ratio()
        if r > best:
            best = r
            best_name = name
    return best_name


def update_db_schedule(interval, client):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while not client.is_ready():
        time.sleep(0.5)

    while not client.is_closed():
        loop.run_until_complete(update_db(loop))
        time.sleep(interval)
    sys.exit()


def start_db_thread(interval, client):
    thread = threading.Thread(
        target=update_db_schedule, args=[interval, client]
    )
    thread.start()
    utilities.log_message("Started XKCD update thread.")


def init_db():
    database.XKCD_Database()
