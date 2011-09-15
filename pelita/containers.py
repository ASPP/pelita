# -*- coding: utf-8 -*-

""" Advanced container classes. """

from collections import Mapping, MutableSequence
from .messaging.json_convert import serializable

import sys
import inspect

__docformat__ = "restructuredtext"


@serializable
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

    def _check_index(self, index):
        """ Checks that `index` is inside the boundaries.

        Parameters
        ----------
        index : tuple of (int, int)
            index (x, y) into the Mesh

        Raises
        ------
        IndexError
            if the index is not within the range of the Mesh

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

        """
        self._check_index(index_tuple)
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

    def _to_json_dict(self):
        return {"width": self.width,
                "height": self.height,
                "data": list(self._data)}

    @classmethod
    def _from_json_dict(cls, item):
        return cls(**item)

@serializable
class TypeAwareList(MutableSequence):
    """ List that is aware of `type`.

    Parameters
    ----------
    iterable : iterable, optional, default=None
        Values to insert into the TypeAwareList
    base_class : type, , optional, default=None
        The base class which all items must be direct or indirect instances of

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
        if base_class is not None and not inspect.isclass(base_class):
            raise TypeError("Wrong type '%r' for 'base_class'. Need 'type'."
                    % base_class)

        self.base_class = base_class
        self._items = []
        if iterable is not None:
            self.extend(iterable)

    def __getitem__(self, key):
        return self._items[key]

    def __setitem__(self, key, value):
        # checks that value is an instance of self.base_class
        if self.base_class and not isinstance(value, self.base_class):
            raise ValueError("Value '%r' is no instance of base '%r'."
                    % (value, self.base_class))
        self._items[key] = value

    def __delitem__(self, key):
        del self._items[key]

    def insert(self, index, value):
        if self.base_class and not isinstance(value, self.base_class):
            raise ValueError("Value '%r' is no instance of base '%r'."
                    % (value, self.base_class))
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
            raise TypeError("Wrong type '%r' for 'filter_type'. Need 'type'."
                    % type_)
        return [item for item in self if isinstance(item, type_)]

    def remove_type(self, type_):
        """ Removes all items which is are instances of `type_`.

        """
        if not inspect.isclass(type_):
            raise TypeError("Wrong type '%r' for 'remove_type'. Need 'type'."
                    % type_)
        for item in self.filter_type(type_):
            self.remove(item)

    def __eq__(self, other):
        return (type(self) == type(other) and
                self._items == other._items and
                self.base_class == other.base_class)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        if self.base_class is None:
            bc = None
        else:
            bc = self.base_class.__name__
        return ('TypeAwareList(%r, base_class=%s)'
            % (self._items, bc))

    def _to_json_dict(self):
        if self.base_class is None:
            base_class_json = None
        else:
            base_class_json = [self.base_class.__module__, self.base_class.__name__]
        return {"iterable": list(self._items),
                "base_class": base_class_json}

    @classmethod
    def _from_json_dict(cls, item):
        # we need to do this in order to serialise a type
        base_class = item["base_class"]
        if base_class is None:
            return cls(**item)

        module, class_name = base_class
        # look up the type, if it is registered
        item["base_class"] = getattr(sys.modules[module], class_name)
        return cls(**item)

