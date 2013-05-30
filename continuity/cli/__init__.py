# -*- coding: utf-8 -*-
"""
    continuity.cli
    ~~~~~~~~~~~~~~

    Continuity command line interface.

    :copyright: 2013 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import get_commands
from continuity import __version__
from argparse import ArgumentParser, Namespace as BaseNamespace
from continuity.git import Git, GitException
from sys import argv


class Namespace(BaseNamespace):
    """Continuity argument namespace.
    """

    @property
    def exclusive(self):
        """Determine if continuity is operating in exclusive mode.
        """
        ret_val = getattr(self, "assignedtoyou", False) or \
            getattr(self, "mywork", False)

        if ret_val is False:
            try:
                git = Git()
                configuration = git.get_configuration("continuity")
                ret_val = configuration.get("exclusive", False)
            except GitException:
                pass

        return ret_val


def main():
    """Main entry point.
    """
    parser = ArgumentParser(prog="continuity")
    version = "continuity version {0}".format(__version__)
    parser.add_argument("--version", action="version", version=version)
    namespace = Namespace()
    subparsers = parser.add_subparsers()

    for command_class in get_commands().itervalues():
        try:
            getattr(command_class, "help")
        except AttributeError:
            help = command_class.__doc__.split('\n', 1)[0][:-1]

        subparser = subparsers.add_parser(command_class.name, help=help)
        command = command_class(subparser, namespace)
        subparser.set_defaults(command=command)

    arguments = argv[1:] or ["--help"]
    parser.parse_args(arguments, namespace=namespace)
    namespace.command()
