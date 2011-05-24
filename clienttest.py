from pelita.remote.rpcsocket import JsonConnectingClient
from pelita.remote.jsonconnection import JsonSocketConnection
sock = JsonConnectingClient()
conn = sock.handle_connect()

jsc = JsonSocketConnection(conn)
jsc.send("a")
jsc.send("a")
jsc.send("a")
jsc.send("a")
jsc.send("a")

from actors.actor import Actor

a = Actor()
a.remote = JsonSocketConnection
a.start()

