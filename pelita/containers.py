from collections import Mapping, MutableSequence
import inspect

""" Advanced container classes. """

__docformat__ = "restructuredtext"

def new_pos(position, move):
    """ Adds a position tuple and a move tuple.

    Parameters
    ----------
    position : tuple of int (x, y)
        current position

    move : tuple of int (x, y)
        direction vector

    Returns
    -------
    new_pos : tuple of int (x, y)
        new position coordinates

    """
    pos_x = position[0] + move[0]
    pos_y = position[1] + move[1]
    return (pos_x, pos_y)

class Mesh(Mapping):
    """ A mapping from a two-dimensional coordinate system into object space.

    Using a list of lists to represent a matrix is memory inefficient, slow,
    (ugly) and requires much effort to keep all lists the same length.
    Instead we store the matrix data in a single list and provide accessor and
    mutator methods (`__getitem__()` and `__setitem__()`) to access the elements
    in a matrixy style.

    Attributes
    ----------
    width : int
        width of the Mesh
    height : int
        height of the Mesh
    shape : (int, int)
        tuple of width and height

    Parameters
    ----------
    width : int
        desired width for Mesh
    height : int
        desired height for Mesh
    data : list, optional
        if given, will try to set this as contents

    Notes
    -----
    Once the container has been allocated, it cannot be resized.

    The container can store arbitrary type objects and even mix types.

    The constructor will preallocate a container with an appropriate shape, and
    populate this with `None`.

    The container cannot be sliced.

    The items are stored row-based (C-order).

    Since this container inherits from `collections.Mapping` you can use methods
    similar to those of the dictionary:

    * `keys()`
    * `values()`
    * `items()`
    * `iterkeys()`
    * `itervalues()`
    * `iteritems()`

    The method `_set_data` is semi-public api. You can use it to modify the
    underlying data inside this container if you know what you are doing. The
    method has some additional checks for type and length of the new data and
    should therefore be safer than just modifying the _data member directly.

    Examples
    --------
    >>> m = Mesh(2, 2)
    >>> print m
    [None, None]
    [None, None]
    >>> m[0, 0] = True
    >>> m[1, 1] = True
    >>> print m
    [True, None]
    [None, True]
    >>> m[0, 1] = 'one'
    >>> m[1, 0] = 1
    >>> print m
    [True, 1]
    ['one', True]
    >>> m.values()
    True
    1
    one
    True
    >>> m.keys()
    [(0, 0), (1, 0), (0, 1), (1, 1)]
    """

    def __init__(self,  width, height, data=None):
        self.width = width
        self.height = height

        if data:
            self._set_data(data)
        else:
            self._data = [None] * (self.width * self.height)

    @property
    def shape(self):
        """ Returns a tuple (width, height)
        """
        return (self.width, self.height)

    def _check_index(self, index):
        """ Checks that `index` is inside the boundaries.
        """
        if not 0 <= index[0] < self.width:
            raise IndexError(
                'Mesh indexing error, requested x-coordinate: %i, but width is: %i'
                % (index[0], self.width))
        elif not 0 <= index[1] < self.height:
            raise IndexError(
                'Mesh indexing error, requested y-coordinate: %i, but height is: %i'
                % (index[1], self.height))

    def _index_linear_to_tuple(self, index_linear):
        x = index_linear % self.width
        y = index_linear // self.width
        return (x, y)

    def _index_tuple_to_linear(self, index_tuple):
        self._check_index(index_tuple)
        return index_tuple[0] + index_tuple[1] * self.width

    def _set_data(self, new_data):
        if not isinstance(new_data, list):
            raise TypeError(
                    'The new_data has the wrong type: %s, ' % type(new_data) +\
                    'currently only lists are supported.')
        if len(new_data) != len(self):
            raise ValueError(
                'The new_data has wrong length: %i, expected: %i'
                % (len(new_data), len(self)))

        self._data = new_data

    def __getitem__(self, index):
        return self._data[self._index_tuple_to_linear(index)]

    def __setitem__(self, index, item):
        self._data[self._index_tuple_to_linear(index)] = item

    def __iter__(self):
        return iter(self._index_linear_to_tuple(idx) for idx in range(len(self)))

    def __len__(self):
        return self.width * self.height

    def __repr__(self):
        return ('Mesh(%i, %i, data=%r)'
            % (self.width, self.height, self._data))

    def __str__(self):
        output = str()
        for i in range(self.height):
            start = i * self.width
            end = start + self.width
            output += str(self._data[start:end])
            output += '\n'
        return output

    @property
    def compact_str(self):
        """ Return a compact string representation of the mesh.

        This is useful in case the maze contains components that can be
        represented with single character strings. See the following examples
        for details.

        Non-compact string:

            ['#', '#', '#', '#', '#', '#']
            ['#', ' ', ' ', '#', '0', '#']
            ['#', ' ', '3', ' ', '#', '#']
            ['#', '2', ' ', ' ', '1', '#']
            ['#', '#', '#', '#', '#', '#']

        Compact string:
            ######
            #  #0#
            # 3 ##
            #2  1#
            ######

        Returns
        -------
        compact : str
            compact string representation

        """
        output = str()
        for i in range(self.height):
            start = i * self.width
            end = start + self.width
            output += ''.join([str(i) for i in self._data[start:end]])
            output += '\n'
        return output

    def copy(self):
        return Mesh(self.width, self.height, list(self._data))

