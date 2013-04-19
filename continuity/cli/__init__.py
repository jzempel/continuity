# -*- coding: utf-8 -*-
"""
    continuity.cli
    ~~~~~~~~~~~~~~

    Continuity command line interface.

    :copyright: 2013 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import commands
from .github import commands as github_commands
from .pt import commands as pivotal_commands
from clint import args
from clint.textui import puts_err
from continuity.git import Git, GitException
from sys import exit


def main():
    """Main entry point.
    """
    command = args.get(0) or "--help"

    try:
        git = Git()
        configuration = git.get_configuration("continuity")

        if configuration:
            tracker = configuration.get("tracker", "pivotal")

            if tracker == "github":
                commands.update(github_commands)
            elif tracker == "pivotal":
                commands.update(pivotal_commands)
    except GitException:
        pass

    if command in commands:
        args.remove(command)
        commands[command](args)
    else:
        message = "continuity: '{0}' is not a continuity command. See 'continuity --help'."  # NOQA
        puts_err(message.format(command))
        exit(1)
