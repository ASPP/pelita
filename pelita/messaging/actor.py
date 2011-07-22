# -*- coding: utf-8 -*-

import Queue
import logging
import uuid

from pelita.messaging.utils import SuspendableThread, CloseThread

_logger = logging.getLogger("pelita.actor")
_logger.setLevel(logging.DEBUG)


class Channel(object):
    """ A `Channel` is an object which may be sent a message.

    This is either a `Request` object or an `ActorProxy`.
    """
    def put(self, message, sender=None, remote=None):
        raise NotImplementedError

    @property
    def uuid(self):
        """ Returns a UUID for this Channel. """
        # we use a string representation of the uuid
        # to avoid errors when converting to json and back
        if not hasattr(self, "_uuid"):
            self._uuid = str(uuid.uuid4())
        return self._uuid


class Request(Channel):
    """ A `Request` is an object which holds a future value.

    A `Request` object is automatically created when doing a
    query and a reference to it is passed to the `Actor`.

    The `Actor` may then reply to the `Request` exactly once.
    """
    def __init__(self):
        self._queue = Queue.Queue(maxsize=1)

    def put(self, message, sender=None, remote=None):
        """ Sets the result of the Request to `method`.

        The other arguments will be discarded.
        """
        self._queue.put(message)

    def get(self, block=True, timeout=3):
        return self._queue.get(block, timeout)

    def get_or_none(self):
        """Returns the result or None, if the value is not available."""
        try:
            return self._queue.get(False).result
        except Queue.Empty:
            return None

    def has_result(self):
        """Checks whether a result is available.

        This method does not guarantee that a subsequent call of Request.get() will succeed,
        because the result could have been removed by another thread.

        However, unless there is code which calls get() in the background, this method
        should be save to use.
        """
        return self._queue.full()

class DeadConnection(Exception):
    """Raised when the connection is lost."""

class StopProcessing(object):
    """If a thread encounters this value in a queue, it is advised to stop processing."""

class Exit(object):
    def __init__(self, sender, reason):
        self.sender = sender
        self.reason = reason

class AbstractActor(object):
    def request(self, method, params=None, id=None):
        raise NotImplementedError

    def request_timeout(self, method, params=None, id=None, timeout=None):
        return self.request(method, params, id).get(True, timeout)

    def send(self, method, params=None):
        raise NotImplementedError

class BaseActor(SuspendableThread):
    """ BaseActor is an actor with no pre-defined queue.
    """
    def __init__(self, **kwargs):
        super(BaseActor, self).__init__(**kwargs)

        self._ref = None

        self._trap_exit = False
        self._linked_actors = []

    @property
    def ref(self):
        return self._ref

    def _run(self):
        try:
            message, sender, priority, remote = self.handle_inbox()
        except Queue.Empty:
            return

        if isinstance(message, Exit):
            if not self._trap_exit:
                self.exit_linked(message)
                _logger.info("Exiting because of %r", message)
                raise CloseThread()

        if message is StopProcessing:
            raise CloseThread()

        # default
        try:
            _logger.debug("Received message %r.", message)
            self.ref._current_message = message
            self.ref._channel = sender
            self.ref._remote = remote

            self.on_receive(message)

            self.ref._current_message = None
            self.ref._channel = None
            self.ref._remote = None
        except Exception as e:
            exit_msg = Exit(self, e)
            self.exit_linked(exit_msg)
            raise

    def exit_linked(self, exit_msg):
        while self._linked_actors:
            linked = self._linked_actors[0]
            self.ref.unlink(linked)
            linked.put(exit_msg)

    def on_start(self):
        """
        This method is called *before* an actor is started.
        """
        pass

    def on_receive(self, message):
        """
        This method is called, whenever a new message is received.
        """
        pass

    def on_stop(self):
        """
        This method is called *after* an actor is stopped.
        """
        pass

    def start(self):
        self.on_start()
        super(BaseActor, self).start()

    def stop(self):
        super(BaseActor, self).stop()
        self.on_stop()

    def handle_inbox(self):
        pass

