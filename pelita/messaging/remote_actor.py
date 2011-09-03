# -*- coding: utf-8 -*-

"""
Remote actor setup and bookkeeping of remote requests.
"""

import Queue
import socket
import weakref
from threading import Lock, RLock

import logging
_logger = logging.getLogger("pelita.mailbox")
_logger.setLevel(logging.DEBUG)

__docformat__ = "restructuredtext"


from pelita.utils import SuspendableThread, CloseThread, Counter
from pelita.messaging.remote import JsonSocketConnection, TcpThreadedListeningServer, TcpConnectingClient
from pelita.messaging.actor import StopProcessing, DeadConnection, actor_registry, BaseActorReference


class RequestDB(object):
    """ Class which holds weak references to all issued requests.

    It is important to use weak references here, so that they are
    automatically removed from this class, whenever the original
    `Request` object is deleted and garbage collected.
    """
    def __init__(self):
        self._db = weakref.WeakValueDictionary()
        self._db_lock = Lock()
        self._counter = Counter(0)

    def get_request(self, id, default=None):
        """ Return the `Request` object with the specified `id`.
        """
        with self._db_lock:
            return self._db.get(id, default)

    def add_request(self, request):
        """ Add a new `Request` object to the database.

        The object is only referenced weakly, so if the main
        reference is deleted, it may be removed automatically
        from the database as well.
        """
        with self._db_lock:
            try:
                id = self.create_id(str(request.uuid))
            except AttributeError:
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

class RemoteInbox(SuspendableThread):
    """ This class fetches all incoming messages from
    `self.mailbox.connection` and dispatches them to the
    specified actor.
    """
    def __init__(self, mailbox, **kwargs):
        self.mailbox = mailbox
        self.connection = mailbox.connection

        super(RemoteInbox, self).__init__(**kwargs)

    def _run(self):
        try:
            recv = self.connection.read()
        except socket.timeout as e:
            _logger.debug("socket.timeout: %r (%r)" % (e, self))
            return
        except DeadConnection:
            _logger.debug("Remote connection is dead, closing mailbox in %r.", self)
            self.mailbox.stop()
            raise CloseThread

        _logger.info("Processing inbox %r", recv)

        actor = recv.get("actor")
        channel = self.mailbox.dispatcher(actor)

        if not channel:
            _logger.warning("No channel found for message %r. Dropping." % recv)
            return

        sender = recv.get("sender")
        if sender:
            proxy = self.mailbox.create_proxy(sender)
            channel.put(recv.get("message"), channel=proxy, remote=self.mailbox)
        else:
            channel.put(recv.get("message"), remote=self.mailbox)

# TODO Not in use now, we rely on timeout until we know better
#    def stop(self):
#        SuspendableThread.stop(self)
#
#        self.connection.connection.shutdown(socket.SHUT_RDWR)
#        self.connection.close()

class RemoteOutbox(object):
    """ This class checks its outgoing queue for new messages and
    sends them through the connection specified by `self.mailbox.connection`.
    """
    def __init__(self, mailbox, **kwargs):
        super(RemoteOutbox, self).__init__(**kwargs)

        self.mailbox = mailbox
        self.connection = mailbox.connection
        self._remote_lock = Lock()

    def put(self, msg):
        with self._remote_lock:
            self.connection.send(msg)

class RemoteMailbox(object):
    """A mailbox bundles an incoming and an outgoing connection."""
    def __init__(self, connection, remote):
        self.connection = JsonSocketConnection(connection)

        self.remote = remote

        self.request_db = RequestDB()

        self.inbox = RemoteInbox(self)
        self.outbox = RemoteOutbox(self)

        # finally, add the connection to the remote database
        remote.add_connection(self.connection, self)

    def create_proxy(self, sender):
        """ Creates a proxy which has a reference to this connection and
        an identifier of the sending actor.
        """
        proxy = RemoteActorReference(remote_mailbox=self, remote_name=sender)
        return proxy

    def dispatcher(self, actor_ref_id):
        """ Tries to find the corresponding actor to the id. """
        # first, see if it is in the request_db
        channel = self.request_db.get_request(actor_ref_id, default=None)

        # now, try to find if it is registered with the remote database
        if not channel:
            channel = self.remote.get_actor(actor_ref_id, default=None)

        # fall back to the general uuid
        if not channel:
            channel = actor_registry.get_by_uuid(actor_ref_id, default=None)

        return channel

    def start(self):
        _logger.info("Starting mailbox %r", self)
        self.inbox.start()

    def stop(self):
        # TODO: this method may be called multiple times
        _logger.info("Stopping mailbox %r", self)
        self.inbox.stop()
        self.connection.close()
        try:
            self.remote.remove_connection(self.connection)
        except KeyError:
            pass

    def __repr__(self):
        return "RemoteMailbox(%r, %r)" % (self.connection, self.remote)

