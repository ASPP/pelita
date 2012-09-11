import unittest
import queue

from pelita.messaging.remote import TcpThreadedListeningServer, TcpConnectingClient

class TestConnection(unittest.TestCase):
    def test_accept(self):
        # Bind to this machine with an arbitrary free port
        listener = TcpThreadedListeningServer(host="localhost", port=0)

        # We use a Queue to wait until the connection is established
        timeout = 1
        q = queue.Queue()

        # define, what to do, when we get a connection
        def acceptor(connection):
            q.put(connection)

        listener.on_accept = acceptor
        listener.start()

        host = listener.socket.host
        port = listener.socket.port

        conn = TcpConnectingClient(host=host, port=port)
        sock = conn.handle_connect()

        try:
            received_conn = q.get(True, timeout)
        except queue.Empty:
            raise AssertionError("Timed out. No connection in %d secs." % timeout)

        # check that both use the same port
        self.assertEqual(port, sock.getpeername()[1])

        # close everything
        listener.stop()
        listener.thread.join()

if __name__ == '__main__':
    unittest.main()
