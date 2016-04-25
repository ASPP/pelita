""" Advanced container classes. """

from collections import Mapping


class Mesh(Mapping):
    """ A mapping from a two-dimensional coordinate system into object space.

    Using a list of lists to represent a matrix is memory inefficient, slow,
    (ugly) and requires much effort to keep all lists the same length.  Instead
    we store the matrix data in a single list and provide accessor and mutator
    methods (`__getitem__()` and `__setitem__()`) to access the elements in a
    matrixy style.

    Parameters
    ----------
    width : int
        desired width for Mesh
    height : int
        desired height for Mesh
    data : list, optional
        If given, will try to set this as contents, using the width and height.
        May raise a `ValueError` or a `TypeError`, see `_set_data()` for
        details.

    Attributes
    ----------
    shape : (int, int)
        tuple of width and height

    Notes
    -----
    Once the container has been allocated, it cannot be resized.

    The container can store arbitrary type objects and even mix types.

    The constructor will preallocate a container with an appropriate shape, and
    populate this with `None`.

    The container cannot be sliced.

    The items are stored row-based (C-order).

    Since this container inherits from `collections.Mapping` you can use
    methods similar to those of the dictionary:

    * `keys()`
    * `values()`
    * `items()`
    * `iterkeys()`
    * `itervalues()`
    * `iteritems()`

    The method `_set_data()` is semi-public API. You can use it to modify the
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
        """ The shape (width, height) of the Mesh.

        Returns
        -------
        shape : tuple of (int, int)
            shape of the Mesh
        """
        return (self.width, self.height)

    def __contains__(self, index):
        return 0 <= index[0] < self.width and 0 <= index[1] < self.height

    def _index_linear_to_tuple(self, index_linear):
        """ Convert a linear index to a tuple.

        Parameters
        ----------
        index_linear : int
            index into the underlying list

        Returns
        -------
        index_tuple : tuple of (int, int)
            index in two dimensional space (x, y)

        """
        x = index_linear % self.width
        y = index_linear // self.width
        return (x, y)

    def _index_tuple_to_linear(self, index_tuple):
        """ Convert a tuple index to linear index

        Parameters
        ----------
        index_tuple : tuple of (int, int)
            index in two dimensional space (x, y)

        Returns
        -------
        index_linear : int
            index into the underlying list

        Raises
        ------
        KeyError
            if the index is not within the range of the Mesh

        """
        if index_tuple not in self:
            raise KeyError(
                'Mesh indexing error, requested coordinate: %r, but size is: (%i, %i)'
                % (index_tuple, self.width, self.height))

        return index_tuple[0] + index_tuple[1] * self.width

    def _set_data(self, new_data):
        """ Set the underlying data for this container.

        Parameters
        ----------
        new_data : list of appropriate length
            the new data

        Raises
        ------
        TypeError
            if new_data is not a list
        ValueError
            if new_data has inappropriate length

        """
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
        return iter(self._index_linear_to_tuple(idx)
                for idx in range(len(self)))

    def __len__(self):
        return self.width * self.height

    def __repr__(self):
        return ('%s(%i, %i, data=%r)'
            % (self.__class__.__name__, self.width, self.height, self._data))

    def __str__(self):
        output = str()
        for i in range(self.height):
            start = i * self.width
            end = start + self.width
            output += str(self._data[start:end])
            output += '\n'
        return output

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.width == other.width and
                self.height == other.height and
                self._data == other._data)

    def __ne__(self, other):
        return not (self == other)

    @property
    def compact_str(self):
        """ Return a compact string representation of the Mesh.

        This is useful in case the maze contains components that can be
        represented with single character strings. See the following examples
        for details.

        Non-compact string::

            ['#', '#', '#', '#', '#', '#']
            ['#', ' ', ' ', '#', '0', '#']
            ['#', ' ', '3', ' ', '#', '#']
            ['#', '2', ' ', ' ', '1', '#']
            ['#', '#', '#', '#', '#', '#']

        Compact string::

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

    def _to_json_dict(self):
        return {"width": self.width,
                "height": self.height,
                "data": list(self._data)}

    @classmethod
    def _from_json_dict(cls, item):
        return cls(**item)
