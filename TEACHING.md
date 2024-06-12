# Teaching Pelita – Caveats and best practices

Over the years, we found the following ideas to teaching to be valuable.

## Prepare the group repositories before the course

When your students are newcomers to git (and the command line) and project setups in Python, it is a good idea to have prepared a repository for all the groups that contains the recommended structure of the project and some demo players and tests.

The standard assumption is that the repositories look similar to:

    groupN/
      .git/
      README.md
      Makefile [*]
      team/
        __init__.py
        player.py
        ...
      test/
        test_player.py


The `team/` folder is therefore a Python module that can be used by `pelita` on the command line and which can be imported as `team` by `py.test` when it iterates through the `test/` folder.

One potential error source is that `pelita` does not care about the location of the `team/` folder relative to the current directory. Any path that ends on `team/` will do (so it won’t work from inside the module but from basically everywhere else). However, the tests will only import the `team` module when `py.test` is run from the `groupN` folder. Notably running `py.test groupN/test` won’t work (or worse: it will execute but fail with confusing `ImportError`s).

A solution would be to add the `groupN` folder to the `PYTHONPATH` variable but this only makes things worse, as usually not everyone in the group will know about it and then one has the situation that for some in the group the tests will work and for others they won’t (without them knowing why) and this is not a situation you want to have.

In Nikiti we therefore started experimenting with a `Makefile` for easier testing. The downside of this is that it introduces another potentially confusing concept (many will not even have heard of what a `Makefile` is) but since they do not have to edit the file, we can just assume it as some kind of black box. The only necessary purpose of the `Makefile` is to ensure that typing

    $ make test

exeutes

    PYTHONPATH=. py.test test/

with the side-effect that it only works inside the `groupN` directory and nowhere else.

It is possible to add more features to the `Makefile` like running a demo game

    $ make demo
    pelita team/ random

but this led to the situation in Nikiti that some groups would assume that they always play on the left side. A better `Makefile` might have both a

    $ make demoleft
    pelita team/ random

and a

    $ make demoright
    pelita random team/

and encourage groups to use both of them.

This of course comes without the flexibility of the `pelita` command line. In particular it is not possible to specify the number of rounds or select a layout for the demo. It should therefore be noted that the `make demo` commands are only there to ensure that the repo is in a state ready to run the tournament.

## Checklist for a three-day project

### After the first day

Check that everybody was able to work with the repositories and all the groups have done a few commits already and know how to run the tests and a demo game. Ensure that all groups are able to run tests before they go home on the first day.

Make a note how the groups split up their work and if all of the subgroups have been able to push and merge to the group repository. My anecdotal findings are that those subgroups who have been too reluctant to look into and deal with git merges on the first day are much more likely to have git problems throughout the final day. (To the point that some could not do any proper work besides fixing conflits.)

### Day 2

In the beginning of day 2, all groups who had (potential) git problems should already be looked after. Force all of the subgroups to merge, even if they are still unfinished or at least let the groups rebase on top of the progressed master branch. Do not let the individual branches diverge too much. It is better to have a tutor play the git magician now than when it is too late.

Later during day 2, it is possible to start setting up network players with hidden code, that can be played against.

A network player that binds port 33333 can be set up with the command

    $ pelita-player --remote path/to/module/ tcp://0.0.0.0:33333

and it can be played against with

    $ pelita my_team/ remote:tcp://192.168.1.99

(or whatever the IP address is).

Caveat: The `pelita-player --remote` command spawns a subprocess for each new connection with a local player. Currently, those subprocesses will not timeout but will only exit when the user’s `pelita` command tells them to. To avoid having hundrets of Python processes waiting on zmq messages, it may be a good idea to run the remote players inside a container.

### Day 3

During the final day, the person who is responsible for the tournament will regularly clone all group repositories and write the `.yaml` file that can run the tournament. All repositories should regularly be checked during the day and tested that a) they do not have import errors, b) they are able to run on both the left and the right side of the maze, c) they do not take overly long for each step.

All those errors should be reported back to the groups and tutors should help solve them.

Additionally, the groups may be offered the chance to play against each other with the network mode. Either centralised on the server that also runs the other hidden network players or self-organised by having groups meet and discuss their code directly with each other.

