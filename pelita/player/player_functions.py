
# Player API
import collections
from typing import List

from ..containers import Mesh

MazeDimensions = collections.namedtuple('MazeDimensions', ['width', 'height'])
Position = collections.namedtuple('Position', ['x', 'y'])

def maze_dimensions(datadict) -> MazeDimensions:    
    width = datadict['maze']['width']
    height = datadict['maze']['height']
    return MazeDimensions(width=width, height=height)


def walls(datadict) -> Mesh:
    dims = maze_dimensions(datadict)
    return Mesh(width=dims.width, height=dims.height, data=datadict['maze']['data'])

def on_own_side(datadict, pos):
    w, h = maze_dimensions(datadict)
    # bot_to_play
    return pos.x < w / 2

def all_food(datadict) -> List[Position]:
    return [Position(*p) for p in datadict['food']]

def food(datadict) -> List[Position]:
    return list(filter(lambda pos: on_own_side(datadict, pos), all_food(datadict)))

def enemy_food(datadict) -> List[Position]:
    return list(filter(lambda pos: not on_own_side(datadict, pos), all_food(datadict)))

def legal_moves(datadict):
    print(walls(datadict))
    print(food(datadict))
    print(enemy_food(datadict))
    return [(0, 0)]

def reachable_positions(datadict, starting_positions: List[Position]) -> List[Position]:
    return []
