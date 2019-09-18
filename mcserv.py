import paramiko # SSH interface
import socket # socket timeout exception
import time # limit how often server is rebooted

class SSH():
    def __init__(self, **kwargs):
        self.ip = kwargs.get('address')
        self.port = kwargs.get('port') if kwargs.get('port') is not None else 22
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.timeout = kwargs.get('timeout') if kwargs.get('timeout') is not None else 3

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.channel = None
        self.out = ''

    def connect(self):
        self.client.connect(self.ip, self.port, username = self.username, password = self.password)
        self.channel = self.client.invoke_shell()
        self.channel.settimeout(self.timeout)

        self.read()

        return self # Allow for code like SSH().connect()
    
    def close(self):
        self.channel.close()
        self.client.close()

    def exec_command(self, command):
        self.channel.send(f'{command}\n')
        self.read()

    def read(self):
        self.out = ''
        while True:
            try:
                self.out += self.channel.recv(1).decode()
            except socket.timeout:
                break

def reboot(config):
    ssh = SSH(**config).connect() # Connect to the server

    ssh.exec_command('screen -r minecraft') # Navigate to the apropriate screen

    if 'There is no screen to be resumed matching minecraft.' in ssh.out: # Screen failed, create a new one
        ssh.exec_command('screen -S minecraft')

    ssh.exec_command('stop') # Stop the server (in the case it isn't running this will just write to stderr: no problem)
    ssh.exec_command('./start.sh') # (re)start the server

    ssh.close() # Close the connection

class Vote():
    def __init__(self, user, vote_time):
        self.user = user
        self.vote_time = vote_time

    @property
    def age(self):
        return time.time() - self.vote_time

class CommandHandler():
    def __init__(self, config):
        self.config = config
        self.reboot_interval = config.get('reboot_interval')
        self.reboot_votes = config.get('reboot_votes')

        self.previous_reboot = 0
        self.votes = []

    def handle_command(self, command, sender):
        """Accepts the command sent and the senders username."""
        if command == 'reboot':
            sender_votes = [v for v in self.votes if v.user == sender]
            if sender_votes:
                self.votes.remove(sender_votes[0])

            self.votes.append(Vote(sender, time.time()))

            for v in [v for v in self.votes if v.age > 3600]:
                self.votes.remove(v)

            if len(self.votes) < self.reboot_votes:
                return f'Not enough users want a reboot. {self.reboot_votes - len(self.votes)} more votes required within {int(self.reboot_interval / 3600)} hour(s).'
            elif time.time() - self.previous_reboot < self.reboot_interval:
                return f'Too soon after last reboot. Please wait {int((self.reboot_interval - (time.time() - self.previous_reboot)) / 60)} more minutes.'
            else:
                reboot(self.config)
                self.previous_reboot = time.time()
                return 'Server rebooted. Should be online shortly. If it isn\'t, poke Owen, it\'s probably his fault.'                

        else:
            return 'Command not available. Available commands:\n\treboot'
            