
import random

from pelita.player import Team
from pelita.player.player_functions import legal_moves, reachable_positions
from pelita.graph import Graph, NoPathException, diff_pos

def move1(datadict, storage):
    legal = legal_moves(datadict)
    return random.choice(legal)

def set_initial(datadict, storage):
    storage['graph'] = Graph(reachable_positions(datadict, [self.initial_pos]))
    storage['next_food'] = None

def goto_pos(self, pos):
    return self.graph.a_star(self.current_pos, pos)[-1]

def get_move(datadict, storage):
    if not storage:
        # init phase
        set_initial(datadict, storage)


    # check, if food is still present
    if (storage['next_food'] is None or storage['next_food'] not in self.enemy_food):
        if not storage['next_food']:
            # all food has been eaten? ok. i’ll stop
            return (0, 0)
        storage['next_food'] = self.rnd.choice(self.enemy_food)

    try:
        dangerous_enemy_pos = [bot.current_pos for bot in self.enemy_bots if bot.is_destroyer]

        next_pos = self.goto_pos(storage['next_food'])
        # check, if the next_pos has an enemy on it
        if next_pos in dangerous_enemy_pos:
            # whoops, better wait this round and take another food next time
            storage['next_food'] = None
            return (0, 0)

        move = diff_pos(self.current_pos, next_pos)
        return move
    except NoPathException:
        return (0, 0)

def team():
    return Team("My Team", move1, get_move)
