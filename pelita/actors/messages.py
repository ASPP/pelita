

class Query(object):
    def __init__(self, method, params, id):
        self.method = method
        self.params = params
        self.id = id

    def reply(self, result):
        return Response(result, self.id)

    def error(self, error):
        return Error(error, self.id)

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

