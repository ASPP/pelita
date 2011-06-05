# -*- coding: utf-8 -*-

class Query(object):
    """A query is a special message which has a unique id. It asks the server for a response."""
    def __init__(self, method, params, id):
        self.method = method
        self.params = params
        self.id = id

    def response(self, result):
        return Response(result, self.id)

    def reply(self, result):
        return self.mailbox.put(self.response(result))

    def error_msg(self, error):
        return Error(error, self.id)

    def reply_error(self, error):
        return self.mailbox.put(self.error_msg(error))

    @property
    def rpc(self):
        return {"method": self.method, "params": self.params, "id": self.id}

class Message(object):
    def __init__(self, method, params):
        self.method = method
        self.params = params

    @property
    def rpc(self):
        return {"method": self.method, "params": self.params}

class Response(object):
    def __init__(self, result, id):
        self.result = result
        self.id = id

    @property
    def rpc(self):
        return {"result": self.result, "id": self.id}

class Error(object):
    def __init__(self, error, id):
        self.error = error
        self.id = id

    @property
    def rpc(self):
        return {"error": self.error, "id": self.id}


rpc_instances = [Query, Message, Response, Error]

def get_rpc(json):
    for cls in rpc_instances:
        try:
            return cls(**json)
        except TypeError:
            pass
    raise ValueError("Cannot convert JSON {0} to RPC object.".format(json))

