def shortest_path(bot_position, target_position, graph):
    """Given a graph representation of the maze, return the shortest-path to target_position.

    The shortest path is computed on the graph using the a-star algorithm"""
    return graph.a_star(bot_position, target_position)

def walls_to_nxgraph(walls):
    """Return a networkx Graph object given a pelita maze (walls)"""
    import networkx
    graph = networkx.Graph()
    width = max([coord[0] for coord in walls]) + 1
    heigth = max([coord[1] for coord in walls]) + 1
    for x in range(width):
        for y in range(heigth):
            if (x, y) not in walls:
                # this is a free position, get its neighbors
                for delta_x, delta_y in ((1,0), (-1,0), (0,1), (0,-1)):
                    neighbor = (x + delta_x, y + delta_y)
                    # we don't need to check for getting neighbors out of the maze
                    # because our mazes are all surrounded by walls, i.e. our
                    # deltas will not put us out of the maze
                    if neighbor not in walls:
                        # this is a genuine neighbor, add an edge in the graph
                        graph.add_edge((x, y), neighbor)
    return graph
