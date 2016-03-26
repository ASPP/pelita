from pelita.datamodel import stop
from pelita.player import AbstractPlayer, SimpleTeam


class SmartRandomPlayer(AbstractPlayer):
    def get_move(self):
        dangerous_enemy_pos = [bot.current_pos
            for bot in self.enemy_bots if bot.is_destroyer]
        killable_enemy_pos = [bot.current_pos
            for bot in self.enemy_bots if bot.is_harvester]

        smart_moves = []
        for move, new_pos in list(self.legal_moves.items()):
            if (move == stop or
                new_pos in dangerous_enemy_pos):
                continue # bad idea
            elif (new_pos in killable_enemy_pos or
                  new_pos in self.enemy_food):
                return move # get it!
            else:
                smart_moves.append(move)

        if smart_moves:
            return self.rnd.choice(smart_moves)
        else:
            # we ran out of smart moves
            return stop

def factory():
    return SimpleTeam("The Smart Random Players", SmartRandomPlayer(), SmartRandomPlayer())
