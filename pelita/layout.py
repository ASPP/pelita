# -*- coding: utf-8 -*-

""" Maze layout parsing. """
import random

from .containers import Mesh
from . import __layouts

__docformat__ = "restructuredtext"


class LayoutEncodingException(Exception):
    """ Signifies a problem with the encoding of a layout. """
    pass

def get_random_layout(filter=''):
    """ Return a random layout string from the available ones.

    Parameters
    ----------
    filter : str
        only return layouts which contain "filter" in their name.
        Default is no filter.

    Returns
    -------
    layout : str
        a random layout string

    Examples
    --------
    To only get layouts without dead ends you may use:

        >>> get_random_layout(filter='without_dead_ends')

    """
    layouts_names = [item for item in get_available_layouts() if filter in item]
    layout_choice = random.choice(layouts_names)
    return get_layout_by_name(layout_choice)

def get_available_layouts(filter=''):
    """ The names of the available layouts.

    Parameters
    ----------
    filter : str
        only return layouts which contain 'filter' in their name.
        Default is no filter.

    Returns
    -------
    layout_names : list of str
        the available layouts

    Examples
    --------
    To only get layouts without dead ends you may use:

        >>> get_available_layouts(filter='without_dead_ends')

    """
    # loop in layouts dictionary and look for layout strings
    return [item for item in dir(__layouts) if item.startswith('layout_') and
            filter in item]

def get_layout_by_name(layout_name):
    """ Get a layout.

    Parameters
    ----------
    layout_name : str
        a valid layout name

    Returns
    -------
    layout_str : str
        the layout as a string

    Raises
    ------
    KeyError
        if the layout_name is not known

    See Also
    --------
    get_available_layouts
    """
    # decode and return this layout
    try:
        return __layouts.__dict__[layout_name].decode('base64').decode('zlib')
    except KeyError, ke:
        # This happens if layout_name is not a valid key in the __dict__.
        # I.e. if the layout_name is not available.
        # The error message would be to terse "KeyError: 'non_existing_layout'",
        # thus reraise as ValueError with appropriate error message.
        raise ValueError("Layout: '%s' is not known." % ke.args)


class Layout(object):
    """ Auxiliary class to parse string encodings of mazes.

    Basically a parser for string encoded maze representations. This class can
    strip such strings, determine the maze shape, check their validity based on
    set of legal encoding characters and covert to a `Mesh`.

    When initialised through the constructor we first strip leading and trailing
    whitespace (mainly space and newline chars). Then we perform several check
    on the data to see if it is rectangular, if it contains the correct number of
    bot_positions and if it is composed of legal characters only. Lastly you can
    use `as_mesh()` to convert the layout into a Mesh of characters.

    The class provides much of its functionality via staticmethods so that reuse
    of these code-parts is easy if needed. Also you can subclass it in case you
    need additional checks for example for mazes that need to be not only
    rectangular, but also square.

    Parameters
    ----------
    layout_str : str
        the layout to work on
    layout_chars : list of str
        the list of legal characters
    number_bots : int
        the number of bots to look for

    Attributes
    ----------
    layout_chars : list of str
        the list of legal characters to use
    stripped : str
        the whitespace stripped version
    shape : tuple of two ints
        height and width of the layout

    """
    def __init__(self, layout_str, layout_chars, number_bots):
        self.number_bots = number_bots
        self.layout_chars = layout_chars
        self.stripped = self.strip_layout(layout_str)
        self.check_layout(self.stripped, self.layout_chars, self.number_bots)
        self.shape = self.layout_shape(self.stripped)

    @staticmethod
    def strip_layout(layout_str):
        """ Remove leading and trailing whitespace from a string encoded layout.

        Parameters
        ----------
        layout_str : str
            the layout, possibly with whitespace

        Returns
        -------
        layout_str : str
            the layout with whitespace removed

        """
        return '\n'.join([line.strip() for line in layout_str.split('\n')]).strip()

    @staticmethod
    def check_layout(layout_str, layout_chars, number_bots):
        """ Check the legality of the layout string.

        Parameters
        ----------
        layout_str : str
            the layout string
        number_bots : int
            the total number of bots that should be present

        Raises
        ------
        LayoutEncodingException
            if an illegal character is encountered
        LayoutEncodingException
            if a bot-id is missing
        LayoutEncodingException
            if a bot-id is specified twice

        """
        bot_ids = [str(i) for i in range(number_bots)]
        existing_bots = []
        legal = layout_chars + bot_ids + ['\n']
        for c in layout_str:
            if c not in legal:
                raise LayoutEncodingException(
                    "Char: '%c' is not a legal layout character" % c)
            if c in bot_ids:
                if c in existing_bots:
                    raise LayoutEncodingException(
                        "Bot-ID: '%c' was specified twice" % c)
                else:
                    existing_bots.append(c)
        existing_bots.sort()
        if bot_ids != existing_bots:
            missing = [str(i) for i in set(bot_ids).difference(set(existing_bots))]
            missing.sort()
            raise LayoutEncodingException(
                'Layout is invalid for %i bots, The following IDs were missing: %s '
                % (number_bots, missing))
        lines = layout_str.split('\n')
        for i in range(len(lines)):
            if len(lines[i]) != len(lines[0]):
                raise LayoutEncodingException(
                    'The layout must be rectangular, ' +\
                    'line %i has length %i instead of %i'
                    % (i, len(lines[i]), len(lines[0])))

    @staticmethod
    def layout_shape(layout_str):
        """ Determine shape of layout.

        Parameters
        ----------
        layout_str : str
            a checked and stripped layout string

        Returns
        -------
        width : int
        height : int

        """
        return (layout_str.find('\n'), len(layout_str.split('\n')))

    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return self.stripped

    def __repr__(self):
        return ("Layout(%r, %s, %i)"
            % (self.stripped, self.layout_chars, self.number_bots))

    def as_mesh(self):
        """ Convert to a Mesh.

        Returns
        -------
        mesh : Mesh
            this layout as a Mesh

        """
        mesh = Mesh(*self.shape)
        mesh._set_data(list(''.join(self.stripped.split('\n'))))
        return mesh

    @classmethod
    def from_file(cls, filename, layout_chars, number_bots):
        """ Loads a layout from file `filename`.

        Parameters
        ----------
        filename : str
            the file with the saved layout
        layout_chars : list of str
            the list of legal characters
        number_bots : int
            the number of bots to look for
        """
        with open(filename) as file:
            lines = file.read()
        return cls(lines, layout_chars=layout_chars, number_bots=number_bots)