class Actor(BaseActor):
    # TODO Handle messages not replied to – else the queue is waiting forever
    def __init__(self, inbox=None):
        super(Actor, self).__init__()

        self._inbox = inbox or Queue.Queue()

    def handle_inbox(self):
        msg = self._inbox.get(True, 3)
        return (msg.get("message"),
                msg.get("channel"),
                msg.get("priority", 0),
                msg.get("remote"))

    def forward(self, message):
        self._inbox.put(message)

    def put(self, message, sender=None, remote=None):
        msg = {
            "message": message,
            "channel": sender,
            "remote": remote,
            "priority": 0
        }
        self._inbox.put(msg)

class BaseActorProxy(Channel):
    """ An `ActorProxy` is used to send all requests and notifications
    to the actor. It also holds the currently processed message and information
    about the sender.

    Every local `ActorProxy` has a 1:1 reference to an `Actor`.
    The splitting is due to the fact that the `Actor` class must be
    subclassed and thus we avoid some name clashes.
    """
    def __init__(self, actor):
        """ Helper class to send messages to an actor.
        """
        self._id = self.uuid

        self._actor = actor

        self._channel = None
        self._remote = None
        self._current_message = None

    @property
    def id(self):
        return self._id

    @property
    def current_message(self):
        return self._current_message

    @property
    def channel(self):
        """ The channel is the sender of the current message. (If there is any.)

        This may be an actor proxy or a waiting request.
        """
        return self._channel

    @property
    def remote(self):
        return self._remote

    def reply(self, value):
        self.channel.put(value, self)

    def notify(self, method, params=None):
        message = {"method": method,
                   "params": params}
        self.put(message)

    def query(self, method, params=None):
        query = {"method": method,
                 "params": params}
        req_obj = Request()

        self.put(query, req_obj)

        return req_obj

    def __repr__(self):
        return "%s(%s)" % (self.__class__, self._actor)

class ActorProxy(BaseActorProxy):
    def put(self, value, sender=None, remote=None):
        """ Puts a raw value into the actor’s inbox
        """
        if hasattr(self, "is_running") and not self.is_running:
            raise RuntimeError("Actor '%r' not running." % self._actor)

        _logger.debug("Putting '%r' into '%r' (channel: %r)" % (value, self._actor, sender))
        self._actor.put(value, sender, remote)

    def link(self, other):
        """ Links this actor to another actor and vice versa.

        When an actor exits (due to an Exception or because of a normal exit),
        it sends a StopProcessing message to all linked actors which will then do
        the same.

        This means that it is possible to notify other actors when one actor closes.
        """
        self.link_to(other)
        other.link_to(self)

    def unlink(self, other):
        self.unlink_from(other)
        other.unlink_from(self)

    def link_to(self, other):
        if not other in self._actor._linked_actors:
            self._actor._linked_actors.append(other)

    def unlink_from(self, other):
        while other in self._actor._linked_actors:
            self._actor._linked_actors.remove(other)

    @property
    def trap_exit(self):
        return self._actor._trap_exit

    @trap_exit.setter
    def trap_exit(self, value):
        self._actor._trap_exit = value

    @property
    def is_running(self):
        return self._actor._running

    def join(self, timeout):
        return self._actor._thread.join(timeout)
    @property
    def is_alive(self):
        return self._actor._thread.is_alive()

    def start(self):
        self._actor.start()

    def stop(self):
        self._actor.put(StopProcessing)

class RemoteProxy(BaseActorProxy):
    def __init__(self, actor):
        super(RemoteProxy, self).__init__(actor)

        self.remote_name = None

    def put(self, message, channel=None, remote=None):
        remote_name = self.remote_name
        sender_info = repr(channel)

        if channel:
            uuid = self._actor.request_db.add_request(channel)
            self._actor.outbox.put({"actor": remote_name,
                                    "sender": uuid,
                                    "message": message,
                                    "sender_info": sender_info})
        else:
            self._actor.outbox.put({"actor": remote_name,
                                    "message": message,
                                    "sender_info": sender_info})


def dispatch(method=None, name=None):
    if name and not method:
        return lambda fun: dispatch(fun, name)
    method.__dispatch = True
    method.__dispatch_as = name
    return method

