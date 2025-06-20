
class NoFoodWarning(Warning):
    """ Warns when a layout has no food during setup. """
    pass

class GameOverError(Exception):
    """ raised from game when match is game over """
    pass

class PelitaBotError(Exception):
    """ Raised when allow_exceptions is turned on """
    pass