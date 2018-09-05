from demo01_stopping import move
from pelita.utils import setup_test_game, create_layout

def test_stays_there():
    # Given a simple layout, verify that the bot does not move, indipendent
    # of its initial position.
    layout="""
    ########
    #     .#
    #.1  EE#
    ########
    """
    # generate all possible locations within the maze
    all_locations = ((x, y) for x in range(8) for y in range(4))
    for loc in all_locations:
        try:
            game = setup_test_game(layout=layout, is_blue=True, bots=[loc])
        except ValueError:
            # loc is a wall, skip this position
            continue
        next_move = move(0, game)
        assert next_move == (0,0)

