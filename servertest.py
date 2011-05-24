import yappi
yappi.start() # start the profiler

from pelita.remote.listening_server import JsonThreadedListeningServer, CONNECTIONS
import threading


def show_num_threads():
    print "%d threads alive" % threading.active_count()
    t = threading.Timer(5, show_num_threads)
    t.start()
t = threading.Timer(5, show_num_threads)
t.start()


s = JsonThreadedListeningServer()
s.start()

while 1:
    from pelita.remote.jsonconnection import JsonThreadedSocketConnection
    conn = CONNECTIONS.get()
    cq = JsonThreadedSocketConnection(conn)
    cq.start()
    cq.join()


while 1:
    y = raw_input("yappi>")
    exec y


