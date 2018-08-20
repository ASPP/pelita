def next_step(bot_position, target_position, graph):
    """Given a graph representation of the maze, return the next position
    in the (shortest-)path to target_position.

    The shortest path is computed on the graph using the a-star algorithm"""
    return graph.a_star(bot_position, target_position)[-1]

