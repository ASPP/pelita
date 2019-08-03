import pytest

from pelita.utils import create_layout
import utils

def test_walls_to_graph_full():
    # skip the test if networkx is not installed
    networkx = pytest.importorskip('networkx')

    layout="""
    ########
    #      #
    #      #
    ########
    """
    l = create_layout(layout)
    graph = utils.walls_to_graph(l['walls'])
    # test that we generate a path of the proper size
    assert len(graph.nodes) == 12
    # test that the graph doesn't have walls in between
    assert networkx.shortest_path_length(graph, (1,1), (6,1)) == 5

def test_walls_to_graph_one_wall():
    # skip the test if networkx is not installed
    networkx = pytest.importorskip('networkx')

    layout="""
    ########
    #  #   #
    #      #
    ########
    """
    l = create_layout(layout)
    graph = utils.walls_to_graph(l['walls'])
    assert networkx.shortest_path_length(graph, (1,1), (6,1)) == 7
    with pytest.raises(networkx.NodeNotFound):
        networkx.has_path(graph, (3,1), (0,0))

def test_walls_to_graph_impossible():
    # skip the test if networkx is not installed
    networkx = pytest.importorskip('networkx')

    layout="""
    ########
    #  #   #
    #  #   #
    ########
    """
    l = create_layout(layout)
    graph = utils.walls_to_graph(l['walls'])
    assert networkx.has_path(graph, (1,1), (6,1)) is False

