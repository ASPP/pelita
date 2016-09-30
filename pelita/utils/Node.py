class Node:
    """ Representation of a position in a path. 
    
    Holds the number of moves it took to get to the node (value), 
    the coordinates and the parent Node.
    
    """
    
    def __init__(self, value=None, coordinates=None, parent=None):
        self.value = value
        self.coordinates = coordinates
        self.parent = parent
        
    def __str__(self):
        return str(self.value)
    
    def __lt__(self, other):
        return self.value < other.value
        
    def backtrack(self):
        """ Backtracks through the parent Nodes to find the path that let to 
        this node.
        
        Returns
        -------
        path : list of tuple of (int, int)
            the path from the first partent Node to the current Node.
        
        """
        
        parent_list = []
        if self.parent:
            parent_list = self.parent.backtrack()
        return parent_list + [self.coordinates]
        
    def check_in_path(self, pos):
        """ Checks if a given position is in the path.
       
        Parameters
        ----------
        pos : tuple of (int, int)
            the position to be checked

        Returns
        -------
        in_path : boolean
            True if the pos is in the path from the first parent to the
            current Node
            
        """
        in_parent = False
        if self.parent:
            in_parent = self.parent.check_in_path(pos)
        in_path = (pos == self.coordinates or in_parent)
        return in_path
            
        