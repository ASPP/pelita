from pelita.remote.rpcsocket import JsonConnectingClient
from pelita.remote.jsonconnection import JsonThreadedSocketConnection, MailboxConnection
sock = JsonConnectingClient()
conn = sock.handle_connect()

jsc = JsonThreadedSocketConnection(conn)
#jsc.send("a")
#jsc.send("a")
#jsc.send("a")
#jsc.send("a")
#jsc.send("a", False)

#from actors.actor import Actor
import threading

mc = MailboxConnection(conn)
mc.put("jhjhfhjfjf")

class RemoteActor(threading.Thread):
    @property
    def remote(self):
        return self._remote

    @remote.setter
    def remote(self, value):
        self._remote = value

    def start(self):
        self.remote.start()

    def stop(self):
        self.remote.stop()

    def send(self, msg):
        self.remote.send(msg)

    def request(self, msg):
        return self.remote.request(msg)

    def request_recv(self, msg, timeout=0):
        return self.request(msg).get(timeout)

a = RemoteActor()
a.remote = JsonThreadedSocketConnection(conn)
a.start()

from pelita.remote.jsonconnection import MailboxConnection
#a = MailboxConnection(conn)

#a.put("Hello")
#print a.request_recv("Hello")

a.stop()


