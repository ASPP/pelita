import unittest
import time
from pelita.messaging import DispatchingActor, dispatch, ActorProxy, Actor

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

class TestActorFailure(unittest.TestCase):
    def test_raise(self):

        class RaisingActor(Actor):
            def receive(self, message):
                raise NotImplementedError

        class CollectingActor1(Actor):
            def receive(self, message):
                pass

        class CollectingActor2(Actor):
            def receive(self, message):
                pass

        collectingActor1 = CollectingActor1()
        collectingActor1.start()

        collectingActor2 = CollectingActor2()
        collectingActor2.start()

        raisingActor = RaisingActor()
        raisingActor.link(collectingActor1)
        collectingActor1.link(collectingActor2)

        raisingActor.start()
        raisingActor.put("Msg")

        # wait for the messages to be sent
        time.sleep(1)

        # collectingActor2 should have closed automatically
        self.assertEqual(collectingActor2.thread.is_alive(), False)



if __name__ == '__main__':
    unittest.main()