class RemoteConnection(object):
    def __init__(self):
        self.listener = None

        self.exposed_actor_reg = {}

        self._db_lock = RLock()
        self.connections = {}

    def add_connection(self, connection, mailbox):
        with self._db_lock:
            _logger.debug("Adding connection %r for mailbox %r.", connection, mailbox)
            self.connections[connection] = mailbox

    def remove_connection(self, connection):
        with self._db_lock:
            _logger.debug("Deleting connection %r.", connection)
            del self.connections[connection]
            if not self.connections:
                self.shutdown()

    def get_connections(self, message):
        with self._db_lock:
            return self.connections

    def shutdown(self):
        with self._db_lock:
            for box in self.connections.values():
                box.stop()

        self.on_shutdown()

    def start_listener(self, host, port):
        self.listener = TcpThreadedListeningServer(host=host, port=port)

        def accepter(connection):
        # a new connection has been established
            mailbox = RemoteMailbox(connection, self)
            mailbox.start()

        self.listener.on_accept = accepter
        self.listener.start()

        return self

    def actor_for(self, name, host, port):
        sock = TcpConnectingClient(host=host, port=port)
        try:
            conn = sock.handle_connect()
        except socket.error:
            raise DeadConnection

        remote = RemoteMailbox(conn, self)
        remote.start()

        def actor_for(name, connection):
            # need access to a bidirectional dispatcher mailbox

            proxy = RemoteActorReference(remote_mailbox=connection, remote_name=name)
            return proxy

        remote_actor = actor_for(name, remote)
        return remote_actor

    def register(self, name, actor_ref):
        self.exposed_actor_reg[name] = actor_ref.uuid

    def get_actor(self, name, default=None):
        uuid = self.exposed_actor_reg.get(name)
        if not uuid:
            return default

        actor = actor_registry.get_by_uuid(uuid, default)
        return actor

    def start_all(self):
        for uuid in self.exposed_actor_reg.values():
            ref = actor_registry.get_by_uuid(uuid)
            ref.start()

    def stop(self):
        for uuid in self.exposed_actor_reg.values():
            ref = actor_registry.get_by_uuid(uuid)
            ref.stop()
        if self.listener:
            self.listener.stop()
        self.shutdown()

    def on_shutdown(self):
        """ Can be overridden to inform other classes of a remote shutdown.
        """
        pass

class RemoteActorReference(BaseActorReference):
    def __init__(self, remote_mailbox, remote_name, **kwargs):
        self.remote_name = remote_name
        self._remote_mailbox = remote_mailbox

        super(RemoteActorReference, self).__init__(**kwargs)

    def put(self, message, channel=None, remote=None):
        remote_name = self.remote_name
        sender_info = repr(channel) # only used for debugging

        if channel:
            # We’ve been given a channel to reply to (either an ActorReference
            # or a Request). Store a reference to the channel and send an uuid
            # over the network. This uuid can then be used by the remote
            # actor to reply to this message.
            uuid = self._remote_mailbox.request_db.add_request(channel)

            self._remote_mailbox.outbox.put({"actor": remote_name,
                                             "sender": uuid,
                                             "message": message,
                                             "sender_info": sender_info})
        else:
            self._remote_mailbox.outbox.put({"actor": remote_name,
                                             "message": message,
                                             "sender_info": sender_info})
