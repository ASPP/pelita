import unittest
from pelita.messaging import DispatchingActor, dispatch, ActorProxy

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

if __name__ == '__main__':
    unittest.main()
