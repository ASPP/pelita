from pelita.remote import TcpConnectingClient
from pelita.remote.jsonconnection import MailboxConnection

from pelita.actors import RemoteActor
from pelita.actors import Message, Query, Error

def init(*params):
    print params

class ClientActor(RemoteActor):
    def receive(self, sender, message):
        if message.method == "init":
            reply = init(*message.params)

        elif message.method == "statechanged":
            sender.put(message.reply("NORTH"))

        else:
            reply = Error("Message not found")

sock = TcpConnectingClient()
conn = sock.handle_connect()

remote = MailboxConnection(conn)
remote.start()

actor = ClientActor(remote.inbox)
actor.start()

actor.send(remote, Message("hello", "Im there"))


import time
try:
    while 1:
        time.sleep(10)
except KeyboardInterrupt:
    print "Interrupted"
    actor.stop()
    remote.stop()