class DispatchingActor(Actor):
    """ The DispatchingActor allows methods of the form

    @dispatch
    def some_action(self, method, *args)

    which may be called as

    actor = DispatchingActor()
    actor.send("some_action", params)

    An alternative form which allows for calling with a different name
    is available

    @dispatch(name="action")
    def some_action(self, method, *args)

    actor.send("action", params)
    """

#
# Messages we accept
# TODO: It is still unclear where to put the arguments
# and where to put the sender/message object
#
# a)
#   def method(self, message, arg1, *args):
#       sender = message.sender
#       message.reply(...)
#
# b)
#   def method(self, arg1, *args):
#       self.sender         # set in the loop before, quasi global
#       self.reply(...)     # set in the loop before, quasi global
#
# c)
#   def method(self, message):
#       args = message.params
#       sender = message.sender
#       message.reply(...)
#
# d)
#   use inner functions inside receive()
#

    def __new__(cls, *args, **kwargs):
        cls._init_dispatch_db()
        return super(DispatchingActor, cls).__new__(cls, *args, **kwargs)

    def __init__(self, inbox=None):
        super(DispatchingActor, self).__init__(inbox)

        self._init_dispatch_db()

    @classmethod
    def _init_dispatch_db(cls):
        cls._dispatch_db = {}
        # search all attributes of this class
        for member_name in dir(cls):
            member = getattr(cls, member_name)
            if getattr(member, "__dispatch", False):
                name = getattr(member, "__dispatch_as", None)
                if not name:
                    name = member_name
                if name in cls._dispatch_db:
                    raise ValueError("Dispatcher name '%r' defined twice", name)
                cls._dispatch_db[name] = member_name

    def _dispatch(self, message):
        method = message.get("method")
        params = message.get("params")

        def reply_error(msg):
            if self.ref.channel:
                self.ref.reply(msg)
            else:
                _logger.warning(msg)

        wants_doc = False
        if method[0] == "?":
            method = method[1:]
            wants_doc = True

        method_name = self._dispatch_db.get(method)
        if not method_name:
            self.on_unhandled(message)
            return

        meth = getattr(self, method_name, None)
        if not meth:
            self.on_unhandled(message)
            return

        if wants_doc:
            if self.ref.channel:
                res = meth.__doc__
                self.ref.reply(res)
            else:
                _logger.warning("Doc requested but no channel given.")

        try:
            if params is None:
                res = meth(message)

            elif isinstance(params, dict):
                res = meth(message, **params)

            else:
                res = meth(message, *params)
        except TypeError, e:
            reply_error("Type Error: method '%r'\n%r" % (message.get("method"), e))
            return

# TODO: Need to consider, if we want to automatically reply the result
#
#        if hasattr(message, "reply"):
#            message.reply(res)

    def on_receive(self, message):
        self._dispatch(message)

    def on_unhandled(self, message):
        """ Called when no method fits the message.

        This method may be overridden to include other error handling mechanisms.
        """
        def reply_error(msg):
            if self.ref.channel:
                self.ref.reply(msg)
            else:
                _logger.warning(msg)
        reply_error("Not found: method '%r'" % message.get("method"))


def actor_of(actor, name=None):
    return actor_registry.register(actor, name)

def _check_actor_correctness(actor):
    methods = []
    return all(hasattr(actor, meth) for meth in methods)


import inspect
from threading import Lock

_registry_lock = Lock()

class ActorRegistry(object):
    def __init__(self):
        self._reg = {}

    def register(self, actor, name=None):
        with _registry_lock:
            if inspect.isclass(actor):
                actor = actor()

            # We should check that our actor has all the methods, the ActorRef needs.
            # This ensures (only a little) that our actor thread does not fail at
            # runtime because it expects other methods.
            assert _check_actor_correctness(actor), "Actor does not follow spec."

            proxy = ActorProxy(actor)
            actor._ref = proxy

            if name:
                self._reg[name] = proxy

            self._reg[proxy.uuid] = proxy

            return proxy

    def get_by_name(self, name, default=None):
        with _registry_lock:
            return self._reg.get(name, default)

    def get_by_uuid(self, uuid, default=None):
        with _registry_lock:
            return self._reg.get(uuid, default)

actor_registry = ActorRegistry()

