from demo_random import move
from pelita.utils import setup_test_game, create_layout

def test_always_legal():
    # Given a simple layout, verify that the bot always returns a valid move,
    # indipendent of the initial position and of location of enemies and food
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
            loc_layout = create_layout(layout, bots=[loc])
        except ValueError:
            # loc is a wall, skip this position
            continue
        game = setup_test_game(layout=loc_layout, is_blue=True)
        next_move = move(0, game)
        legal_moves = game.team[0].legal_moves
        assert next_move in legal_moves

