import pytest
import unittest

from pelita.exceptions import NoFoodWarning
from pelita.game import setup_game, run_game, play_turn
from pelita.layout import parse_layout
from pelita.player import stopping_player, stepping_player


class TestGameMaster:
    def test_team_names(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)

        def team_pattern(fn):
            # The pattern for a local team.
            return f'local-team ({fn})'

        def team_1(bot, state):
            assert bot.team_name == team_pattern('team_1')
            assert bot.other.team_name == team_pattern('team_1')
            assert bot.enemy[0].team_name == team_pattern('team_2')
            assert bot.enemy[1].team_name == team_pattern('team_2')
            return bot.position, state

        def team_2(bot, state):
            assert bot.team_name == team_pattern('team_2')
            assert bot.other.team_name == team_pattern('team_2')
            assert bot.enemy[0].team_name == team_pattern('team_1')
            assert bot.enemy[1].team_name == team_pattern('team_1')
            return bot.position, state

        state = setup_game([team_1, team_2], layout_dict=parse_layout(test_layout), max_rounds=3)
        assert state['team_names'] == [team_pattern('team_1'), team_pattern('team_2')]

        state = play_turn(state)
        # check that player did not fail
        assert state['fatal_errors'] == [[], []]

        state = play_turn(state)
        # check that player did not fail
        assert state['fatal_errors'] == [[], []]

    def test_too_few_registered_teams(self):
        test_layout_4 = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
        team_1 = stopping_player
        with pytest.raises(ValueError):
            setup_game([team_1], layout_dict=parse_layout(test_layout_4), max_rounds=300)

    def test_too_many_registered_teams(self):
        test_layout_4 = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
        team_1 = stopping_player
        with pytest.raises(ValueError):
            setup_game([team_1] * 3, layout_dict=parse_layout(test_layout_4), max_rounds=300)


    @pytest.mark.parametrize('bots', [
        ([(1, 1), (4, 2), (1, 2), (4, 1)], True), # n=4: good layout
        ([(1, 1), (1, 1), (1, 1), (1, 1)], True), # n=4, all on same spot: good layout
        ([(0, 1), (4, 2), (1, 2), (4, 1)], False), # n=4, bot on wall: bad layout
        ([(1, 1), None, (1, 2), (4, 1)], False),# n=4, empty: bad layout
        ([(1, 1), None, (1, 2)], False),# n=3, empty: bad layout
        ([(1, 1), (1, 2)], False),# n=2, empty: bad layout
        ([(-1, 1), (4, 2), (1, 2), (4, 1)], False), # n=4, illegal value: bad layout
        ([], False), # n=0, illegal value: bad layout
        ([(1, 1)], False),# n=3, empty: bad layout
        ([(1, 1), (4, 2), (1, 2), (4, 1), None], False), # n=5, illegal value: bad layout
        ([(1, 1), (4, 2), (1, 2), (4, 1), (1, 3)], False) # n=5, illegal value: bad layout
        ])
    def test_setup_game_with_different_number_of_bots(self, bots):
        layout = """
        ######
        #  . #
        # .# #
        ######
        """
        bot_pos, should_succeed = bots
        parsed = parse_layout(layout)
        parsed['bots'] = bot_pos

        if should_succeed:
            state = setup_game([stopping_player] * 2, layout_dict=parsed, max_rounds=5)
            assert state['bots'] == bot_pos
            state = run_game([stopping_player] * 2, layout_dict=parsed, max_rounds=5)
            assert state['fatal_errors'] == [[], []]
            assert state['errors'] == [{}, {}]
        else:
            with pytest.raises(ValueError):
                setup_game([stopping_player] * 2, layout_dict=parsed, max_rounds=300)

    @pytest.mark.parametrize('layout', [
        """
        ######
        #0 . #
        # . 1#
        ######
        """,
        """
        ######
        #0  .#
        #.3 1#
        ######
        """])
    def test_setup_game_with_too_few_bots_in_layout(self, layout):
        with pytest.raises(ValueError):
            parsed = parse_layout(layout)
            setup_game([stopping_player] * 2, layout_dict=parsed, max_rounds=300)

    @pytest.mark.parametrize('layout', [
        """
        ######
        #0 .3#
        #4. 1#
        ######
        """,
        """
        ######
        #0 6.#
        #.3 1#
        ######
        """])
    def test_setup_game_with_wrong_bots_in_layout(self, layout):
        with pytest.raises(ValueError):
            parsed = parse_layout(layout) # fails here
            setup_game([stopping_player] * 2, layout_dict=parsed, max_rounds=300)

    @pytest.mark.parametrize('layout', [
        """
        ######
        #0 3 #
        # 2 1#
        ######
        """,
        """
        ######
        #0 3.#
        # 2 1#
        ######
        """])
    def test_no_food(self, layout):
        with pytest.warns(NoFoodWarning):
            parsed = parse_layout(layout)
            setup_game([stopping_player] * 2, layout_dict=parsed, max_rounds=300)


