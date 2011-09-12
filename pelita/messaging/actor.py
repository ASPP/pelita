# -*- coding: utf-8 -*-

"""
General and local actor definitions.
"""


import Queue
import uuid
import inspect
from threading import Lock

import logging
_logger = logging.getLogger("pelita.actor")
_logger.setLevel(logging.DEBUG)

from ..utils import SuspendableThread, CloseThread

__docformat__ = "restructuredtext"

class Channel(object):
    """ A `Channel` is an object which may be sent a message.

    This is either a `Request` object or an `ActorReference`.
    """
    def put(self, message, channel=None, remote=None):
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

    def put(self, message, channel=None, remote=None):
        """ Sets the result of the Request to `message`.

        The other arguments will be discarded.
        """
        self._queue.put(message)

    def get(self, timeout=3):
        """ Returns the result of the Request (if it is there).
        Else, it waits `timeout` seconds.

        Parameters
        ----------
        timeout : float, optional
            the time in seconds to wait.
            default = None (no timeout)
        """
        if timeout == 0:
            block = False
        else:
            block = True

        return self._queue.get(block, timeout)

    def get_or_none(self, timeout=0):
        """Returns the result or None, if the value is not available."""
        try:
            return self._queue.get(timeout).result
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

class ActorNotRunning(Exception):
    """Raised when the actor is not yet running or stopped."""

class StopProcessing(object):
    """If a thread encounters this value in a queue, it is advised to stop processing."""

class Exit(object):
    def __init__(self, sender, reason):
        self.sender = sender
        self.reason = reason

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
        """ Returns the `ActorReference` of the current actor.

        `ActorReference` provides the methods needed to interact
        with the `Actor` instance.
         - channel
         - notify
         - query
         - link
         - current_message
        """
        return self._ref

    def _run(self):
        """ Reads and processed the next element in the queue,
        sets the `ActorReference` to the current values and
        calls `self.on_receive`.
        """
        try:
            message, channel, priority, remote = self.handle_inbox()
        except Queue.Empty:
            return

        if isinstance(message, Exit):
            if not self._trap_exit:
                self._exit_linked(message)
                _logger.info("Exiting because of %r", message)
                raise CloseThread()

        if message is StopProcessing:
            raise CloseThread()

        # default
        try:
            _logger.debug("Received message %r.", message)
            self.ref._current_message = message
            self.ref._channel = channel
            self.ref._remote = remote

            self.on_receive(message)

            self.ref._current_message = None
            self.ref._channel = None
            self.ref._remote = None
        except Exception as e:
            exit_msg = Exit(self, e)
            self._exit_linked(exit_msg)
            raise

    def _exit_linked(self, exit_msg):
        """ If an exception occurred, tell every linked actor.
        """
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
    def __init__(self, inbox=None, **kwargs):
        self._inbox = inbox or Queue.Queue()

        super(Actor, self).__init__(**kwargs)

    def handle_inbox(self):
        """ Reads the next item from the Queue or raises Queue.Empty
        """
        msg = self._inbox.get(True, 3)
        return (msg.get("message"),
                msg.get("channel"),
                msg.get("priority", 0),
                msg.get("remote"))

    def put(self, message, channel=None, remote=None):
        msg = {
            "message": message,
            "channel": channel,
            "remote": remote,
            "priority": 0
        }
        self._inbox.put(msg)

class BaseActorReference(Channel):
    """ An `ActorReference` is used to send all requests and notifications
    to the actor. It also holds the currently processed message and information
    about the sender.

    Every local `ActorReference` has a 1:1 reference to an `Actor`.
    The splitting is due to the fact that the `Actor` class must be
    subclassed and thus we avoid some name clashes.
    """
    def __init__(self, **kwargs):
        """ Helper class to send messages to an actor.
        """
        self._id = self.uuid

        self._channel = None
        self._remote = None
        self._current_message = None

    @property
    def id(self):
        return self._id

    @property
    def current_message(self):
        """ The message which is currently processed by the `Actor`.
        """
        return self._current_message

    @property
    def channel(self):
        """ The channel is the sender of the current message. (If there is any.)

        This may be an actor proxy or a waiting request.
        """
        return self._channel

    @property
    def remote(self):
        """ The remote connection over which the message was sent (if there is any).
        """
        return self._remote

    def reply(self, value):
        self.channel.put(value, self)

    def notify(self, method, params=None, channel=None):
        message = {"method": method,
                   "params": params}
        self.put(message=message, channel=channel)

    def query(self, method, params=None):
        query = {"method": method,
                 "params": params}
        req_obj = Request()

        self.put(message=query, channel=req_obj)

        return req_obj

class ActorReference(BaseActorReference):
    def __init__(self, actor, **kwargs):
        self._actor = actor
        super(ActorReference, self).__init__(**kwargs)

    def put(self, message, channel=None, remote=None):
        """ Puts a raw value into the actor’s inbox
        """
        if not self.is_running:
            raise ActorNotRunning("Actor '%r' not running." % self._actor)
        _logger.debug("Putting '%r' into '%r' (channel: %r)" % (message, self._actor, channel))
        self._actor.put(message, channel, remote)

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

    def join(self, timeout=None):
        """ Blocks until the actor’s thread is completed or waits `timeout` seconds.
        Whatever happens earlier.

        Parameters
        ----------
        timeout : float, optional
            the time in seconds to wait.
            default = None (no timeout)
        """
        return self._actor._thread.join(timeout)

    @property
    def is_alive(self):
        return self._actor._thread.is_alive()

    def start(self):
        self._actor.start()

    def stop(self):
        self._actor.put(StopProcessing)

    def __repr__(self):
        return "%s(%s)" % (self.__class__, self._actor)

