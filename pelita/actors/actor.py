import Queue
import threading

import logging

log = logging.getLogger("jsonSocket")
log.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

class DeadConnection(RuntimeError):
    pass


killable_threads = []

def killable(cls):
    _n = cls.__init__
    def __new__(*args, **kwargs):
        obj = _n(*args, **kwargs)
        killable_threads.append(obj)
        return obj
    cls.__new__ = __new__
    return cls


#class Actor():
#    pass
#Actor = killable(Actor)

##



@killable
class Actor(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.queue = Queue.Queue()
        self._running = False

        self._unpaused = threading.Event()
        self._unpaused.set()

    def send(self, msg):
        print "Send", msg
        self.queue.put( ("", msg) )

    def receive(self, remote, data):
        raise NotImplementedError

    def dispatcher(self):
        pass

    def suspend(self):
        self._unpaused.clear()

    def resume(self):
        self._unpaused.set()

    def stop(self):
        print "Stopped"
        self._running = False

    def start(self):
        print "Start"
        self._running = True
        threading.Thread.start(self)

    def run(self):
        count = 0
        while self._running:
            # wait, if _unpaused is cleared
            print self._unpaused.is_set(), self._running

            self._unpaused.wait()

            try:
                msg = self.queue.get(True, 3)
                print "Running", msg
                self.receive(*msg)
            except Queue.Empty:
                print "E"
                pass

import time

if __name__ == "__main__":
    a = Actor()
    
    a.suspend()
    a.start()
    print "Q"
    a.resume()


    threads = killable_threads
    print threads

    while len(threads) > 0:
        try:
            # Join all threads using a timeout so it doesn't block
            # Filter out threads which have been joined or are None
            threads = [t for t in threads if t is not None and t.is_alive()]
            [t.join(2) for t in threads]
            #time.sleep(100)
        except KeyboardInterrupt:
            print "Ctrl-c received! Sending kill to threads..."
            for t in threads:
                t.stop()
    



