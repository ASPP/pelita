# -*- coding: utf-8 -*-

import Queue
import weakref

import logging
from pelita.utils import SuspendableThread, Counter, CloseThread
from pelita.actors import Query, Message, Response, Error


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

class AbstractActor(object):
    def request(self, method, params=None, id=None):
        raise NotImplementedError

    def request_timeout(self, method, params=None, id=None, timeout=None):
        return self.request(method, params, id).get(True, timeout)

    def send(self, method, params=None):
        raise NotImplementedError

class RemoteActor(AbstractActor):
    def __init__(self, mailbox):
        self.mailbox = mailbox

    def request(self, method, params, id=None):
        """Requests an answer and returns a Request object."""
        query = Query(method, params, id)

        # send as json
        return self.mailbox.request(query)

    def send(self, method, params=None):
        message = Message(method, params)
        self.mailbox.put(message)

class Actor(SuspendableThread):
    # TODO Handle messages not replied to – else the queue is waiting forever
    def __init__(self, inbox=None):
        SuspendableThread.__init__(self)
        self._inbox = inbox or Queue.Queue()

        self._requests = weakref.WeakValueDictionary()
        self._counter = Counter(0)

    def _run(self):
        try:
            message = self._inbox.get(True, 3)
        except Queue.Empty:
            return

        if isinstance(message, Response) or \
                (isinstance(message, Error) and message.id is not None):

            awaiting_result = self._requests.get(message.id, None)
            if awaiting_result is not None:
                awaiting_result._queue.put(message)
                # TODO need to handle race conditions

                return # finish handling of messages here

            else:
                _logger.warning("Received a response (%s) without a waiting future. Dropped response.", message.rpc)
                return

        if message is StopProcessing:
            raise CloseThread()

        # default
        self.receive(message)


    def request(self, method, params=None, id=None):
        """Requests an answer and returns a Request object."""
        query = Query(method, params, id)

        # send as json
        return self._request(query)

    def _request(self, message):
        """Put a query into the outbox and return the Request object."""
        if isinstance(message, Query):
            # save the id to the _requests dict
            if message.id is None:
                message.id = self._counter.inc()
            else:
                _logger.info("Using existing id.")

            req_obj = Request(message.id)
            self._requests[message.id] = req_obj

            message.mailbox = self

            self.put(message)
            return req_obj
        else:
            raise ValueError

    def receive(self, message):
        _logger.debug("Received message %s.", message)

    def send(self, method, params=None):
        message = Message(method, params)
        self.put(message)

    def put(self, message):
        self._inbox.put(message)

def dispatch(method=None, name=None):
    if name and not method:
        return lambda fun: dispatch(fun, name)
    method.__dispatch = True
    method.__dispatch_as = name
    return method

class DispatchingActor(Actor):
    """The DispatchingActor allows methods of the form

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
    def __init__(self, inbox=None):
        super(DispatchingActor, self).__init__(inbox)

        self._dispatch_db = {}
        self._init_dispatch_db()
        print self._dispatch_db

    def _init_dispatch_db(self):
        for member_name in dir(self):
            member = getattr(self, member_name)
            if getattr(member, "__dispatch", False):
                print member_name
                name = getattr(member, "__dispatch_as", None)
                if not name:
                    name = member_name
                self._dispatch_db[name] = member_name

    def _dispatch(self, message):

        # call method directly on actor (unsafe)
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
            reply_error("Not found: method '{0}'".format(message.method))
            return

        meth = getattr(self, method_name, None)
        if not meth:
            reply_error("Not found: method '{0}'".format(message.method))
            return

        if wants_doc:
            if hasattr(message, "reply"):
                res = meth.__doc__
                message.reply(res)
            return

        if params is None:
            params = []

        try:
            res = meth(message, *params)
        except TypeError:
            reply_error("Type Error: method '{0}'".format(message.method))
            return

        if hasattr(message, "reply"):
            message.reply(res)

    def receive(self, message):
        super(DispatchingActor, self).receive(message)
        self._dispatch(message)




class ProxyActor(object):
    def __init__(self, actor):
        self._actor = actor

    def query(self, remote, method, params):
        self._actor.request(remote, Query(method, params, None))



