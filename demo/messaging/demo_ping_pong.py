from pelita.messaging import DispatchingActor, dispatch, actor_of
from pelita.messaging.mailbox import Remote

class Ping(DispatchingActor):
    def on_start(self):
        self.pong = None
        self.pings_left = 1000

    @dispatch
    def connect(self, message, actor_uuid):
        self.pong = self.ref.remote.create_proxy(actor_uuid)

    @dispatch
    def Start(self, message):
        print "Ping: Starting"
        self.pong.notify("Ping", channel=self.ref)
        self.pings_left -= 1

    @dispatch
    def SendPing(self, message):
        self.pong.notify("Ping", channel=self.ref)
        self.pings_left -= 1

    @dispatch
    def Pong(self, message):
        if (self.pings_left % 100 == 0):
            print "Ping: pong from: " + str(self.ref.channel)
        if (self.pings_left > 0):
            self.ref.notify("SendPing")
        else:
            print "Ping: Stop."
            self.pong.notify("Stop", channel=self.ref)
            raise StopProcessing

class Pong(DispatchingActor):
    def on_start(self):
        self.pong_count = 0

    @dispatch
    def Ping(self, message):
        if (self.pong_count % 100 == 0):
            print "Pong: ping " + str(self.pong_count) + " from " + str(self.ref.channel)

        self.ref.channel.notify("Pong", channel=self.ref)
        self.pong_count += 1

    @dispatch
    def Stop(self, message):
        print "Pong: Stop."
        raise StopProcessing


remote = Remote().start_listener("localhost", 0)
remote.register("ping", actor_of(Ping))
remote.start_all()

port = remote.listener.socket.port

remote_ping = Remote().actor_for("ping", "localhost", port)
pong = actor_of(Pong)
pong.start()

print pong.uuid

remote_ping.notify("connect", [pong.uuid])
remote_ping.notify("Start")

pong.join()

remote.stop()
pong.stop()


