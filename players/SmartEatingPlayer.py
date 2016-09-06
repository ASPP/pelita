from pelita import datamodel
from pelita.graph import AdjacencyList, NoPathException, diff_pos
from pelita.player import AbstractPlayer, SimpleTeam


class SmartEatingPlayer(AbstractPlayer):
    def set_initial(self):
        self.adjacency = AdjacencyList(self.current_uni.reachable([self.initial_pos]))
        self.next_food = None

    def goto_pos(self, pos):
        return self.adjacency.a_star(self.current_pos, pos)[-1]

    def get_move(self):
        # check, if food is still present
        if (self.next_food is None
                or self.next_food not in self.enemy_food):
            if not self.enemy_food:
                # all food has been eaten? ok. i’ll stop
                return datamodel.stop
            self.next_food = self.rnd.choice(self.enemy_food)

        try:
            dangerous_enemy_pos = [bot.current_pos
                                   for bot in self.enemy_bots if bot.is_destroyer]

            next_pos = self.goto_pos(self.next_food)
            # check, if the next_pos has an enemy on it
            if next_pos in dangerous_enemy_pos:
                # whoops, better wait this round and take another food next time
                self.next_food = None
                return datamodel.stop

            move = diff_pos(self.current_pos, next_pos)
            return move
        except NoPathException:
            return datamodel.stop

def factory():
    return SimpleTeam("Smart Eating Players", SmartEatingPlayer(), SmartEatingPlayer())
