from pelita.remote import TcpConnectingClient

sock = TcpConnectingClient()
conn = sock.handle_connect()

#from actors.actor import Actor

# class RemoteActor(threading.Thread):
    # @property
    # def remote(self):
        # return self._remote

    # @remote.setter
    # def remote(self, value):
        # self._remote = value

    # def start(self):
        # self.remote.start()

    # def stop(self):
        # self.remote.stop()

    # def send(self, msg):
        # self.remote.send(msg)

    # def request(self, msg):
        # return self.remote.request(msg)

    # def request_recv(self, msg, timeout=0):
        # return self.request(msg).get(timeout)

#a = RemoteActor()
#a.remote = JsonThreadedSocketConnection(conn)
#a.start()

from pelita.remote.jsonconnection import MailboxConnection
a = MailboxConnection(conn)
a.start()

from pelita.actors import RemoteActor

ac = RemoteActor(a.inbox)
ac.start()

from pelita.remote.jsonconnection import Message

ac.send(a, Message("shutdown", None).rpc)


from pelita.actors.actor import ProxyActor
ap = ProxyActor(ac)

ap.query

#a.put({"method": "shutdon", "params": None})

#print a.get()

#print a._outbox._queue.qsize()
#print a.request_recv("Hello")

#a._inbox._queue.join()
import time
time.sleep(3)

#yappi.print_stats()

#print a._outbox._queue.qsize()

ac.stop()
a.stop()


