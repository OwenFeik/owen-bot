<h1>owen-bot for Discord</h1>

Bot for assorted functionality, including searches for MTG cards, dice rolling and campaign management for dungeons and dragons and various humorous inclusions.

Dependencies:
    
* `discord.py`, `aiosqlite` and `requests` for general use.
* `emoji`, for operating wordart.
* `paramiko`, for minecraft server integration.

Paramiko is an optional dependancy and will not be imported if ```mcserv``` is ```false``` in the config. 
