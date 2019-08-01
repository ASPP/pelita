
class FatalException(Exception): # TODO rename to FatalGameException etc
    pass

class NonFatalException(Exception):
    pass

class PlayerTimeout(NonFatalException):
    pass

class PlayerDisconnected(FatalException):
    # unsure, if PlayerDisconnected should be fatal in the sense of that the team loses
    # it could simply be a network error for both teams
    # and it would be random who will be punished
    pass

class NoFoodWarning(Warning):
    """ Warns when a layout has no food during setup. """
    pass
