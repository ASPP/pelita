
from pelita import datamodel
from pelita.player import AbstractPlayer, SimpleTeam

class StoppingPlayer(AbstractPlayer):
    """ A Player that just stands still. """
    def get_move(self):
        return datamodel.stop

def team():
    return SimpleTeam("Stopping", StoppingPlayer(), StoppingPlayer())
