import pelita.universe as uni
import random

class GameMaster(object):

    def __init__(self, layout, number_bots, game_time):
        self.universe = uni.create_CTFUniverse(layout, number_bots)
        self.game_time = game_time
        self.players = [None] * number_bots
        self.viewers = []

    def register_player(self,index, player):
        self.players[index] = player
        player.set_initial(self.universe)

    def register_viewer(self, viewer):
        self.viewers.append(viewer)

    def play(self):
        for gt in range(self.game_time):
            for i,p in enumerate(self.players):
                move = p.get_move(self.universe)
                self.universe.move_bot(i, move)
                for v in self.viewers:
                    v.observe(gt, i, self.universe)
            # TODO check for victory

class AsciiViewer(object):

    def __init__(self):
        pass

    def observe(self, round_, turn, universe):
        print ("Round: %i Turn: %i Score: %i:%i"
        % (round_, turn, universe.teams[0].score, universe.teams[1].score))
        print universe.as_str()

class RandomPlayer(object):

    def __init__(self, index):
        self.index = index

    def set_initial(self, universe):
        pass

    def get_move(self, universe):
        legal_moves = universe.get_legal_moves(universe.bots[self.index].current_pos)
        return random.choice(legal_moves.keys())

if __name__ == '__main__':
    layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)
    gm = GameMaster(layout, 4, 200)
    gm.register_player(0, RandomPlayer(0))
    gm.register_player(1, RandomPlayer(1))
    gm.register_player(2, RandomPlayer(2))
    gm.register_player(3, RandomPlayer(3))
    gm.register_viewer(AsciiViewer())
    gm.play()
