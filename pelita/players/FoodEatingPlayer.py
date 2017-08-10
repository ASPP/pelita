from pelita import datamodel
from pelita.graph import AdjacencyList, NoPathException, diff_pos
from pelita.player import AbstractPlayer, SimpleTeam


class FoodEatingPlayer(AbstractPlayer):
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
            next_pos = self.goto_pos(self.next_food)
            move = diff_pos(self.current_pos, next_pos)
            return move
        except NoPathException:
            return datamodel.stop

def factory():
    return SimpleTeam("The Food Eating Players", FoodEatingPlayer(), FoodEatingPlayer())
