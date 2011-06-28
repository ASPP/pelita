import unittest
from pelita.messaging.utils import SuspendableThread, CloseThread

class NotImplementedThread(SuspendableThread):
    pass

class SimpleThread(SuspendableThread):
    def __init__(self):
        super(SimpleThread, self).__init__()
        self.number = 0

    def _run(self):
        if self.number < 10:
            self.number += 1
        else:
            self.stop()

class CloseableThread(SimpleThread):
    def __init__(self):
        super(CloseableThread, self).__init__()

    def _run(self):
        if self.number < 10:
            self.number += 1
            if self.number == 5:
                raise CloseThread
        else:
            self.stop()

class TestThreading(unittest.TestCase):
    def test_simple_thread(self):
        thread = SimpleThread()
        thread.start()
        thread.thread.join()
        self.assertEqual(thread.number, 10)
        self.assertEqual(thread._running, False)

    def test_suspendable_thread(self):
        thread = SimpleThread()
        thread.paused = True
        thread.start()
        self.assertEqual(thread.paused, True)

        self.assertEqual(thread.number, 0)
        thread.paused = False
        self.assertEqual(thread.paused, False)

        thread.thread.join()
        self.assertEqual(thread.number, 10)
        self.assertEqual(thread._running, False)

    def test_thread_raise(self):
        thread = CloseableThread()
        thread.start()
        thread.thread.join()
        self.assertEqual(thread.number, 5)
        self.assertEqual(thread._running, False)

if __name__ == '__main__':
    unittest.main()
