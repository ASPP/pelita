# -*- coding: utf-8 -*-

from pelita import datamodel
from pelita.player import AbstractPlayer, SimpleTeam

class SmartRandomPlayer(AbstractPlayer):
    def get_move(self):
        smart_moves = []
        dangerous_enemy_pos = [bot for bot in self.enemy_bots if bot.is_destroyer]
        killable_enemy_pos = [bot for bot in self.enemy_bots if bot.is_harvester]
        for move, new_pos in self.legal_moves.iteritems():
            if move == datamodel.stop:
                continue
            if new_pos in dangerous_enemy_pos:
                continue
            if new_pos in killable_enemy_pos:
                return move
            if new_pos in self.enemy_food:
                return move
            smart_moves.append(move)
        try:
            return self.rnd.choice(smart_moves)
        except IndexError:
            return datamodel.stop

def factory():
    return SimpleTeam("The Smart Random Players", SmartRandomPlayer(), SmartRandomPlayer())