def expose(method=None, name=None):
    if name and not method:
        return lambda fun: expose(fun, name)
    method.__expose = True
    method.__expose_as = name
    return method

class DispatchingActor(Actor):
    """ The `DispatchingActor` allows methods of the form

    @expose
    def some_action(self, *args)

    which may be called as

    actor = DispatchingActor()
    actor.send("some_action", params)

    An alternative form which allows for calling with a different name
    is available

    @expose(name="action")
    def some_action(self, *args)

    actor.send("action", params)

    Note that `DispatchingActor` overrides `on_receive`.
    """

    def __new__(cls, *args, **kwargs):
        cls._init_dispatch_db()
        return super(DispatchingActor, cls).__new__(cls, *args, **kwargs)

    def __init__(self, **kwargs):
        super(DispatchingActor, self).__init__(**kwargs)

        self._init_dispatch_db()

    @classmethod
    def _init_dispatch_db(cls):
        cls._dispatch_db = {}
        # search all attributes of this class
        for member_name in dir(cls):
            member = getattr(cls, member_name)
            if getattr(member, "__expose", False):
                name = getattr(member, "__expose_as", None)
                if not name:
                    name = member_name
                if name in cls._dispatch_db:
                    raise ValueError("Dispatcher name '%r' defined twice", name)
                cls._dispatch_db[name] = member_name

    def __reply_error(self, msg):
        """ Called, when an error occurs. We either reply with the error message
        or we log a warning.
        """
        if self.ref.channel:
            self.ref.reply(msg)
        else:
            _logger.warning(msg)

    def __get_method(self, sent_name):
        local_name = self._dispatch_db.get(sent_name) or ""
        return getattr(self, local_name, None)

    def _dispatch(self, message):
        try:
            method = message["method"]
            params = message.get("params")
        except (TypeError, AttributeError, KeyError):
            # TypeError -> message must be indexable
            # AttributeError -> message must have a ‘get’ method
            # KeyError -> message must have a "method" key
            return self.on_invalid(message)

        if not isinstance(method, basestring):
            return self.__reply_error("'method' must be a string.")

        prefixes = ["?"]
        method_prefix = ""

        if method and method[0] in prefixes:
            method_prefix = method[0]
            method = method[1:]

        local_method = self.__get_method(method)
        if not local_method:
            self.on_unhandled(message)
            return

        if method_prefix == "?":
            if self.ref.channel:
                res = local_method.__doc__
                self.ref.reply(res)
            else:
                _logger.warning("Doc requested but no channel given.")

        try:
            if params is None:
                local_method()
            elif isinstance(params, dict):
                local_method(**params)
            else:
                local_method(*params)
        except TypeError as e:
            # Must inspect the stack trace, because we cannot
            # be sure, where the exception happened.
            # Was it a problem of the Actor, or did the caller
            # just have a typo somewhere?
            trace = inspect.trace()
            if len(trace) > 1:
                # The exception happened inside the code,
                # so it is really the Actor’s fault.
                # This will most probably kill the Actor.
                raise
            else:
                # The exception happened because a non-existing method
                # got called. Tell the sender what was wrong.
                self.__reply_error("Type Error: method '%r'\n%r" % (message.get("method"), e))
            return

# TODO: Need to consider, if we want to automatically reply the result
#
#        if hasattr(message, "reply"):
#            message.reply(res)

    def on_receive(self, message):
        self._dispatch(message)

    def on_invalid(self, message):
        """ Called when the method is not valid.

        This method may be overridden to include other error handling mechanisms.
        """
        self.__reply_error("Invalid message for dispatch: '%r'" % message)

    def on_unhandled(self, message):
        """ Called when no method fits the message.

        This method may be overridden to include other error handling mechanisms.
        """
        self.__reply_error("Not found: method '%r'" % message.get("method"))


def actor_of(actor, name=None):
    return actor_registry.register(actor, name)

def _check_actor_correctness(actor):
    methods = ["ref", "put", "_running", "_thread", "_trap_exit", "_linked_actors"]
    return all(hasattr(actor, meth) for meth in methods)

# the actor_registry should be unique,
# so we’ll have a lock defined on module basis
_registry_lock = Lock()

class _ActorRegistry(object):
    def __init__(self):
        self._reg = {}

    def register(self, actor, name=None):
        with _registry_lock:
            _orig_arg = actor
            if inspect.isclass(actor):
                actor = actor()

            # We should check that our actor has all the methods, the ActorRef needs.
            # This ensures (only a little) that our actor thread does not fail at
            # runtime because it expects other methods.
            if not _check_actor_correctness(actor):
                raise ValueError("Actor '%r' does not follow spec." % _orig_arg)

            proxy = ActorReference(actor)
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

actor_registry = _ActorRegistry()

