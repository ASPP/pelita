import textwrap

import numpy as np
from pelita._layouts import maze_generator as mg

SEED = 103525239

def test_maze_bytes_str_conversions():
    # note that the first empty line is needed!
    maze_str = """
                  ##################
                  #. ... .##.     3#
                  # # #  .  .### #1#
                  # # ##.   .      #
                  #      .   .## # #
                  #0# ###.  .  # # #
                  #2     .##. ... .#
                  ##################"""
    maze_bytes = bytes(maze_str, 'ascii')
    maze_clist = [[b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#'],
                  [b'#',b'.',b' ',b'.',b'.',b'.',b' ',b'.',b'#',b'#',b'.',b' ',b' ',b' ',b' ',b' ',b'3',b'#'],
                  [b'#',b' ',b'#',b' ',b'#',b' ',b' ',b'.',b' ',b' ',b'.',b'#',b'#',b'#',b' ',b'#',b'1',b'#'],
                  [b'#',b' ',b'#',b' ',b'#',b'#',b'.',b' ',b' ',b' ',b'.',b' ',b' ',b' ',b' ',b' ',b' ',b'#'],
                  [b'#',b' ',b' ',b' ',b' ',b' ',b' ',b'.',b' ',b' ',b' ',b'.',b'#',b'#',b' ',b'#',b' ',b'#'],
                  [b'#',b'0',b'#',b' ',b'#',b'#',b'#',b'.',b' ',b' ',b'.',b' ',b' ',b'#',b' ',b'#',b' ',b'#'],
                  [b'#',b'2',b' ',b' ',b' ',b' ',b' ',b'.',b'#',b'#',b'.',b' ',b'.',b'.',b'.',b' ',b'.',b'#'],
                  [b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#']]
    maze_arr = np.array(maze_clist, dtype=bytes)
    assert np.all(mg.bytes_to_maze(maze_bytes) == maze_arr)
    assert np.all(mg.str_to_maze(maze_str) == maze_arr)
    # round trip
    # we must dedent the string and remove the first newline
    # we have the newline in the first line to have dedent work out of the box
    maze_str = textwrap.dedent(maze_str[1:])
    maze_bytes = bytes(maze_str, 'ascii')
    assert mg.maze_to_bytes(maze_arr) == maze_bytes
    assert mg.maze_to_str(maze_arr) == maze_str


def test_create_half_maze():
    # this test is not really testing that create_half_maze does a good job
    # we only test that we keep in returning the same maze when the random
    # seed is fixed, in case something changes during future porting/refactoring
    maze_str = """################################
                  #   #    #  #  #               #
                  # # #    #  #                  #
                  # #         # ##               #
                  # #   # ##                     #
                  # # #    ####                  #
                  # # #                          #
                  # # ##### ######               #
                  # ###          #               #
                  #   #                          #
                  # # #                          #
                  ######### #  #                 #
                  #              #               #
                  #    #                         #
                  #              #               #
                  ################################"""

    np.random.seed(SEED)
    maze = mg.empty_maze(16,32)
    mg.create_half_maze(maze, 8)
    expected = mg.str_to_maze(maze_str)
    assert np.all(maze == expected)

def test_conversion_to_nx_graph():
    np.random.seed(SEED)
    maze = mg.empty_maze(16,32)
    mg.create_half_maze(maze, 8)
    graph, _ = mg.walls_to_graph(maze)
    # now derive a maze from a graph manually
    # - start with a maze full of walls
    newmaze = mg.empty_maze(16,32)
    newmaze.fill(mg.W)
    # - loop through each node of the graph and remove a wall at the
    # corresponding coordinate
    for node in graph.nodes():
        newmaze[node[1], node[0]] = mg.E
    assert np.all(maze == newmaze)

def test_remove_one_dead_end():