class Maze(Mesh):
    """ A Mesh of TypeAwareLists of MazeComponents.

    This is a container class to represent a game maze. It is a two-dimensional
    structure (Mesh) which contains a special list (TypeAwareList) at each
    position. Further each TypeAwareList may contain only MazeComponent.

    """

    def __init__(self, width, height, data=None):
        if not data:
            data = [TypeAwareList() for i in range(width * height)]
        elif any([not isinstance(x, TypeAwareList) for x in data]):
            raise TypeError("Maze keyword argument 'data' should be list of"\
                    "TypeAwareList objects, not: %r" % data)
        super(Maze, self).__init__(width, height, data)

    def has_at(self, type_, pos):
        return type_ in self[pos]

    def get_at(self, type_, pos):
        return self[pos].filter_type(type_)

    def remove_at(self, type_, pos):
        self[pos].remove_type(type_)

    @property
    def positions(self):
        return self.keys()

class MazeComponent(object):
    """ Base class for all items inside a maze. """

    def __str__(self):
        return self.__class__.char

    def __eq__(self, other):
        return isinstance(other, self.__class__)

class TypeAwareList(MutableSequence):
    """ List that is aware of `type`.

    This is a special type of list that knows about the types of its contents
    thus allowing you to check if an object of a certain type is in the list.
    It also allows for specifying a base_class which ensures that all items
    in the list must be instances of this base_class or one of its subclasses.

    It inherits from MutableSequence, thus supporting all the usual operations on list.
    One difference is, that for list equality the `list` method must be called.

    Examples
    --------
    >>> tal = TypeAwareList([Free(), Food()])
    >>> Food in tal
    True
    >>> Food() in tal
    True
    >>> Wall in tal
    False
    >>> Wall() in tal
    False
    >>> tal.index(Food)
    1
    >>> tal.index(Food())
    1
    >>> tal.index(Free)
    0
    >>> tal.index(Free())
    0
    >>> tal = TypeAwareList([1, 2, 3], base_class=int)
    >>> tal.append("string")
    ValueError: Value ''a'' is no instance of base '<type 'int'>'.
    >>> list(tal)
    [1, 2, 3]
    """

    def __init__(self, iterable=None, base_class=None):
        """ Creates a new TypeAwareList which may only contain

        Parameters
        ----------
        iterable : iterable
            Values to insert into the TypeAwareList
        base_class : type
            The base class which all items must be direct or indirect instances of

        """
        if base_class is not None and not inspect.isclass(base_class):
            raise TypeError("Wrong type '%r' for 'base_class'. Need 'type'." % base_class)

        self.base_class = base_class
        self._items = []
        if iterable is not None:
            self.extend(iterable)

    def __getitem__(self, key):
        return self._items[key]

    def __setitem__(self, key, value):
        # checks that value is an instance of self.base_class
        if self.base_class and not isinstance(value, self.base_class):
            raise ValueError("Value '%r' is no instance of base '%r'." % (value, self.base_class))
        self._items[key] = value

    def __delitem__(self, key):
        del self._items[key]

    def insert(self, index, value):
        if self.base_class and not isinstance(value, self.base_class):
            raise ValueError("Value '%r' is no instance of base '%r'." % (value, self.base_class))
        self._items.insert(index, value)

    def __len__(self):
        return len(self._items)

    def __contains__(self, item):
        """ y in x or instance of y in x """
        if inspect.isclass(item):
            return any(isinstance(x, item) for x in self)
        else:
            return item in self._items

    def index(self, item):
        """ L.index(value, [start, [stop]]) -> integer -- return first index of
        value or instance of value"""
        if inspect.isclass(item):
            for i, x in enumerate(self):
                if isinstance(x, item):
                    return i
            raise ValueError("list.index(x): x not in list")
        else:
            return self._items.index(item)

    def filter_type(self, type_):
        """ Returns the subset of self which is an instance of `type_`.

        Returns
        -------
        filtered_items : list
            items which are instances of `type_`
        """
        if not inspect.isclass(type_):
            raise TypeError("Wrong type '%r' for 'filter_type'. Need 'type'." % type_)
        return [item for item in self if isinstance(item, type_)]

    def remove_type(self, type_):
        """ Removes all items which is are instances of `type_`.

        """
        if not inspect.isclass(type_):
            raise TypeError("Wrong type '%r' for 'remove_type'. Need 'type'." % type_)
        for item in self.filter_type(type_):
            self.remove(item)

    def __eq__(self, other):
        return self._items == other._items and self.base_class == other.base_class

    def __repr__(self):
        return 'TypeAwareList(%r, base_class=%r)' % (self._items, self.base_class)

