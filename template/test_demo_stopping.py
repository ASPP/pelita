from demo_stopping import move
from pelita.utils import setup_test_game, create_layout

def test_stays_there():
    layout="""
    ########
    #     .#
    #.1  EE#
    ########
    """
    # verify that we always stay where we are, indipendent
    # of that initial position. Try all possible initial
    # positions
    all_locations = ((x, y) for x in range(1,7) for y in range(1,7))
    for loc in all_locations:
        loc_layout = create_layout(layout)
        loc_layout.bot_positions["0"] = loc
        game = setup_test_game(layout=loc_layout, is_blue=True)
        next_move = move(0, game)
        assert next_move == (0,0)

