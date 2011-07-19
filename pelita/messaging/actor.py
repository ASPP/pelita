# -*- coding: utf-8 -*-

import Queue
import logging

from pelita.messaging.utils import SuspendableThread, CloseThread

_logger = logging.getLogger("pelita.actor")
_logger.setLevel(logging.DEBUG)


class Channel(object):
    def put(self, message, sender=None):
        raise NotImplementedError


class Request(Channel):
    def __init__(self):
        self._queue = Queue.Queue(maxsize=1)

    def put(self, message, sender=None):
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

        This method does not guarantee that a subsequent call of Request.get() will succeed.
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

        self.trap_exit = False
        self.linked_actors = []

    def _run(self):
        try:
            message, sender, priority = self.handle_inbox()
        except Queue.Empty:
            return

        if isinstance(message, Exit):
            if not self.trap_exit:
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

            self.on_receive(message)

            self.ref._current_message = None
            self.ref._channel = None
        except Exception as e:
            exit_msg = Exit(self, e)
            self.exit_linked(exit_msg)
            raise

    def exit_linked(self, exit_msg):
        while self.linked_actors:
            linked = self.linked_actors[0]
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
        self.ref = None

    def handle_inbox(self):
        msg = self._inbox.get(True, 3)
        return (msg.get("message"), msg.get("channel"), msg.get("priority"))

    def forward(self, message):
        self._inbox.put(message)

    def put(self, message, sender=None):
        msg = {
            "message": message,
            "channel": sender,
            "priority": 0
        }
        self._inbox.put(msg)

class ForwardingActor(object):
    """ This is a mix-in which simply forwards all messages to another actor.

    When using it, the variable `self.forward_to` needs to be set.
    """
    def on_receive(self, message):
        self.forward_to.put(message)

    def on_stop(self):
        self.forward_to.put(StopProcessing)

class ActorProxy(Channel):
    def __init__(self, actor):
        """ Helper class to send messages to an actor.
        """
        self.actor = actor

        self._channel = None
        self._current_message = None

    @property
    def current_message(self):
        return self._current_message

    @property
    def channel(self):
        return self._channel

    def start(self):
        self.actor.start()

    def stop(self):
        self.actor.put(StopProcessing)

    def reply(self, value):
        self.channel.put(value, self)

    def put(self, value, sender=None):
        """ Puts a raw value into the actor’s inbox
        """
        if not self.is_running:
            raise RuntimeError("Actor '%r' not running." % self.actor)

        _logger.debug("Putting '%r' into '%r' (channel: %r)" % (value, self.actor, sender))
        self.actor.put(value, sender)

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

    @property
    def is_running(self):
        return self.actor._running

    def join(self, timeout):
        return self.actor._thread.join(timeout)

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
        if not other in self.actor.linked_actors:
            self.actor.linked_actors.append(other)

    def unlink_from(self, other):
        while other in self.actor.linked_actors:
            self.actor.linked_actors.remove(other)

    @property
    def trap_exit(self):
        return self.actor.trap_exit

    @trap_exit.setter
    def trap_exit(self, value):
        self.actor.trap_exit = value

    @property
    def is_alive(self):
        return self.actor._thread.is_alive()

class RemoteActorProxy(object):
    def __init__(self, name, actor):
        """ Helper class to send messages to an actor.
        """
        self.actor = actor

    def start(self):
        self.actor.start()

    def stop(self):
        self.notify("stop")

    def notify(self, method, params=None):
        message = Notification(method, params)
        self.actor.outbox.put(message)

    def query(self, method, params=None, id=None):
        # Update the query.id
        if not id:
            id = self.actor.request_db.create_id(id)

        query = Query(method, params, id)
        req_obj = Request(query.id)

        # save the id to the _requests dict
        self.actor.request_db.add_request(req_obj)
        query.mailbox = self.actor
        self.actor.outbox.put(query)

        return req_obj

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
            proxy = ActorProxy(actor)
            actor.ref = proxy

            if name:
                self._reg[name] = proxy

            return proxy

    def get_by_name(self, name):
        with _registry_lock:
            return self._reg.get(name)

actor_registry = ActorRegistry()

