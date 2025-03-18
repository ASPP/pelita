import textwrap
from random import Random

import networkx as nx
import numpy as np
import pytest

import pelita.maze_generator as mg
import pelita.layout

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

    graph = mg.walls_to_graph(maze)
    width = maze.shape[1]
    dead_ends = mg.find_dead_ends(graph, width)
    assert len(dead_ends) == 0


def test_find_chambers():
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
    width = maze_orig.shape[1]
    chamber_tiles = mg.find_chambers(graph, width)
    assert chamber_tiles == {(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (3, 1), (3, 2)}

    # now remove the chamber and verify that we don't detect anything
    # we just remove wall (4,1) manually
    maze = mg.str_to_maze(maze_chamber)
    maze[1,4] = mg.E # REMEMBER! Indexing is maze[y,x]!!!
    graph = mg.walls_to_graph(maze)
    chamber_tiles = mg.find_chambers(graph, width)
    assert len(chamber_tiles) == 0


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
def test_create_maze(iteration):
    # generate a few mazes and check them for consistency
    local_seed = SEED * iteration
    maze_str = mg.create_maze(8,16,nfood=15,rng=local_seed)
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
        mg.create_maze(2,3,1)

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


def test_distribute_food():
    maze_chamber = """############
                      #   #      #
                      #   #      #
                      # ###      #
                      #          #
                      #          #
                      ############"""

    maze = mg.str_to_maze(maze_chamber)
    graph = mg.walls_to_graph(maze)
    all_tiles = set(graph.nodes)
    width = maze.shape[1]
    chamber_tiles = mg.find_chambers(graph, width)

    # expected exceptions
    with pytest.raises(ValueError):
        mg.distribute_food(all_tiles, chamber_tiles, 0, len(all_tiles) + 1)

    with pytest.raises(ValueError):
        mg.distribute_food(all_tiles, chamber_tiles, 10, 8)

    # no intersection of food positions and chamber_tiles
    trapped_food = 0
    total_food = 10
    food = mg.distribute_food(all_tiles, chamber_tiles, trapped_food, total_food)
    assert len(set(food) & chamber_tiles) == trapped_food

    # trapped food is placed in chamber as requested
    # all food is placed as requested
    trapped_food = 3
    food = mg.distribute_food(all_tiles, chamber_tiles, trapped_food, total_food)
    assert len(food & chamber_tiles) == trapped_food
    assert len(food) == total_food

    # food is completely contained in chamber
    total_food = trapped_food = 3
    food = mg.distribute_food(all_tiles, chamber_tiles, trapped_food, total_food)
    assert food.issubset(chamber_tiles)
    assert len(food) == total_food

    # best effort placement of trapped food
    trapped_food = 10  # > 7 chamber_tiles
    total_food = 20
    food = mg.distribute_food(all_tiles, chamber_tiles, trapped_food, total_food)
    assert len(food & chamber_tiles) == len(chamber_tiles)
    assert len(food) == total_food

    # distribute only leftover food in chambers, fill non-chambers first
    trapped_food = 1
    free_tiles = all_tiles - chamber_tiles
    n_free_tiles = len(free_tiles)
    leftover_food = 2
    total_food = n_free_tiles + trapped_food + leftover_food
    food = mg.distribute_food(all_tiles, chamber_tiles, trapped_food, total_food)
    assert len(food) == total_food
    assert (food & free_tiles) == free_tiles
    assert len(food & chamber_tiles) == trapped_food + leftover_food

    # edge case, no food at all
    food = mg.distribute_food(all_tiles, chamber_tiles, 0, 0)
    assert len(food) == 0

np_maze_generator_86523 = """
################################
# #  ..  ..  # ##    # ..  #  y#
# # . .           .. ## ####  x#
#       .. . #     . #   . ## ##
#.#### #######    ####.#. .#   #
#. .  .        ## .# # #       #
#.#  ## ######     #  .### #####
#     ....   . ## ## #      #  #
#  #      # ## ## .   ....     #
##### ###.  #     ###### ##  #.#
#       # # #. ##        .  . .#
#   #. .#.####    ####### ####.#
## ## .   # .     # . ..       #
#a  #### ## ..           . . # #
#b  #  .. #    ## #  ..  ..  # #
################################
"""

def test_create_maze_graph_compatibility():
    # make sure that we are reproducing the mazes generated by the old
    # numpy implementation
    seed = 86523
    height, width = 16,32


    # original call was:
    #np_str = mg.create_maze(height, width, food, dead_ends=True, rng=seed)
    np_layout = pelita.layout.parse_layout(np_maze_generator_86523)
    new_layout = mg.create_maze_graph(trapped_food=0, total_food=30, width=width, height=height, rng=seed)
    # we can not compare the food distribution, because the two algorithms
    # distribute food in a different way
    assert np_layout['walls'] == new_layout['walls']
    assert np_layout['bots'] == new_layout['bots']

@pytest.mark.parametrize('iteration', range(100))
def test_numpy_compatibility(iteration):
    local_seed = SEED + iteration
    height, width = 16,32
    rand = Random()
    rand.seed(local_seed)
    l_str = mg.create_maze(height, width, 30, dead_ends=True, rng=rand)
    np_layout = pelita.layout.parse_layout(l_str)
    rand.seed(local_seed)
    new_layout = mg.create_maze_graph(trapped_food=0, total_food=30, width=width, height=height, rng=rand)
    assert np_layout['walls'] == new_layout['walls']
    assert np_layout['bots'] == new_layout['bots']

@pytest.mark.parametrize('iteration', range(100))
def test_create_maze_graph(iteration):
    local_seed = SEED * iteration
    rng = Random(local_seed)

    # edge cases
    # width not even
    with pytest.raises(ValueError):
        mg.create_maze_graph(0, 0, 9, 10, rng=rng)

    # width too small
    with pytest.raises(ValueError):
        mg.create_maze_graph(0, 0, 2, 10, rng=rng)

    # height too small
    with pytest.raises(ValueError):
        mg.create_maze_graph(0, 0, 10, 2, rng=rng)


    width = rng.choice(range(16, 65, 2))
    height = rng.randint(8, 32)
    total_food = int(0.15 * width * height / 2)
    trapped_food = int(total_food / 3)

    ld = mg.create_maze_graph(trapped_food, total_food, width, height, rng=rng)

    walls = set(ld["walls"])

    border = set()
    for x in range(width):
        border.add((x, 0))
        border.add((x, height - 1))

    for y in range(height):
        border.add((0, y))
        border.add((width - 1, y))

    def split(nodes, width):
        left = [node for node in nodes if node[0] < width // 2]
        right = [node for node in nodes if node[0] >= width // 2]
        return left, right

    def is_full_mirror(left, right, width, height):
        right_copy = right[:]

        for x, y in left:
            mirrored = (width - 1 - x, height - 1 - y)
            if mirrored not in right:
                return False
            else:
                right_copy.remove(mirrored)

        if len(right_copy) > 0:
            return False

        return True

    # check that the maze is mirrored around the center
    left_walls, right_walls = split(ld["walls"], width)
    left_food, right_food = split(ld["food"], width)
    assert is_full_mirror(left_walls, right_walls, width, height)
    assert is_full_mirror(left_food, right_food, width, height)

    # check that the maze is completely enclosed by walls
    assert border.issubset(set(ld["walls"]))

    # check that there is enough food
    assert len(ld["food"]) == 2 * total_food

    # check that the bots are where they are supposed to be
    assert ld["bots"] == [
        (1, height - 3),
        (width - 2, 2),
        (1, height - 2),
        (width - 2, 1),
    ]

    # verify shape
    assert min(ld["walls"]) == (0, 0)
    assert max(ld["walls"]) == (width - 1, height - 1)

    # verify that the types in the dictionary are as expected
    def is_seq_of_tuples(seq_type, thing):
        assert type(thing) is seq_type
        for item in thing:
            assert type(item) is tuple

    is_seq_of_tuples(tuple, ld["walls"])
    is_seq_of_tuples(list, ld["food"])
    is_seq_of_tuples(list, ld["bots"])
    assert type(ld["shape"]) is tuple

    # verify that we generate exactly the same maze if started with the same seed
    seed = rng.randint(1,100000)
    l1 = mg.create_maze_graph(trapped_food, total_food, width, height, rng=seed)
    l2 = mg.create_maze_graph(trapped_food, total_food, width, height, rng=seed)
    assert l1 == l2

@pytest.mark.parametrize('iteration', range(100))
def test_create_maze_graph(iteration):
    local_seed = SEED + iteration
    rng = Random(local_seed)

    width = 10
    height = 5
    total_food = 10
    trapped_food = 0
    ld = mg.create_maze_graph(trapped_food, total_food, width, height, rng=rng)
    # check that we never place food on the border
    x_food = {x for (x, y) in ld['food']}
    assert width//2 not in x_food
    assert width//2 - 1 not in x_food
