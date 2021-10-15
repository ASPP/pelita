""" Base classes for player implementations. """


def speaking_player(bot, state):
    """ A player that makes moves at random and tells us about it. """
    move = bot.random.choice(bot.legal_positions)
    bot.say(f"Going {move}.")
    return move


def stepping_player(*bot_moves):
    """ A Player with predetermined set of moves.

    Parameters
    ----------
    moves : list of moves or str of shorthand symbols
        the moves to make in order, see notes below

    Notes
    -----
    The ``moves`` argument can either be a list of moves, e.g. ``[west, east,
    south, north, stop]`` or a string of shorthand symbols, where the equivalent
    of the previous example is: ``'><v^-'``.

    """
    _MOVES = {
        '^': (0, -1),
        'v': (0, 1),
        '<': (-1, 0),
        '>': (1, 0),
        '-': (0, 0),
    }

    def convert(next_move):
        if isinstance(next_move, str):
            return _MOVES[next_move]
        else:
            return next_move

    converted_moves = [map(convert, m) for m in bot_moves]
    iterators = [iter(m) for m in converted_moves]

    def move(bot, state):
        moves_iter = iterators[bot.turn]
        try:
            next_move = next(moves_iter)
            return (bot.position[0] + next_move[0], bot.position[1] + next_move[1])
        except StopIteration:
            raise ValueError()
    return move


def round_based_player(*bot_moves):
    """ A Player which makes a decision dependent on the round index
    in a dict or list. (Or anything which responds to moves[idx].)

    Parameters
    ----------
    moves : list or dict of moves
        the moves to make, a move is determined by moves[round]
    """
    def move(bot, state):
        try:
            next_move = bot_moves[bot.turn][bot.round]
            return (bot.position[0] + next_move[0], bot.position[1] + next_move[1])
        except (IndexError, KeyError):
            return bot.position
    return move


def move_exception_player(bot, state):
    """ Player that raises an Exception on get_move(). """
    raise Exception("Exception from MoveExceptionPlayer.")


def debuggable_player(bot, state):
    """ Player which invokes pdb on each move.

    Setting ``positions`` inside the debugger will change
    its behaviour.
    """
    position = bot.position
    breakpoint()
    return position
