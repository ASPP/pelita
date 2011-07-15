# -*- coding: utf-8 -*-

import Queue
import socket

import logging
_logger = logging.getLogger("pelita.mailbox")
_logger.setLevel(logging.DEBUG)

from pelita.messaging.utils import SuspendableThread, CloseThread
from pelita.messaging.remote import MessageSocketConnection
from pelita.messaging import Actor, StopProcessing, DeadConnection, ForwardingActor, Query, Request, DispatchingActor, dispatch

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
        self._db[request.id] = request

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

        message = recv
        _logger.info("Processing inbox %r", message.dict)
        # add the mailbox to the message
        message.mailbox = self.mailbox
        self.forward_message(message)

    def forward_message(self, message):
        self.mailbox.put(message)

# TODO Not in use now, we rely on timeout until we know better
#    def stop(self):
#        SuspendableThread.stop(self)
#
#        self.connection.connection.shutdown(socket.SHUT_RDWR)
#        self.connection.close()

class IncomingActor(Actor):
    pass

class ForwardingInbox(ForwardingActor, JsonThreadedInbox):
    pass

class JsonThreadedOutbox(SuspendableThread):
    def __init__(self, connection):
        super(JsonThreadedOutbox, self).__init__()

        self.connection = connection
        self._queue = Queue.Queue()

        self.put = self._queue.put

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

class MailboxConnection(Actor):
    """A mailbox bundles an incoming and an outgoing connection."""
    def __init__(self, connection, main_actor, **kwargs):
        super(MailboxConnection, self).__init__(**kwargs)
        self.connection = MessageSocketConnection(connection)

#        self.inbox = ForwardingInbox(self, request_db=self._requests)
#        self.inbox.forward_to = main_actor

        self.main_actor = main_actor

        self.inbox = JsonThreadedInbox(self)
        self.outbox = JsonThreadedOutbox(self.connection)

#        main_actor.link(self.inbox)

    def on_receive(self, message):
        print "Forwarding"
        self.main_actor.forward(message)

    def on_start(self):
        _logger.info("Starting mailbox %r", self)
        self.inbox.start()
        self.outbox.start()

    def on_stop(self):
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
    def add_connection(self, message, connection):
        mailbox = MailboxConnection(connection, main_actor=actor_ref) # which actor?
        self.connections[connection] = mailbox
        mailbox.start()

    @dispatch
    def remove_connection(self, message, connection):
        del self.connections[connection]

    @dispatch
    def get_connections(self, message):
        message.reply(self.connections)

from pelita.messaging.remote import TcpThreadedListeningServer, TcpConnectingClient
from pelita.messaging.actor import actor_of
class Remote(object):
    def __init__(self):
        self.remote_ref= actor_of(Remote)
        self.listener = None

        self.reg = {}

    def start_listener(self, host, port):
        self.listener = TcpThreadedListeningServer(host=host, port=port)

        def accepter(connection):
        # a new connection has been established
            self.remote_ref.notify("add_connection", connection)

        self.listener.on_accept = accepter
        self.listener.start()


        return self

    def actor_for(self, name, host, port):
        sock = TcpConnectingClient(host=host, port=port)
        conn = sock.handle_connect()

        actor = ClientActor()
        actor.start()

        remote = MailboxConnection(conn, actor)
        remote.start()

        return remote

        def actorFor(connection):
            # need access to a bidirectional dispatcher mailbox
            return RemoteActorProxy(connection)

        remote_actor = actorFor(conn)

        remote_actor = RemoteActorProxy(remote)
        remote_actor.notify("hello", "Im there")




    def register(self, actor_name, actor_ref):
        self.reg[actor_name] = actor_ref
        return self

    def start_all(self):
        for ref in self.reg.values():
            ref.start()
