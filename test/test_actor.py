import unittest
import time
from pelita.messaging import DispatchingActor, dispatch, ActorProxy, Actor, actor_of
from pelita.messaging.actor import Exit
from pelita.messaging.mailbox import Remote

class Dispatcher(DispatchingActor):
    def __init__(self):
        super(Dispatcher, self).__init__()
        self.param1 = None

    @dispatch
    def set_param1(self, message, argument):
        self.param1 = argument

    @dispatch
    def get_param1(self, message):
        self.ref.reply(self.param1)


class TestActor(unittest.TestCase):
    def test_running(self):
        actor = actor_of(Dispatcher)
        actor.start()

        self.assertEqual(actor.is_running, True)

        actor.stop()
        actor.join(3)
        self.assertEqual(actor.is_running, False)

    def test_messages(self):
        actor = actor_of(Dispatcher)
        actor.start()

        actor.notify("set_param1", [12])

        request = actor.query("get_param1")
        response = request.get()

        self.assertEqual(response, 12)
        actor.stop()

class RaisingActor(Actor):
    def on_receive(self, message):
        raise NotImplementedError

class CollectingActor(Actor):
    def __init__(self):
        super(CollectingActor, self).__init__()
        self.received_exit = None

    def on_receive(self, message):
        if isinstance(message, Exit):
            self.received_exit = message


class TestActorFailure(unittest.TestCase):
    def test_raise_no_trap_exit(self):
        collectingActor1 = actor_of(CollectingActor)
        collectingActor1.trap_exit = False
        collectingActor1.start()

        collectingActor2 = actor_of(CollectingActor)
        collectingActor2.trap_exit = False
        collectingActor2.start()

        collectingActor3 = actor_of(CollectingActor)
        collectingActor3.trap_exit = True
        collectingActor3.start()

        collectingActor4 = actor_of(CollectingActor)
        collectingActor4.trap_exit = True
        collectingActor4.start()

        raisingActor = actor_of(RaisingActor)
        raisingActor.link(collectingActor1)
        collectingActor1.link(collectingActor2)
        collectingActor2.link(collectingActor3)
        collectingActor3.link(collectingActor4)

        raisingActor.start()
        raisingActor.notify("Msg")

        # wait for the messages to be sent
        time.sleep(1)

        # collectingActor2 should have closed automatically
        self.assertEqual(collectingActor2.is_alive, False)

        # collectingActor3 should still be alive
        self.assertEqual(collectingActor3.is_alive, True)

        # collectingActor3 should have received an Exit
        self.assertEqual(collectingActor1.actor.received_exit, None)
        self.assertEqual(collectingActor2.actor.received_exit, None)
        self.assertNotEqual(collectingActor3.actor.received_exit, None)
        self.assertEqual(collectingActor4.actor.received_exit, None)

        # TODO: who should be the sender of the exit notice?
        # self.assertEqual(collectingActor3.received_exit.sender, collectingActor2)

        collectingActor3.stop()
        collectingActor4.stop()
        # wait for the messages to be sent
        collectingActor3.join(3)

        self.assertEqual(collectingActor3.is_alive, False)

class MultiplyingActor(Actor):
    def on_receive(self, message):
        if message.method == "mult":
            params = message.params
            res = reduce(lambda x,y: x*y, params)
            self.ref.reply(res)


class TestActorReply(unittest.TestCase):
    def test_simply_reply(self):
        actor_ref = actor_of(MultiplyingActor)
        actor_ref.start()

        res = actor_ref.query("mult", [1, 2, 3, 4])
        self.assertEqual(res.get(timeout=3), 24)
        actor_ref.stop()
        #assert False

class TestRemoteActor(unittest.TestCase):
    def test_remote(self):
        remote = Remote().start_listener("localhost", 0)
        remote.register("main-actor", actor_of(MultiplyingActor))
        remote.start_all()

        port = remote.listener.socket.port

        client1 = Remote().actor_for("main-actor", "localhost", port)
        res = client1.query("mult", [1, 2, 3, 4])
        self.assertEqual(res.get(timeout=3).result, 24)


if __name__ == '__main__':
    unittest.main()
