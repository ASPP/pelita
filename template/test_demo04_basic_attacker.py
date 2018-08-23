from demo04_basic_attacker import move
from pelita.utils import setup_test_game, create_layout

def test_eat_food():
    # do we eat food when it's available?
    layout="""
    ########
    #    0.#
    #.1  EE#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    next_move = move(0, game)
    assert next_move == (1, 0)

def test_no_kamikaze():
    # do we avoid enemies when they can kill us?
    layout="""
    ########
    #    E.#
    #.1  0E#
    ########
    """
    game = setup_test_game(layout=layout, is_blue=True)
    # create a "fake" track of previous moves, as our bot needs it to decide
    # where to go to avoid a bot
    game.state = {0: {}}
    game.team[0]._track = [(4,2), (5,2)] # we use the internal attribute '_track'
                                     # because the property 'track' is read-only
    print(game.team[0].legal_moves)
    print(game.team[0].position)
    next_move = move(0, game)
    assert next_move == (-1, 0)

def test_shortest_path():
    # is the Graph implementation in pelita giving us the shortest path to the
    # food pellet? And are we really following it?

    # straight line is the right choice
    layout1="""
    ########
    #0    .#
    #.1  EE#
    ########
    """
    path1 = [(6,1), (5,1), (4,1), (3,1), (2,1)]
    # there are more alternatives now, but the shortest is unique, so we can
    # test it
    layout2="""
    ########
    #0####.#
    #      #
    #      #
    #.1  EE#
    ########
    """
    path2 = [(6, 1), (6,2), (5,2), (4,2), (3,2), (2,2), (1,2)]
    for l, p in ((layout1, path1), (layout2, path2)):
        game = setup_test_game(layout=l, is_blue=True)
        # we can ignore this, we just call move to have the bot generate the graph
        # representation of the maze
        next_move = move(0, game)
        graph = game.state['graph']
        path = graph.a_star((1,1), (6,1))
        # test that the generated path is the shortest one
        assert path == p
        # given this layout, move our bot to the next position in the shortest
        # path and see if we follow it
        path.reverse() # flip the path so we have it in the right order
        for idx, step in enumerate(path[:-1]):
            # create a layout where we are starting from the current step in
            # the path
            new_layout = create_layout(l, bots=[step])
            game = setup_test_game(layout=new_layout, is_blue=True)
            next_move = move(0, game)
            next_pos = (step[0]+next_move[0], step[1]+next_move[1])
            assert next_pos == path[idx+1]
