# -*- coding: utf-8 -*-
"""
    continuity.services.utils
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Continuity service utilities.

    :copyright: 2015 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from dateutil.parser import parse


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


class datetime_property(object):
    """Date/time property decorator.

    :param function: The function to decorate.
    """

    def __init__(self, function):
        self.function = function

    def __get__(self, instance, owner):
        """Attribute accessor - converts a GitHub date/time value into a Python
        datetime object.

        :param instance: The instance to get an attribute for.
        :param owner: The owner class.
        """
        try:
            value = self.function(instance)
            ret_val = parse(value).replace(microsecond=0)
        except AttributeError:
            ret_val = None

        return ret_val
