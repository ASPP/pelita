import textwrap
from random import Random

import networkx as nx
import numpy as np
import pytest

import pelita.maze_generator as mg

SEED = 103525239


def test_maze_bytes_str_conversions():
    # note that the first empty line is needed!
    maze_str = """
                  ##################
                  #. ... .##.     y#
                  # # #  .  .### #x#
                  # # ##.   .      #
                  #      .   .## # #
                  #a# ###.  .  # # #
                  #b     .##. ... .#
                  ##################"""
    maze_bytes = bytes(maze_str, 'ascii')
    maze_clist = [[b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#',b'#'],
                  [b'#',b'.',b' ',b'.',b'.',b'.',b' ',b'.',b'#',b'#',b'.',b' ',b' ',b' ',b' ',b' ',b'y',b'#'],
                  [b'#',b' ',b'#',b' ',b'#',b' ',b' ',b'.',b' ',b' ',b'.',b'#',b'#',b'#',b' ',b'#',b'x',b'#'],
                  [b'#',b' ',b'#',b' ',b'#',b'#',b'.',b' ',b' ',b' ',b'.',b' ',b' ',b' ',b' ',b' ',b' ',b'#'],
                  [b'#',b' ',b' ',b' ',b' ',b' ',b' ',b'.',b' ',b' ',b' ',b'.',b'#',b'#',b' ',b'#',b' ',b'#'],
                  [b'#',b'a',b'#',b' ',b'#',b'#',b'#',b'.',b' ',b' ',b'.',b' ',b' ',b'#',b' ',b'#',b' ',b'#'],
                  [b'#',b'b',b' ',b' ',b' ',b' ',b' ',b'.',b'#',b'#',b'.',b' ',b'.',b'.',b'.',b' ',b'.',b'#'],
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
                  #         #    #               #
                  #  # #########                 #
                  #  # #                         #
                  #  #         # #               #
                  #  ####### ###                 #
                  #  #                           #
                  # ### ###### ###               #
                  #      #       #               #
                  ##### ## # ###                 #
                  #   #        #                 #
                  #   #          #               #
                  ##    ###### #                 #
                  #   #      #                   #
                  #              #               #
                  ################################"""

    maze = mg.empty_maze(16,32)
    mg.create_half_maze(maze, 8, rng=SEED)
    expected = mg.str_to_maze(maze_str)
    print(mg.maze_to_str(maze))
    assert np.all(maze == expected)

def test_conversion_to_nx_graph():
    maze_str = """##################
                  #       ##       #
                  # # #      ### # #
                  # # ##           #
                  #           ## # #
                  # # ###      # # #
                  #       ##       #
                  ##################"""
    maze = mg.str_to_maze(maze_str)
    graph = mg.walls_to_graph(maze)
    # now derive a maze from a graph manually
    # - start with a maze full of walls
    newmaze = mg.empty_maze(maze.shape[0], maze.shape[1])
    newmaze.fill(mg.W)
    # - loop through each node of the graph and remove a wall at the
    # corresponding coordinate
    for node in graph.nodes():
        newmaze[node[1], node[0]] = mg.E
    assert np.all(maze == newmaze)

def test_find_one_dead_end():
    # this maze has exactly one dead end at coordinate (1,1)
    maze_dead = """########
                   # #    #
                   #      #
                   #      #
                   ########"""

    maze = mg.str_to_maze(maze_dead)
    graph = mg.walls_to_graph(maze)
    width = maze.shape[1]
    dead_ends = mg.find_dead_ends(graph, width)
    assert len(dead_ends) == 1
    assert dead_ends[0] == (1,1)

def test_find_multiple_dead_ends():
    # this maze has exactly three dead ends at coordinates (1,1), (1,5), (3,5)
    maze_dead = """############
                   # #        #
                   #          #
                   #          #
                   # # #      #
                   # # #      #
                   ############"""

    maze = mg.str_to_maze(maze_dead)
    graph = mg.walls_to_graph(maze)
    width = maze.shape[1]
    dead_ends = mg.find_dead_ends(graph, width)
    assert len(dead_ends) == 3
    dead_ends.sort()
    assert dead_ends[0] == (1,1)
    assert dead_ends[1] == (1,5)
    assert dead_ends[2] == (3,5)

def test_find_multiple_dead_ends_on_the_right():
    # this maze has exactly three dead ends at coordinates (10,1), (10,5), (8,5)
    maze_dead = """############
                   #        # #
                   #          #
                   #          #
                   #      # # #
                   #      # # #
                   ############"""

    maze = mg.str_to_maze(maze_dead)
    graph = mg.walls_to_graph(maze)
    width = maze.shape[1]
    dead_ends = mg.find_dead_ends(graph, width)
    assert len(dead_ends) == 3
    dead_ends.sort()
    assert dead_ends[2] == (10,5)
    assert dead_ends[1] == (10,1)
    assert dead_ends[0] == (8,5)

def test_remove_one_dead_end():
    # this maze has exactly one dead end at coordinate (1,1)
    maze_dead = """########
                   # #    #
                   #      #
                   #      #
                   ########"""

    maze = mg.str_to_maze(maze_dead)
    mg.remove_dead_end((1,1), maze)
    assert maze[1,1] == mg.E

def test_remove_multiple_dead_ends():
    # this maze has exactly three dead ends at coordinates (1,1), (1,5), (3,5)
    maze_dead = """############
                   # #        #
                   #          #
                   #          #
                   # # #      #
                   # # #      #
                   ############"""

    maze = mg.str_to_maze(maze_dead)
    mg.remove_all_dead_ends(maze)
    # There are many ways of getting rid of the two dead ends at the bottom
    # The one that requires the less work is to remove the left-bottom wall
    # This one is the solution we get from remove_all_dead_ends, but just
    # because the order in which we find dead ends is from top to bottom and from
    # left to right.
    # In other words, remove the dead ends here actually means getting this maze back
    expected_maze = """############
                       #          #
                       #          #
                       #          #
                       # # #      #
                       #   #      #
                       ############"""
    expected_maze = mg.str_to_maze(expected_maze)
    assert np.all(maze == expected_maze)

def test_find_chamber():
    # This maze has one single chamber, whose entrance is one of the
    # nodes (1,2), (1,3) or (1,4)
    maze_chamber = """############
                      #   #      #
                      #   #      #
                      # ###      #
                      #          #
                      #          #
                      ############"""

    maze = mg.str_to_maze(maze_chamber)
    maze_orig = maze.copy()
    mg.remove_all_dead_ends(maze)
    # first, check that the chamber is not mistaken for a dead end
    assert np.all(maze_orig == maze)
    # now check that we detect it
    graph = mg.walls_to_graph(maze)
    # there are actually two nodes that can be considered entrances
    entrance, chamber = mg.find_chamber(graph)
    assert entrance in ((1,2), (1,3), (1,4))
    # check that the chamber contains the right nodes. Convert to set, because
    # the order is irrelevant
    if entrance == (1,4):
        expected_chamber = {(1,1), (1,2), (1,3), (2,1), (2,2), (3,1), (3,2)}
    elif entrance == (1,3):
        expected_chamber = {(1,1), (1,2), (2,1), (2,2), (3,1), (3,2)}
    else:
        expected_chamber = {(1,1), (2,1), (2,2), (3,1), (3,2)}
    assert set(chamber) == expected_chamber

    # now remove the chamber and verify that we don't detect anything
    # we just remove wall (4,1) manually
    maze = mg.str_to_maze(maze_chamber)
    maze[1,4] = mg.E # REMEMBER! Indexing is maze[y,x]!!!
    graph = mg.walls_to_graph(maze)
    entrance, chamber = mg.find_chamber(graph)
    assert entrance is None
    assert chamber == []




maze_one_chamber = """############
                      #   #      #
                      #   #      #
                      # ###      #
                      #          #
                      #          #
                      ############"""
maze_two_chambers = """############
                       #   #      #
                       #   #      #
                       # ###  # ###
                       #      #   #
                       #      #   #
                       #      #   #
                       #      #   #
                       ############"""
maze_neighbor_chambers = """####################
                            #   ##   #         #
                            #   ##   #         #
                            # ###### #         #
                            #                  #
                            #                  #
                            #                  #
                            ####################"""
maze_chamber_in_chamber = """######################
                             #                    #
                             #                    #
                             #                    #
                             ##### ####           #
                             #        #           #
                             #   #    #           #
                             ######################"""
maze_chamber_bonanza = """################################
                          #   #   #                      #
                          #   #   #                      #
                          #   ### #                      #
                          #                              #
                          #                              #
                          ###### ##########              #
                          #               #              #
                          #               #              #
                          # ###########   #              #
                          #           #                  #
                          ##### ####  #   #              #
                          #        #  #   #              #
                          #   #    #  #   #              #
                          ################################"""


@pytest.mark.parametrize("maze_chamber", (maze_one_chamber,
                                          maze_two_chambers,
                                          maze_neighbor_chambers,
                                          maze_chamber_in_chamber,
                                          maze_chamber_bonanza,))
def test_remove_all_chambers(maze_chamber):
    maze = mg.str_to_maze(maze_chamber)
    mg.remove_all_chambers(maze)
    # there are no more chambers if the connectivity of the graph is larger than 1
    graph = mg.walls_to_graph(maze)
    assert nx.node_connectivity(graph) > 1
    #XXX: TODO -> an easy way of getting rid of chambers is to just remove all the
    # walls. How can we test that this is not what we are doing but that instead
    # we are removing just a few walls?

@pytest.mark.parametrize('iteration', range(1,11))
def test_get_new_maze(iteration):
    # generate a few mazes and check them for consistency
    local_seed = 12345 * iteration
    maze_str = mg.get_new_maze(8,16,nfood=15,rng=local_seed)
    maze = mg.str_to_maze(maze_str)
    height, width = maze.shape
    # check that the returned maze has all the pacmen
    for pacman in (b'a',b'x',b'b',b'y'):
        assert np.any(maze == pacman)
        # now that we now we have a pacman, check that we have it only once
        # and remove it by putting an empty space instead
        row, col = np.nonzero(maze == pacman)
        assert len(row) == 1
        assert len(col) == 1
        maze[row,col] = mg.E

    # check that we have in total twice nfood in the maze
    assert (maze == mg.F).sum() == 15*2
    # remove the food for computing dead ends and chambers
    maze[maze == mg.F] = mg.E

    # check that the returned maze is center-mirror symmetric
    left_maze = np.flipud(np.fliplr(maze[:,width//2:]))
    assert np.all(left_maze == maze[:,:width//2])

    # check that we don't have any dead ends
    # no node in the graph should have only one connection
    graph = mg.walls_to_graph(maze)
    for node, degree in graph.degree():
        assert degree > 1

    # now check that we don't have chambers, i.e. the connectivity of the
    # graph is > 1
    assert nx.node_connectivity(graph) > 1

def test_odd_width():
    with pytest.raises(ValueError):
        mg.get_new_maze(2,3,1)

def test_add_food():
    mini = """########
              #      #
              #      #
              ########"""
    maze = mg.str_to_maze(mini)
    # We have 12 empty squares in total, so 6 on the left side.
    # -> 2 slots are taken by the dividing border, so we have 4 left
    # -> 2 are reserved for pacmen, so we have only 2 slots for food
    # - check that we can indeed accommodate 2 pellets in the maze
    lmaze = maze.copy()
    mg.add_food(lmaze, 2)
    assert (lmaze == mg.F).sum() == 2
    # - check that if we add a wall in a free spot that is not reserved by the
    #   pacmen we can only accommodate 1 pellet
    lmaze = maze.copy()
    lmaze[1,2] = mg.W
    mg.add_food(lmaze, 1)
    assert (lmaze == mg.F).sum() == 1
    # - if we try to add more food, we complain
    lmaze = maze.copy()
    lmaze[1,2] = mg.W
    with pytest.raises(ValueError):
        mg.add_food(lmaze, 2)
    # - check that if no space is left we complain
    lmaze = maze.copy()
    lmaze[1,2], lmaze[2,2] = mg.W, mg.W
    with pytest.raises(ValueError):
        mg.add_food(lmaze, 1)
    # - check that we fail if we get passed unreasonable amounts of food
    lmaze = maze.copy()
    with pytest.raises(ValueError):
        mg.add_food(lmaze, -1)
    # - check that we can cope with no food to add
    lmaze = maze.copy()
    mg.add_food(lmaze, 0)
    assert np.all(lmaze == maze)

