import unittest
import time
from pelita.messaging import DispatchingActor, dispatch, ActorProxy, Actor
from pelita.messaging.actor import Exit

class Dispatcher(DispatchingActor):
    def __init__(self):
        super(Dispatcher, self).__init__()
        self.param1 = None

    @dispatch
    def set_param1(self, message, argument):
        self.param1 = argument

    @dispatch
    def get_param1(self, message):
        message.reply(self.param1)


class TestActor(unittest.TestCase):
    def test_running(self):
        actor = Dispatcher()
        actor.start()

        self.assertEqual(actor._running, True)

        actor.stop()
        actor.thread.join(3)
        self.assertEqual(actor._running, False)

    def test_messages(self):
        actor = Dispatcher()
        actor.start()

        remote = ActorProxy(actor)
        remote.notify("set_param1", [12])

        request = remote.query("get_param1")
        response = request.get()

        self.assertEqual(response.result, 12)
        actor.stop()

class RaisingActor(Actor):
    def receive(self, message):
        raise NotImplementedError

class CollectingActor(Actor):
    def __init__(self):
        super(CollectingActor, self).__init__()
        self.received_exit = None

    def receive(self, message):
        if isinstance(message, Exit):
            self.received_exit = message


class TestActorFailure(unittest.TestCase):
    def test_raise_no_trap_exit(self):
        collectingActor1 = CollectingActor()
        collectingActor1.trap_exit = False
        collectingActor1.start()

        collectingActor2 = CollectingActor()
        collectingActor2.trap_exit = False
        collectingActor2.start()

        collectingActor3 = CollectingActor()
        collectingActor3.trap_exit = True
        collectingActor3.start()

        collectingActor4 = CollectingActor()
        collectingActor4.trap_exit = True
        collectingActor4.start()

        raisingActor = RaisingActor()
        raisingActor.link(collectingActor1)
        collectingActor1.link(collectingActor2)
        collectingActor2.link(collectingActor3)
        collectingActor3.link(collectingActor4)

        raisingActor.start()
        raisingActor.put("Msg")

        # wait for the messages to be sent
        time.sleep(1)

        # collectingActor2 should have closed automatically
        self.assertEqual(collectingActor2.thread.is_alive(), False)

        # collectingActor3 should still be alive
        self.assertEqual(collectingActor3.thread.is_alive(), True)

        # collectingActor3 should have received an Exit
        self.assertEqual(collectingActor1.received_exit, None)
        self.assertEqual(collectingActor2.received_exit, None)
        self.assertNotEqual(collectingActor3.received_exit, None)
        self.assertEqual(collectingActor4.received_exit, None)

        # TODO: who should be the sender of the exit notice?
        # self.assertEqual(collectingActor3.received_exit.sender, collectingActor2)

        collectingActor3.stop()
        collectingActor4.stop()
        # wait for the messages to be sent
        collectingActor3.thread.join(3)

        self.assertEqual(collectingActor3.thread.is_alive(), False)


if __name__ == '__main__':
    unittest.main()
