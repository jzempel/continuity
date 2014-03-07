# -*- coding: utf-8 -*-
"""
    continuity.cli.utils
    ~~~~~~~~~~~~~~~~~~~~

    Continuity command line utilities.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from clint.textui import puts
from curses.ascii import ctrl, CR, EOT, ETX, isctrl, LF
from getch.getch import getch


class cached_property(object):
    """Cached property decorator.

    :param function: The function to decorate.
    """

    def __init__(self, function):
        self.__doc__ = function.__doc__
        self.__module__ = function.__module__
        self.__name__ = function.__name__
        self.function = function
        self.attribute = "_{0}".format(self.__name__)

    def __get__(self, instance, owner):
        """Get the attribute of the given instance.

        :param instance: The instance to get an attribute for.
        :param owner: The instance owner class.
        """
        if not hasattr(instance, self.attribute):
            setattr(instance, self.attribute, self.function(instance))

        return getattr(instance, self.attribute)


def confirm(message, default=False):
    """Prompt for confirmation.

    :param message: The confirmation message.
    :param default: Default `False`.
    """
    if default is True:
        options = "Y/n"
    elif default is False:
        options = "y/N"
    else:
        options = "y/n"

    message = "{0} ({1})".format(message, options)
    ret_val = prompt(message, default=default, characters="YN")

    if ret_val == 'Y':
        ret_val = True
    elif ret_val == 'N':
        ret_val = False

    return ret_val


def prompt(message, default=None, characters=None):
    """Prompt for input.

    :param message: The prompt message.
    :param default: Default `None`. The default input value.
    :param characters: Default `None`. Case-insensitive constraint for single-
        character input.
    """
    if isinstance(default, basestring):
        message = "{0} [{1}]".format(message, default)

    if characters:
        puts("{0} ".format(message), newline=False)
    else:
        message = "{0}: ".format(message)

    while True:
        if characters:
            ret_val = getch()

            if default is not None and ret_val in (chr(CR), chr(LF)):
                puts()
                ret_val = default
                break
            if ret_val in characters.lower() or ret_val in characters.upper():
                puts()

                if ret_val not in characters:
                    ret_val = ret_val.swapcase()

                break
            elif isctrl(ret_val) and ctrl(ret_val) in (chr(ETX), chr(EOT)):
                raise KeyboardInterrupt
        else:
            ret_val = raw_input(message).strip() or default

            if ret_val:
                break

    return ret_val
