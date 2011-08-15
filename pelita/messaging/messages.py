# -*- coding: utf-8 -*-

"""
This module holds the basic messages which are allowed to be sent.

The messages are standardised. If there is a need for a subclass,
one should not inherit directly from `BaseMessage` but from one of the
pre-defined subclasses, depending on what is needed.

Message types are:

    Notification(method, params)
    Query(method, params, id)
    Response(result, id)
    Error(error, id)

A `Query` with a specific id awaits a `Response` with the same id. If no
`Response` can be given or something strange happened, an `Error` may be
returned.

The `Error` message may have an empty id in which case it is not thought as a
response to a specific query.

Each `Query` may only have one responding message.
"""

__docformat__ = "restructuredtext"


class BaseMessage(object):
    """A message can be converted to a simple dict object,
    which in turn may be represented by a JSON string when sent
    through a remote connection.
    """
    def __repr__(self):
        return self.__class__.__name__ + "(" + repr(self.dict) + ")"

    # TODO: is_response might be replaced by a check
    #   if (isinstance(msg, Response) or isinstance(msg, Error)) and \
    #       msg.id is not None
    @property
    def is_response(self):
        """This flag is set to true, if this message is of a response type."""
        raise NotImplementedError

    # TODO: wants_response might be replaced by a check
    #   if isinstance(msg, Query)
    @property
    def wants_response(self):
        """This flag is set to true, if this message awaits a response."""
        raise NotImplementedError

    @classmethod
    def load(cls, dict):
        """Load one of the pre-defined subclasses.
        """
        return _load_message(dict)

    @property
    def dict(self):
        raise NotImplementedError


class Query(BaseMessage):
    """A query is a special message which has a unique id. It asks the server for a response."""
    def __init__(self, method, params, id):
        self.method = method
        self.params = params
        self.id = id

    @property
    def is_response(self):
        return False

    @property
    def wants_response(self):
        return True

    @property
    def dict(self):
        return {"method": self.method, "params": self.params, "id": self.id}

class Notification(BaseMessage):
    def __init__(self, method, params):
        self.method = method
        self.params = params

    @property
    def is_response(self):
        return False

    @property
    def wants_response(self):
        return False

    @property
    def dict(self):
        return {"method": self.method, "params": self.params}

class Response(BaseMessage):
    def __init__(self, result, id):
        self.result = result
        self.id = id

    @property
    def is_response(self):
        return True

    @property
    def wants_response(self):
        return False

    @property
    def dict(self):
        return {"result": self.result, "id": self.id}

class Error(BaseMessage):
    def __init__(self, error, id):
        self.error = error
        self.id = id

    @property
    def is_response(self):
        # an Error message may or may not be a response, depending
        # on the value of id
        return self.id is not None

    @property
    def wants_response(self):
        return False

    @property
    def dict(self):
        return {"error": self.error, "id": self.id}


_defined_messages = [Query, Notification, Response, Error]

def _load_message(dict):
        for cls in _defined_messages:
            try:
                return cls(**dict)
            except TypeError:
                pass
        raise ValueError("Cannot convert object %r to Message." % dict)
