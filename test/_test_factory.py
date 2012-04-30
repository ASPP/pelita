
""" framework to simplify test development for pelita players

This framework allows you to easily define different tests
for the behaviour of your bots.
It comes with the tools to create tests for the movement of your bots.
You can test two bots simultaniously and can specify the movements of
your enemies.
You can use the framework for other types of tests as well.
Just write a create_* function and pass it as second parameter
to tests_from_list.

Example
-------
>>> from _test_factory import TestMovementSettings, GeneratedTests
>>> from _test_factory import tests_from_list
>>> from pelita.datamodel import north, south, west, east, stop
>>> eat = TestMovementSettings(
...    "eat",
...    '''######
...       #0  .#
...       #    #
...       #.  1#
...       ######
...       #2  3#
...       ######''',
...    {0: (1,1), 3: (4,1)},
...    [south, north]
... )

>>> team_eat = TestMovementSettings(
...    name   = "team eat",
...    layout =
...    '''######
...       #0  .#
...       #    #
...       #2  .#
...       ######
...       #. 13#
...       ######''',
...    expect = ({0: (1,1), 3: (4,1)},
...              {0: (1,3), 2: (3,3)})
... )

>>> enemy_food = TestAttributeSettings(
...     "enemy food",
...     '''######
...        #0  .#
...        #.  1#
...        ######''',
...     "enemy_food",
...     [(4,1)]
... )

>>> tests = [eat, team_eat]
>>> tests_from_list(tests)
>>> tests_from_list([enemy_food],create_attribute_test)
>>> import unittest
>>> from pelita.player import BFSPlayer
>>> GeneratedTests.player = BFSPlayer
>>> #when using this in a file simply run unittest.main()
>>> suite = unittest.TestLoader().loadTestsFromTestCase(GeneratedTests)
>>> unittest.TextTestRunner(verbosity=2).run(suite)
<unittest.runner.TextTestResult run=3 errors=0 failures=0>

"""

import unittest
from pelita.game_master import GameMaster
from pelita.player import TestPlayer, StoppingPlayer, SimpleTeam
from pelita.datamodel import stop

class TestAttributeSettings(object):
    """ Container for the settings of a property test

    This object contains the settings form which a test
    will then be generated.

    Parameters
    ----------
    name : string
        name of the test
    layout : string
        initial map layout as string
        (as used by GameMaster)
        the map must contain 2 starting postions
        and at least one food pellet for each team
    attribute : string
        attribute that should be tested
    expect : *
        expected return value of the tested property

    """
    def __init__(self, name, layout, attribute, expect):
        self.name      = name
        self.layout    = layout
        self.attribute = attribute
        self.expect    = expect


class TestMovementSettings(object):
    """ Container for the settings of a movement test

    This object contains the settings form which a test
    will then be generated.

    Parameters
    ----------
    name : string
        name of the test
    layout : string
        initial map layout as string
        (as used by GameMaster)
        the map must contain 4 starting postions
    expect : (tuple of) dictionaries
        a dictionary with entries of the form "round : (x,y)"
        defining the possistions where the bot is expected
        in a given round.
        if a tuple with two dictionaries is given, bot 0 and 2 will
        be tested, otherwise bot 2 is a StoppingPlayer
    enemy_moves : (tuple of) lists
        lists containing the moves of the enemy bots
        as used by TestPlayer
        if a list is missing or the predefined moves run out
        the bot will "stop"
    second_team : boolean
        if true the we control bots 1 and 3

    Attributes
    ----------
    see Parameters
    use_bots : int
        number of bots that should be tested

    """
    def __init__(self, name, layout, expect,
                 enemy_moves = [stop], second_team = False ):
        self.name        = name
        self.layout      = layout
        # store expecte positions for our bots
        if type(expect) == tuple and len(expect) == 2:
            self.use_bots = 2
            self.expect    = expect
        else:
            self.use_bots = 1
            self.expect = expect, {}
        # store moves for enemy bots
        if type(enemy_moves) == tuple and len(enemy_moves) == 2:
            self.enemy_moves = enemy_moves
        else:
            self.enemy_moves = enemy_moves, []
        self.second_team = second_team

class GeneratedTests(unittest.TestCase):
    """ Container for genereated tests

    Object that will contain the generated tests
    and store general settings

    Attributes
    ----------
    silent : boolean
        if False, movements of tested bots will be printed
        use -v commandline option
    player : Player
        the player class that should used for the tested bots

    """
    silent = True
    player = None


def create_attribute_test(settings):
    """ create a test from given attribute settings

    Parameters
    ----------
    settings : TestAttributeSettings
        settings defining the test to be created

    Returns
    -------
    new_test : function
        the newly generated test

    """
    def new_test(self):
        """ test function based on settings """
        game = GameMaster(settings.layout, 2, 200, noise=False)
        player_0 = self.player()
        player_1 = StoppingPlayer()
        game.register_team(SimpleTeam(player_0))
        game.register_team(SimpleTeam(player_1))
        game.set_initial()

        self.assertEqual(settings.expect,
                         player_0.__getattribute__(settings.attribute))
    return new_test


def create_movement_test(settings):
    """ create a test from given movement settings

    Parameters
    ----------
    settings : TestMovementSettings
        settings defining the test to be created

    Returns
    -------
    new_test : function
        the newly generated test

    """
    def new_test(self):
        """ test function based on settings """
        if not self.silent:
            print " "
        game = GameMaster(settings.layout, 4, 200, noise=False, silent=True)
        team = [self.player()]
        if settings.use_bots == 2:
            team.append(self.player())
        else:
            team.append(StoppingPlayer())
        enemies = [TestPlayer(settings.enemy_moves[0]),
                   TestPlayer(settings.enemy_moves[1])]
        if not settings.second_team:
            game.register_team(SimpleTeam(team[0], team[1]))
            game.register_team(SimpleTeam(enemies[0], enemies[1]))
        else:
            game.register_team(SimpleTeam(enemies[0], enemies[1]))
            game.register_team(SimpleTeam(team[0], team[1]))
        test_steps = settings.expect[0].keys()
        test_steps += settings.expect[1].keys()
        game.set_initial()
        for i in range(0, max(test_steps)+1):
            for enemy in enemies:
                if len(enemy.moves) == 0:
                    enemy.moves.append(stop)
            game.play_round(i)
            for bot in range(0, settings.use_bots):

                target_pos = ""
                if settings.expect[bot].has_key(i):
                    target_pos = "should be "+str(settings.expect[bot][i])
                    self.assertEqual(settings.expect[bot][i],
                                     team[bot].current_pos)
                if not self.silent:
                    print " ", i, ": ", team[bot].current_pos, target_pos
    return new_test

def tests_from_list(test_settings, create_fun=create_movement_test):
    """ create tests and add them to container

    creates tests from list of settings and registers
    each test with the container.
    This is the function that should be called by the user.

    Parameters
    ----------
    test_settings : list
        list containing TestSettings objects
    create_fun : function
        the function which should be used to generate the test

    """
    for settings in test_settings:
        test = create_fun(settings)
        test.__name__ = "test_%s" % settings.name.replace(" ", "_")
        test.__doc__ = settings.name+" (GeneratedTests)"
        setattr(GeneratedTests, test.__name__, test)

