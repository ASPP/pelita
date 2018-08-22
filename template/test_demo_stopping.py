from demo_stopping import move
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
            loc_layout = create_layout(layout, bots=[loc, None])
        except ValueError:
            # loc is a wall, skip this position
            continue
        game = setup_test_game(layout=loc_layout, is_blue=True)
        next_move = move(0, game)
        assert next_move == (0,0)

