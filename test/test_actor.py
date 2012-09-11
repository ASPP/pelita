import unittest
import time
import queue

from pelita.messaging import DispatchingActor, expose, Actor, actor_of, RemoteConnection, Exit, Request, ActorNotRunning
from functools import reduce

class Dispatcher(DispatchingActor):
    def __init__(self):
        super(Dispatcher, self).__init__()
        self.param1 = None

    @expose
    def dummy(self):
        pass

    @expose
    def set_param1(self, argument):
        self.param1 = argument

    @expose
    def get_param1(self):
        self.ref.reply(self.param1)

    @expose
    def complicated_params(self, arg1=1, arg2=2, arg3=3):
        self.ref.reply(arg1 + 10 * arg2 + 100 * arg3)

    @expose
    def get_docstring(self):
        """ This method has no content but a docstring. """

    @expose
    def return_message(self, *args, **kwargs):
        msg = self.ref.current_message
        self.ref.reply(msg)

    @expose(name="renamed_method")
    def fake_name(self):
        self.ref.reply(12)


class TestDispatchingActor(unittest.TestCase):
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

    def test_unhandled(self):
        actor = actor_of(Dispatcher)
        actor.start()

        res = actor.query("unhandled")
        self.assertEqual(type(res.get()), str)

        actor.stop()

    def test_docstring_request(self):
        actor = actor_of(Dispatcher)
        actor.start()

        res = actor.query("?get_docstring")
        self.assertEqual(res.get(), " This method has no content but a docstring. ")

        actor.stop()

    def test_renamed_dispatch(self):
        actor = actor_of(Dispatcher)
        actor.start()

        res = actor.query("renamed_method")
        self.assertEqual(res.get(), 12)

        res = actor.query("fake_name")
        self.assertTrue(res.get().startswith("Not found")) # TODO: proper error handling

        actor.stop()

    def test_invalid_dispatch(self):
        actor = actor_of(Dispatcher)
        actor.start()

        res = Request()
        actor.put("No dict", res)
        self.assertEqual(type(res.get()), str) # cant do better now

        res = actor.query(1)
        self.assertEqual(type(res.get()), str) # cant do better now

        actor.stop()

    def test_lifecycle(self):
        actor = actor_of(Dispatcher)
        self.assertRaises(ActorNotRunning, actor.notify, "dummy")
        actor.start()
        actor.notify("dummy")
        actor.stop()
        actor.join()
        self.assertRaises(ActorNotRunning, actor.notify, "dummy")

    def test_complicated_params(self):
        actor = actor_of(Dispatcher)
        actor.start()
        req = actor.query("complicated_params", {"arg1": 5, "arg3": 7}) # arg2 is default 2
        self.assertEqual(req.get(), 725)

        req = actor.query("complicated_params", [1,2,3])
        self.assertEqual(req.get(), 321)
        actor.stop()
        actor.join()

    def test_current_message(self):
        actor = actor_of(Dispatcher)
        actor.start()
        req = actor.query("return_message", {"arg1": 5, "arg3": 7})
        self.assertEqual(req.get(), {'params': {'arg1': 5, 'arg3': 7}, 'method': 'return_message'})

        actor.stop()
        actor.join()

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
        # sorry, this is quite ugly
        time.sleep(1)

        # collectingActor2 should have closed automatically
        self.assertEqual(collectingActor2.is_alive, False)

        # collectingActor3 should still be alive
        self.assertEqual(collectingActor3.is_alive, True)

        # collectingActor3 should have received an Exit
        self.assertEqual(collectingActor1._actor.received_exit, None)
        self.assertEqual(collectingActor2._actor.received_exit, None)
        self.assertNotEqual(collectingActor3._actor.received_exit, None)
        self.assertEqual(collectingActor4._actor.received_exit, None)

        # TODO: who should be the sender of the exit notice?
        # self.assertEqual(collectingActor3.received_exit.sender, collectingActor2)

        collectingActor3.stop()
        collectingActor4.stop()
        # wait for the messages to be sent
        collectingActor3.join(3)

        self.assertEqual(collectingActor3.is_alive, False)

    def test_no_real_actor(self):
        class NoActor(object): pass
        self.assertRaises(ValueError, actor_of, NoActor)

class MultiplyingActor(Actor):
    def on_receive(self, message):
        if message.get("method") == "mult":
            params = message.get("params")
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
        remote = RemoteConnection().start_listener("localhost", 0)
        remote.register("main-actor", actor_of(MultiplyingActor))

        remote.start_all()

        # port is dynamic
        port = remote.listener.socket.port

        client1 = RemoteConnection().actor_for("main-actor", "localhost", port)
        res = client1.query("mult", [1, 2, 3, 4])
        self.assertEqual(res.get(timeout=3), 24)

        # check, that I can use another client
        client2 = RemoteConnection().actor_for("main-actor", "localhost", port)
        res = client2.query("mult", [4, 4, 4])
        self.assertEqual(res.get(timeout=3), 64)

        # check, that the first still works
        res = client1.query("mult", [2, 2, 4])
        self.assertEqual(res.get(timeout=3), 16)

        remote.stop()

    def test_bad_actors(self):
        remote = RemoteConnection().start_listener("localhost", 0)
        remote.register("main-actor", actor_of(MultiplyingActor))

        remote.start_all()

        # port is dynamic
        port = remote.listener.socket.port

        # check a remote identifier which does not work
        # should reply with an error message
        client = RemoteConnection().actor_for("unknown-actor", "localhost", port)
        req = client.query("mult", [1, 4, 4])
        res = req.get(timeout=3)
        self.assertTrue("error" in res)

        remote.stop()

    def test_not_running(self):
        remote = RemoteConnection().start_listener("localhost", 0)
        remote.register("main-actor", actor_of(MultiplyingActor))

        # port is dynamic
        port = remote.listener.socket.port

        client = RemoteConnection().actor_for("main-actor", "localhost", port)
        req = client.query("mult", [1, 4, 4])
        res = req.get(timeout=3)
        self.assertTrue("error" in res)

        remote.stop()

    def test_bad_json(self):
        remote = RemoteConnection().start_listener("localhost", 0)
        remote.register("main-actor", actor_of(MultiplyingActor))

        # port is dynamic
        port = remote.listener.socket.port

        client = RemoteConnection().actor_for("main-actor", "localhost", port)

        # unserialisable class
        class SomeClass(object):
            pass
        somobj = SomeClass()

        self.assertRaises(TypeError, client.query, "mult", somobj)

        remote.stop()

    def test_connection(self):
        remote = RemoteConnection().start_listener("localhost", 0)
        remote_actor = actor_of(MultiplyingActor)
        remote.register("main-actor", remote_actor)
        remote.start_all()

        # port is dynamic
        port = remote.listener.socket.port

        client = RemoteConnection().actor_for("main-actor", "localhost", port)

        self.assertTrue(remote_actor.is_alive)
        self.assertTrue(client.is_connected())
        self.assertTrue(remote_actor.is_alive)

        remote_actor.stop()
        remote_actor.join()

        # we are still connected
        self.assertTrue(client.is_connected())

        remote.stop()
        # need to wait a little until the connection shuts down, sorry
        for i in range(50):
            still_connected = client.is_connected()
            if still_connected:
                time.sleep(0.1)
            else:
                return

        self.assertFalse(still_connected)

if __name__ == '__main__':
    unittest.main()
