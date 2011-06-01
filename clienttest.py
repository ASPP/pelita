from pelita.remote import TcpConnectingClient

sock = TcpConnectingClient()
conn = sock.handle_connect()

from pelita.remote.jsonconnection import MailboxConnection
a = MailboxConnection(conn)
a.start()

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


ac = ClientActor(a.inbox)
ac.start()

ac.send(a, Message("hello", "Im there"))


import time
try:
    while 1:
        time.sleep(10)
except KeyboardInterrupt:
    print "Interrupted"
    ac.stop()
    a.stop()


