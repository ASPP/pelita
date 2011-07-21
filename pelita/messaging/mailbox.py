# -*- coding: utf-8 -*-

import Queue
import socket

import logging
_logger = logging.getLogger("pelita.mailbox")
_logger.setLevel(logging.DEBUG)

from pelita.messaging.utils import SuspendableThread, CloseThread, Counter
from pelita.messaging.remote import MessageSocketConnection, JsonSocketConnection
from pelita.messaging import Actor, RemoteProxy, StopProcessing, DeadConnection, DispatchingActor, dispatch, BaseActorProxy, actor_registry

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
        id = self.create_id(str(getattr(request, "uuid")))
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

        actor = recv.get("actor")

        channel = self.request_db.get_request(actor)

        if channel is None:
            channel = self.mailbox.dispatcher(actor)

        # if no channel can be found: create a new one which uses this connection.
        # {from: uuid, to: uuid or actor_name, message: ... }

        print channel, type(channel)

        sender = recv.get("sender")
        if sender:
            proxy = self.mailbox.create_proxy(sender)
            channel.put(recv.get("message"), sender=proxy, remote=self.mailbox)
        else:
            channel.put(recv.get("message"), remote=self.mailbox)

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

    def put(self, msg):
        self._queue.put(msg)

class MailboxConnection(object):
    """A mailbox bundles an incoming and an outgoing connection."""
    def __init__(self, connection, remote):
        self.connection = JsonSocketConnection(connection)

        self.remote = remote

        self.request_db = RequestDB()

        self.inbox = JsonThreadedInbox(self)
        self.outbox = JsonThreadedOutbox(self)

    def create_proxy(self, sender):
        proxy = RemoteProxy(self)
        proxy.remote_name = sender
        return proxy

    def dispatcher(self, actor):
        try:
            ref = self.remote.get_actor(actor)
        except KeyError:
            ref = actor_registry.get_by_uuid(actor)
        return ref

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
        self.connections[connection].stop()
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
            mailbox = MailboxConnection(connection, self)

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

            proxy = RemoteProxy(connection)
            proxy.remote_name = name
            return proxy

        remote_actor = actor_for(name, remote)
        return remote_actor

    def register(self, name, actor_ref):
        self.reg[name] = actor_ref.uuid

    def get_actor(self, name):
        uuid = self.reg[name]
        actor = actor_registry.get_by_uuid(uuid)
        return actor

    def start_all(self):
        for uuid in self.reg.values():
            ref = actor_registry.get_by_uuid(uuid)
            ref.start()

    def stop(self):
        for uuid in self.reg.values():
            ref = actor_registry.get_by_uuid(uuid)
            ref.stop()
        if self.listener:
            self.listener.stop()
        self.remote_ref.stop()
