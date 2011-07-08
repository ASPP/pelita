# -*- coding: utf-8 -*-

import Queue
import weakref
import logging

from pelita.messaging.utils import SuspendableThread, Counter, CloseThread
from pelita.messaging import Query, Notification, BaseMessage

_logger = logging.getLogger("pelita.actor")
_logger.setLevel(logging.DEBUG)

class Request(object):
    # TODO: Need to make messages immutable to avoid synchronisation errors
    # eg. pykka uses a deepcopy to add things to the queue…
    def __init__(self, id):
        self.id = id
        self._queue = Queue.Queue(maxsize=1)

    def get(self, block=True, timeout=None):
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

class BaseActor(SuspendableThread):
    """ BaseActor is an actor with no pre-defined queue.
    """
    def __init__(self, **kwargs):
        super(BaseActor, self).__init__(**kwargs)

        self.ref = None

        self.trap_exit = False
        self.linked_actors = []

    def _run(self):
        try:
            message = self.handle_inbox()
        except Queue.Empty:
            return

        if isinstance(message, BaseMessage) and message.is_response:
            self.handle_response(message)
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
            self.on_receive(message)
        except Exception as e:
            exit_msg = Exit(self, e)
            self.exit_linked(exit_msg)
            raise

    def exit_linked(self, exit_msg):
        while self.linked_actors:
            linked = self.linked_actors[0]
            self.unlink(linked)
            linked.put(exit_msg)

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
        if not other in self.linked_actors:
            self.linked_actors.append(other)

    def unlink_from(self, other):
        while other in self.linked_actors:
            self.linked_actors.remove(other)

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

    def handle_response(self, message):
        # check if there is a waiting request in the ref’s database
        awaiting_result = self.ref.request_db.get_request(message.id, None)
        if awaiting_result is not None:
            awaiting_result._queue.put(message)
            # TODO need to handle race conditions

            return # finish handling of messages here

        else:
            _logger.warning("Received a response (%r) without a waiting future. Dropped response.", message.dict)
            return

class Actor(BaseActor):
    # TODO Handle messages not replied to – else the queue is waiting forever
    def __init__(self, inbox=None):
        super(Actor, self).__init__()

        self._inbox = inbox or Queue.Queue()

    def handle_inbox(self):
        return self._inbox.get(True, 3)

    def forward(self, message):
        self._inbox.put(message)

    def put(self, message):
        self._inbox.put(message)

class ForwardingActor(object):
    """ This is a mix-in which simply forwards all messages to another actor.

    When using it, the variable `self.forward_to` needs to be set.
    """
    def on_receive(self, message):
        self.forward_to.put(message)

    def on_stop(self):
        self.forward_to.put(StopProcessing)

class ActorProxy(object):
    def __init__(self, actor):
        """ Helper class to send messages to an actor.
        """
        self.actor = actor

        self.request_db = RequestDB()

    def start(self):
        self.actor.start()

    def stop(self):
        self.notify("stop")

    def notify(self, method, params=None):
        message = Notification(method, params)
        self.actor.put(message)

    def query(self, method, params=None, id=None):
        # Update the query.id
        if not id:
            id = self.request_db.create_id(id)

        query = Query(method, params, id)
        req_obj = Request(query.id)

        # save the id to the _requests dict
        self.request_db.add_request(req_obj)
        query.mailbox = self.actor
        self.actor.put(query)

        return req_obj


class RemoteActorProxy(object):
    def __init__(self, actor):
        """ Helper class to send messages to an actor.
        """
        self.actor = actor

    def notify(self, method, params=None):
        message = Notification(method, params)
        self.actor.put_remote(message)

    def query(self, method, params=None, id=None):
        query = Query(method, params, id)
        return self.actor.put_query_remote(query)

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

    def __init__(self, inbox=None):
        super(DispatchingActor, self).__init__(inbox)

        self._init_dispatch_db()

    def _init_dispatch_db(self):
        self._dispatch_db = {}
        # search all attributes of this class
        for member_name in dir(self):
            member = getattr(self, member_name)
            if getattr(member, "__dispatch", False):
                name = getattr(member, "__dispatch_as", None)
                if not name:
                    name = member_name
                if name in self._dispatch_db:
                    raise ValueError("Dispatcher name '%r' defined twice", name)
                self._dispatch_db[name] = member_name

    def _dispatch(self, message):
        method = message.method
        params = message.params

        def reply_error(msg):
            try:
                message.reply_error(msg)
            except AttributeError:
                pass

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
            if hasattr(message, "reply"):
                res = meth.__doc__
                message.reply(res)
            return

        try:
            if params is None:
                res = meth(message)

            elif isinstance(params, dict):
                res = meth(message, **params)

            else:
                res = meth(message, *params)
        except TypeError, e:
            reply_error("Type Error: method '%r'\n%r" % (message.method, e))
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
            try:
                message.reply_error(msg)
            except AttributeError:
                pass
        reply_error("Not found: method '%r'" % message.method)
