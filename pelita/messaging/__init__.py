# -*- coding: utf-8 -*-

__docformat__ = "restructuredtext"

"""Pelita messaging framework.

Description
-----------

The messaging framework in pelita serves two main purposes:
 1) Easier handling of threaded objects without the need for explicit locks
 2) Establishing a means of communication between remote processes

One of the primary design goals of pelita was to split server and client
code in a way that no client could exploit the program state by examining
the stack trace.

A simple way to sandbox the client code was to separate the processes
and exchange information only via network sockets. This has been done
for pelita as well. As an exchange and serialisation format, we use
JSON strings which represent simple python objects.

Since networking code very often needs to wait on I/O input and output,
this code should be written using separate threads. The actor paradigm
then ensures that different threads may easily exchange information
between them without the dangers of explicit locking and thread ownership
confusion.

Usage
-----
A plain actor is defined by subclassing `Actor`::

    class MyActor(Actor):
        def on_receive(self, message):
            print "I received the message '%s'" % message

In order to instantiate and use it, we have to create an `ActorReference`
which is done using the `actor_of` method. (Note that neither `Actor` nor
`ActorReference` should not be instantiated manually.)

::

    my_actor = actor_of(MyActor) # we pass the class as a parameter

We may then start our actor and send it a message::

    my_actor.start()
    my_actor.notify("Hello")

    # prints
    # "I received the message '{method: "Hello"}'"

If we are finished, we need to stop the actor::

    my_actor.stop()

If we do not stop the actor, the thread will still be running in the
background, which means that out program will not be able to exit.

Because overriding the `on_receive` method and checking for every incoming
method is tedious, there is an alternative `DispatchingActor` which
automatically transforms incoming messages into method calls on the actor’s
instance::

    class MyOtherActor(DispatchingActor):
        @expose
        def hello(self, what):
            print "Hello, " + what

    my_other_actor = actor_of(MyOtherActor)
    my_other_actor.start()
    my_other_actor.notify("hello", ["World!"])
    # prints "Hello, World!"
    my_other_actor.stop()

It is also possible to request information from an actor. This can be done
using the `query` statement::

    class MyOtherActor(DispatchingActor):
        @expose
        def hello(self, what):
            self.ref.reply("Hello, " + what)

    my_other_actor = actor_of(MyOtherActor)
    my_other_actor.start()
    res = my_other_actor.query("hello", ["World!"])
    # wait at most three seconds and print the result
    print res.get(3)
    # prints "Hello, World!"
    my_other_actor.stop()

With `res`, a `Request` type was being returned from `query`. A `Request`
acts as a placeholder for a future result.
It is a special type of a channel, which may receive a message. The channel
can be passed to the `Actor` which may use `self.ref.reply` to send a message
to it.

In the case of a `Request`, we can ask our main thread to wait until the result
is there using `res.get()`. We may also add a timeout (and we should always
use one) by saying `res.get(3)`.

Remote actors
-------------

Remote actors use a socket connection in the background and will act on all
messages which are addressed to them. In general, addressing an actor is done
by specifying its remote connection and its unique identifier.

However, since unique identifiers are impractical to use for the very first
connection (the client code must know how to reach the main server actor
without any further input), a remote actor may also expose a public name
by which it can be reached::

    # starts an actor listening on localhost:50007
    remote = RemoteConnection().start_listener("localhost", 50007)
    remote.register("main-actor", actor_of(MyOtherActor))
    remote.start_all()

Client code can now easily access this actor::

    client = RemoteConnection().actor_for("main-actor", "localhost", 50007)
    res = client.query("hello", ["World!"])
    print res.get(3)

Finally, the remote connection must be closed (which also stops all remote
actors)::

    remote.stop()

Acknowledgements
----------------

The framework draws its inspiration from other actor frameworks such as
 - The Scala actor library (http://www.scala-lang.org/)
 - The Akka Project (http://akka.io/)

It also shares similarities with
 - pykka (http://jodal.github.com/pykka/)

"""


from .messages import Query, Notification, Response, Error, BaseMessage
from .actor import (Actor, BaseActorReference, ActorReference, DispatchingActor,
                    expose, DeadConnection, StopProcessing, Request,
                    actor_of, actor_registry, Exit, ActorNotRunning)
from .remote_actor import RemoteActorReference, RemoteConnection
