from actors.actor import Actor

class HelloWorldActor(Actor):
    def receive(self, msg):
        self.reply(msg + " World")


class Remote(object):
    pass

def remote_start(server, address, port):
    s = server(address, port)


remote_start(JsonThreadedListeningServer, "localhost", 9990).register_actor(HelloWorldActor)