@pytest.mark.xfail(reason="WIP")
class TestGame:

    def test_malicous_player(self):

        class MaliciousPlayer(AbstractPlayer):
            def _get_move(self, universe, game_state):
                universe = CTFUniverse._from_json_dict(gm.game_state)
                universe.teams[0].score = 100
                universe.bots[0].current_pos = (2,2)
                universe.maze[0,0] = False
                game_state.update(universe._to_json_dict())
                return {"move": (0,0)}

            def get_move(self):
                pass

        test_layout = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)

        original_universe = None
        class TestMaliciousPlayer(AbstractPlayer):
            def get_move(self):
                assert original_universe is not None
                print(id(original_universe.maze))
                print(id(universe.maze))
                # universe should have been altered because the
                # Player is really malicious
                assert original_universe != universe
                return (0,0)

        teams = [
            SimpleTeam(MaliciousPlayer()),
            SimpleTeam(TestMaliciousPlayer())
        ]
        gm = GameMaster(test_layout, teams, 2, 200)
        universe = CTFUniverse._from_json_dict(gm.game_state)
        original_universe = universe.copy()

        gm.set_initial()
        gm.play_round()

        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert original_universe != universe

    def test_failing_player(self):
        class FailingPlayer(AbstractPlayer):
            def get_move(self):
                return 1

        test_layout = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)
        teams = [SimpleTeam(FailingPlayer()), SimpleTeam(SteppingPlayer("^"))]

        gm = GameMaster(test_layout, teams, 2, 1)

        gm.play()
        assert gm.game_state["timeout_teams"] == [1, 0]

    def test_viewer_may_change_gm(self):

        class MeanViewer(AbstractViewer):
            def set_initial(self, game_state):
                universe = CTFUniverse._from_json_dict(gm.game_state)
                universe.teams[1].score = 50
                game_state.update(universe._to_json_dict())

            def observe(self, game_state):
                universe = CTFUniverse._from_json_dict(gm.game_state)
                universe.teams[0].score = 100
                universe.bots[0].current_pos = (4,2)
                universe.maze[0,0] = False

                game_state["team_wins"] = 0
                game_state.update(universe._to_json_dict())
                print(game_state)

        test_start = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)

        number_bots = 2

        teams = [
            SimpleTeam(SteppingPlayer([(0,0)])),
            SimpleTeam(SteppingPlayer([(0,0)]))
        ]
        gm = GameMaster(test_start, teams, number_bots, 200)
        universe = CTFUniverse._from_json_dict(gm.game_state)

        original_universe = universe.copy()

        class TestViewer(AbstractViewer):
            def observe(self, game_state):
                # universe has been altered
                universe = CTFUniverse._from_json_dict(gm.game_state)
                assert original_universe != universe

        gm.register_viewer(MeanViewer())
        gm.register_viewer(TestViewer())

        gm.set_initial()
        gm.play_round()

        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert original_universe != universe

    def test_win_on_timeout_team_0(self):
        test_start = (
            """ ######
                #0 ..#
                #.. 1#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        NUM_ROUNDS = 2
        # bot 1 moves east twice to eat the single food
        teams = [
            SimpleTeam(SteppingPlayer('>>')),
            SimpleTeam(StoppingPlayer())
        ]
        gm = GameMaster(test_start, teams, 2, game_time=NUM_ROUNDS)

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        assert tv.cache[-1]["team_wins"] is not None
        assert tv.cache[-1]["team_wins"] == 0
        assert gm.game_state["round_index"] == NUM_ROUNDS

    def test_win_on_timeout_team_1(self):
        test_start = (
            """ ######
                #0 ..#
                #.. 1#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        NUM_ROUNDS = 2

        teams = [
            SimpleTeam(StoppingPlayer()),
            SimpleTeam(SteppingPlayer('<<')) # bot 1 moves west twice to eat the single food
        ]
        gm = GameMaster(test_start, teams, 2, game_time=NUM_ROUNDS)

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        assert tv.cache[-1]["team_wins"] is not None
        assert tv.cache[-1]["team_wins"] == 1
        assert gm.game_state["round_index"] == NUM_ROUNDS

    def test_draw_on_timeout(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """)
        # the game lasts one round, and then draws
        NUM_ROUNDS = 1
        # players do nothing
        teams = [SimpleTeam(StoppingPlayer()), SimpleTeam(StoppingPlayer())]
        gm = GameMaster(test_start, teams, 2, game_time=NUM_ROUNDS)

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        assert tv.cache[-1]["game_draw"]
        assert gm.game_state["round_index"] == NUM_ROUNDS

    def test_win_on_eating_all(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """
        )
        teams = [
            SimpleTeam(StoppingPlayer()),
            SimpleTeam(SteppingPlayer('<<<'))
        ]
        # bot 1 eats all the food and the game stops
        gm = GameMaster(test_start, teams, 2, 100)

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        assert tv.cache[-1]["team_wins"] is not None
        assert tv.cache[-1]["team_wins"] == 1
        assert tv.cache[-1]["round_index"] == 1
        assert gm.game_state["round_index"] == 1

    def test_lose_on_eating_all(self):
        test_start = (
            """ ######
                #0 . #
                # . 1#
                ###### """
        )
        teams = [
            SimpleTeam(StoppingPlayer()),
            SimpleTeam(SteppingPlayer('<<<'))
        ]
        # bot 1 eats all the food and the game stops
        gm = GameMaster(test_start, teams, 2, 100)
        universe = CTFUniverse._from_json_dict(gm.game_state)
        universe.teams[0].score = 2
        gm.game_state.update(universe._to_json_dict())

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()
        gm.play()

        # check
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert tv.cache[-1]["round_index"] == 1
        assert universe.teams[0].score == 2
        assert universe.teams[1].score == 1
        assert tv.cache[-1]["team_wins"] is not None
        assert tv.cache[-1]["team_wins"] == 0
        assert gm.game_state["round_index"] == 1

    def test_lose_5_timeouts(self):
        # 0 must move back and forth because of random steps
        test_start = (
            """ ######
                #0 #.#
                ###  #
                ##. 1#
                ###### """
        )
        # players do nothing
        class TimeOutPlayer(AbstractPlayer):
            def get_move(self):
                raise PlayerTimeout

        teams = [
            SimpleTeam(TimeOutPlayer()),
            SimpleTeam(StoppingPlayer())
        ]
        # the game lasts one round, and then draws
        gm = GameMaster(test_start, teams, 2, 100, max_timeouts=5)

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()

        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (1,1)

        gm.play()

        # check
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert gm.game_state["max_timeouts"] == 5
        assert tv.cache[-1]["round_index"] == gm.game_state["max_timeouts"] - 1
        assert universe.teams[0].score == 0
        assert universe.teams[1].score == 0
        # the bot moves four times, so after the fourth time,
        # it is back on its original position
        assert universe.bots[0].current_pos == (1,1)
        assert tv.cache[-1]["team_wins"] is not None
        assert tv.cache[-1]["team_wins"] == 1

    def test_must_not_move_after_last_timeout(self):
        # 0 must move back and forth because of random steps
        # but due to its last timeout, it should be disqualified
        # immediately
        test_start = (
            """ ######
                ##0.##
                # ## #
                ##. 1#
                ###### """
        )
        # players do nothing
        class TimeOutPlayer(AbstractPlayer):
            def get_move(self):
                raise PlayerTimeout

        class CheckTestPlayer(AbstractPlayer):
            def get_move(self):
                raise RuntimeError("This should never be called")

        teams = [
            SimpleTeam(TimeOutPlayer()),
            SimpleTeam(CheckTestPlayer())
        ]
        # the game lasts one round, and then draws
        gm = GameMaster(test_start, teams, 2, 100, max_timeouts=1)

        # this test viewer caches all events lists seen through observe
        class TestViewer(AbstractViewer):
            def __init__(self):
                self.cache = list()
            def observe(self, game_state):
                self.cache.append(game_state)

        # run the game
        tv = TestViewer()
        gm.register_viewer(tv)
        gm.set_initial()

        gm.play()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        print(universe.pretty)
        print(gm.game_state)

        # check
        assert gm.game_state["max_timeouts"] == 1
        assert tv.cache[-1]["round_index"] == gm.game_state["max_timeouts"] - 1
        assert universe.teams[0].score == 0
        assert universe.teams[1].score == 0
        assert universe.bots[0].current_pos == (2,1)
        assert tv.cache[-1]["team_wins"] is not None
        assert tv.cache[-1]["team_wins"] == 1

        # the game ends in round 0 with bot_id 0
        assert gm.game_state["round_index"] == 0
        assert gm.game_state["bot_id"] == 0


    def test_play_step(self):

        test_start = (
            """ ########
                # 0  ..#
                #..  1 #
                ######## """)

        number_bots = 2


        teams = [
            SimpleTeam(SteppingPlayer('>>>>')),
            SimpleTeam(SteppingPlayer('<<<<'))
        ]
        gm = GameMaster(test_start, teams, number_bots, 4)

        gm.set_initial()

        gm.play_round()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (3,1)
        assert universe.bots[1].current_pos == (4,2)
        assert gm.game_state["round_index"] == 0
        assert gm.game_state["bot_id"] is None
        assert not gm.game_state["finished"]

        gm.play_step()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (4,1)
        assert universe.bots[1].current_pos == (4,2)
        assert gm.game_state["round_index"] == 1
        assert gm.game_state["bot_id"] == 0
        assert gm.game_state["finished"] == False

        gm.play_step()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (4,1)
        assert universe.bots[1].current_pos == (3,2)
        assert gm.game_state["round_index"] == 1
        assert gm.game_state["bot_id"] == 1
        assert gm.game_state["finished"] == False

        gm.play_step()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (5,1)
        assert universe.bots[1].current_pos == (3,2)
        assert gm.game_state["round_index"] == 2
        assert gm.game_state["bot_id"] == 0
        assert gm.game_state["finished"] == False

        gm.play_step()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (5,1)
        assert universe.bots[1].current_pos == (2,2)
        assert gm.game_state["round_index"] == 2
        assert gm.game_state["bot_id"] == 1
        assert gm.game_state["finished"] == False

        gm.play_round()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        # first call tries to finish current round (which already is finished)
        # so nothing happens
        assert universe.bots[0].current_pos == (5,1)
        assert universe.bots[1].current_pos == (2,2)
        assert gm.game_state["round_index"] == 2
        assert gm.game_state["bot_id"] is None
        assert gm.game_state["finished"] == False
        assert gm.game_state["team_wins"] == None
        assert gm.game_state["game_draw"] == None

        gm.play_round()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        # second call works
        assert universe.bots[0].current_pos == (6,1)
        assert universe.bots[1].current_pos == (2,2)
        assert gm.game_state["round_index"] == 3
        assert gm.game_state["bot_id"] == 0
        assert gm.game_state["finished"] == True
        assert gm.game_state["team_wins"] == 0
        assert gm.game_state["game_draw"] == None

        # Game finished immediately once all food for one group was eaten
        # team 0 finished first and the round was NOT played regularly to the end
        # (hence round_index == 3 and bot_id == 0)

        # nothing happens anymore
        gm.play_round()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (6,1)
        assert universe.bots[1].current_pos == (2,2)
        assert gm.game_state["round_index"] == 3
        assert gm.game_state["bot_id"] == 0
        assert gm.game_state["finished"] == True
        assert gm.game_state["team_wins"] == 0
        assert gm.game_state["game_draw"] == None

        # nothing happens anymore
        gm.play_round()
        universe = CTFUniverse._from_json_dict(gm.game_state)
        assert universe.bots[0].current_pos == (6,1)
        assert universe.bots[1].current_pos == (2,2)
        assert gm.game_state["round_index"] == 3
        assert gm.game_state["bot_id"] == 0
        assert gm.game_state["finished"] == True
        assert gm.game_state["team_wins"] == 0
        assert gm.game_state["game_draw"] == None

    def test_kill_count(self):
        test_start = (
            """ ######
                #0  1#
                #....#
                ###### """)
        # the game lasts two rounds, enough time for bot 1 to eat food
        NUM_ROUNDS = 5
        teams = [
            SimpleTeam(SteppingPlayer('>--->')),
            SimpleTeam(SteppingPlayer('<<<<<')) # bot 1 moves west twice to eat the single food
        ]
        gm = GameMaster(test_start, teams, 2, game_time=NUM_ROUNDS)

        gm.set_initial()
        gm.play_round()
        assert gm.game_state["times_killed"] == [0, 0]
        gm.play_round()
        assert gm.game_state["times_killed"] == [0, 1]
        gm.play_round()
        assert gm.game_state["times_killed"] == [0, 1]
        gm.play_round()
        assert gm.game_state["times_killed"] == [0, 2]
        gm.play_round()
        assert gm.game_state["times_killed"] == [1, 2]
