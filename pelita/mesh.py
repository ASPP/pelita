from collections import Mapping

__docformat__ = "restructuredtext"

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
        if type(new_data) != list:
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
        for i in range(self.width):
            start = i * self.height
            end = start + self.height
            output += str(self._data[start:end])
            output += '\n'
        return output

    def copy(self):
        return Mesh(self.width, self.height, list(self._data))
