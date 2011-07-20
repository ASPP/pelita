# -*- coding: utf-8 -*-

import Queue
import socket

import logging
_logger = logging.getLogger("pelita.mailbox")
_logger.setLevel(logging.DEBUG)

from pelita.messaging.utils import SuspendableThread, CloseThread, Counter
from pelita.messaging.remote import MessageSocketConnection, JsonSocketConnection
from pelita.messaging import Actor, StopProcessing, DeadConnection, DispatchingActor, dispatch

import weakref

class RequestDB(object):
    """ Class which holds weak references to all issued requests.

    It is important to use weak references here, so that they are
    automatically removed from this class, whenever the original
    `Request` object is deleted and garbage collected.
    """
    def __init__(self):
        self._db = weakref.WeakValueDictionary()
        self._counter = Counter(0)

    def get_request(self, id, default=None):
        """ Return the `Request` object with the specified `id`.
        """
        return self._db.get(id, default)

    def add_request(self, request):
        """ Add a new `Request` object to the database.

        The object is only referenced weakly, so if the main
        reference is deleted, it may be removed automatically
        from the database as well.
        """
        id = self.create_id()
        self._db[id] = request
        return id

    def create_id(self, id=None):
        """ Create a new and hopefully unique id for this database.
        """
        if id is None:
            return self._counter.inc()
        else:
            _logger.info("Using existing id.")
            return id

class JsonThreadedInbox(SuspendableThread):
    def __init__(self, mailbox, **kwargs):

        self.mailbox = mailbox
        self.connection = mailbox.connection
        self.request_db = mailbox.request_db

        super(JsonThreadedInbox, self).__init__(**kwargs)

    def _run(self):
        try:
            recv = self.connection.read()
        except socket.timeout as e:
            _logger.debug("socket.timeout: %r (%r)" % (e, self))
            return
        except DeadConnection:
            _logger.debug("Remote connection is dead, closing mailbox in %r", self)
            self.mailbox.stop()
            raise CloseThread

        _logger.info("Processing inbox %r", recv)

        id = recv.get("id")
        actor = recv.get("actor")

        channel = self.request_db.get_request(id)

        if channel is None:
            channel = self.mailbox.dispatcher(actor)

        print channel, type(channel)

        proxy = ActorProxy(self.mailbox.outbox) # ???
        self.mailbox.outbox.ref = proxy

        channel.put(recv.get("message"), sender=proxy)

# TODO Not in use now, we rely on timeout until we know better
#    def stop(self):
#        SuspendableThread.stop(self)
#
#        self.connection.connection.shutdown(socket.SHUT_RDWR)
#        self.connection.close()

class JsonThreadedOutbox(SuspendableThread):
    def __init__(self, mailbox):
        super(JsonThreadedOutbox, self).__init__()

        self.mailbox = mailbox
        self.connection = mailbox.connection
        self.request_db = mailbox.request_db
        self._queue = Queue.Queue()

    def _run(self):
        self.handle_outbox()

    def handle_outbox(self):
        try:
            to_send = self._queue.get(True, 3)

            _logger.info("Processing outbox %r", to_send)
            if to_send is StopProcessing:
                raise CloseThread

            self.connection.send(to_send)
        except Queue.Empty:
            pass

    def put(self, message, channel=None):
        actor = "main-actor"
        if channel:
            id = self.request_db.add_request(channel)
            self._queue.put({"actor": actor, "message": message, "id": id})
        else:
            self._queue.put({"actor": actor, "message": message})

class MailboxConnection(object):
    """A mailbox bundles an incoming and an outgoing connection."""
    def __init__(self, connection, remote, main_actor=None, **kwargs):
        _logger.debug("Init new MailboxConnection %r" % self)
        super(MailboxConnection, self).__init__(**kwargs)
        self.connection = JsonSocketConnection(connection)

        self.remote = remote

#        self.inbox = ForwardingInbox(self, request_db=self._requests)
#        self.inbox.forward_to = main_actor
        self.request_db = RequestDB()

        self.main_actor = main_actor

        self.inbox = JsonThreadedInbox(self)
        self.outbox = JsonThreadedOutbox(self)

#        main_actor.link(self.inbox)
    def dispatcher(self, actor):
        return self.remote.reg[actor]

    def on_receive(self, message):
        print "Forwarding"
        self.main_actor.forward(message)

    def start(self):
        _logger.info("Starting mailbox %r", self)
        self.inbox.start()
        self.outbox.start()

    def stop(self):
        _logger.info("Stopping mailbox %r", self)
        #self.inbox._queue.put(StopProcessing)
        self.outbox._queue.put(StopProcessing) # I need to to this or the thread will not stop...
        self.inbox.stop()
        self.outbox.stop()
        self.connection.close()


class RemoteConnections(DispatchingActor):
    def __init__(self, *args, **kwargs):
        super(RemoteConnections, self).__init__(*args, **kwargs)
        self.connections = {}

    @dispatch
    def add_connection(self, message, connection, mailbox):
        _logger.debug("Adding connection")
        self.connections[connection] = mailbox
        mailbox.start()

    @dispatch
    def remove_connection(self, message, connection):
        del self.connections[connection]

    @dispatch
    def get_connections(self, message):
        message.reply(self.connections)

    def on_stop(self):
        for box in self.connections.values():
            box.stop()


from pelita.messaging.remote import TcpThreadedListeningServer, TcpConnectingClient
from pelita.messaging.actor import actor_of, ActorProxy
class Remote(object):
    def __init__(self):
        self.remote_ref = actor_of(RemoteConnections)
        self.listener = None

        self.reg = {}

    def start_listener(self, host, port):
        self.remote_ref.start()
        self.listener = TcpThreadedListeningServer(host=host, port=port)

        def accepter(connection):
        # a new connection has been established
            mailbox = MailboxConnection(connection, self, main_actor=self.remote_ref)
            self.remote_ref.notify("add_connection", [connection, mailbox])

        self.listener.on_accept = accepter
        self.listener.start()

        return self

    def actor_for(self, name, host, port):
        sock = TcpConnectingClient(host=host, port=port)
        conn = sock.handle_connect()

        remote = MailboxConnection(conn, self)
        remote.start()

        def actor_for(name, connection):
            # need access to a bidirectional dispatcher mailbox

            proxy = ActorProxy(connection.outbox)
            connection.ref = proxy
            return proxy

        remote_actor = actor_for(name, remote)
        return remote_actor

    def register(self, name, actor_ref):
        self.reg[name] = actor_ref

    def start_all(self):
        for ref in self.reg.values():
            ref.start()

    def stop(self):
        for ref in self.reg.values():
            ref.stop()
        if self.listener:
            self.listener.stop()
        self.remote_ref.stop()
