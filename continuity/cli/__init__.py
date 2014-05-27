# -*- coding: utf-8 -*-
"""
    continuity.cli
    ~~~~~~~~~~~~~~

    Continuity command line interface.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import get_commands
from argparse import (ArgumentParser as BaseArgumentParser,
        HelpFormatter as BaseHelpFormatter,
        Namespace as BaseNamespace, PARSER, SUPPRESS)
from continuity.services.git import GitException, GitService
from sys import argv
import continuity


class ArgumentParser(BaseArgumentParser):
    """Continuity argument parser.

    :param *args: Argument list.
    :param **kwargs: Keyword arguments.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("add_help", False)
        super(ArgumentParser, self).__init__(*args, **kwargs)
        self.add_argument("-h", "--help", action="help", help=SUPPRESS)


class HelpFormatter(BaseHelpFormatter):
    """Continuity help formatter.

    :param *args: Argument list.
    :param **kwargs: Keyword arguments.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_help_position", 18)
        super(HelpFormatter, self).__init__(*args, **kwargs)

    def _format_args(self, action, default_metavar):
        """Format action arguments.

        :param action: The action to format arguments for.
        :param default_metavar: Default action display name.
        """
        if action and action.nargs == PARSER:
            # Replace subparser list.
            ret_val = "[--version] [--help]\n{0}<command> [<args>]".format(
                ' ' * 18)
        else:
            ret_val = super(HelpFormatter, self)._format_args(action,
                    default_metavar)

        return ret_val

    def _join_parts(self, part_strings):
        """Join the given part strings.

        :param part_strings: The part strings to join.
        """
        if part_strings:
            part_string = part_strings[0]

            if part_string and part_string.strip().startswith('{'):
                # Remove redundant subparser list.
                part_strings = part_strings[1:]

        return super(HelpFormatter, self)._join_parts(part_strings)


class Namespace(BaseNamespace):
    """Continuity argument namespace.
    """

    @property
    def exclusive(self):
        """Determine if continuity is operating in exclusive mode.
        """
        ret_val = getattr(self, "assignedtoyou", False) or \
            getattr(self, "myissues", False) or \
            getattr(self, "mywork", False)

        if ret_val is False:
            try:
                git = GitService()
                configuration = git.get_configuration("continuity")
                ret_val = configuration.get("exclusive", False)
            except GitException:
                pass

        return ret_val


def main(*args):
    """Main entry point.

    :param *args: Optional command-argument list.
    """
    parser = ArgumentParser(prog=continuity.__name__,
            formatter_class=HelpFormatter)

    for action_group in parser._action_groups:
        if "positional" in action_group.title:
            action_group.title = "The {0} commands are".format(parser.prog)
            break

    subparsers = parser.add_subparsers()
    namespace = Namespace()
    commands = get_commands()

    for command_name in sorted(commands.iterkeys()):
        command_class = commands[command_name]
        help = command_class._help()

        if help is not SUPPRESS:
            kwargs = {"help": help}
        else:
            kwargs = {}

        subparser = subparsers.add_parser(command_name, **kwargs)
        command = command_class(subparser, namespace)
        subparser.set_defaults(command=command)

    version = "%(prog)s version {0}".format(continuity.__version__)
    parser.add_argument("--version", action="version", help=SUPPRESS,
            version=version)
    arguments = args or argv[1:] or ["--help"]
    parser.parse_args(arguments, namespace=namespace)
    namespace.command()
