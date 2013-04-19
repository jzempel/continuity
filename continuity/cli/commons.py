# -*- coding: utf-8 -*-
"""
    continuity.cli.commons
    ~~~~~~~~~~~~~~~~~~~~~~

    Continuity command line commons.

    :copyright: 2013 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from argparse import ArgumentParser, Namespace as BaseNamespace
from clint.textui import colored, columns, indent, puts, puts_err
from continuity import __version__
from continuity.git import Git, GitException
from continuity.github import GitHub, GitHubException
from continuity.pt import PivotalTracker
from curses.ascii import ctrl, CR, EOT, ETX, isctrl, LF
from getch.getch import getch
from getpass import getpass
from os import chmod, rename
from os.path import exists
from sys import exit


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


class Namespace(BaseNamespace):
    """Continuity argument namespace.

    :param git: Git repository.
    """

    def __init__(self, git, **kwargs):
        super(Namespace, self).__init__(**kwargs)

        self.configuration = git.get_configuration("continuity")

    @property
    def exclusive(self):
        """Determine if continuity is operating in exclusive mode.
        """
        return self.configuration.get("exclusive", False) or \
            getattr(self, "assignedtoyou", False) or \
            getattr(self, "mywork", False)


class GitCommand(object):
    """Base Git command.
    """

    def __call__(self, arguments):
        """Call this command.

        :param arguments: Command-line arguments.
        """
        parser = ArgumentParser()

        try:
            self.initialize(parser)
            namespace = parser.parse_args(arguments.all,
                    namespace=Namespace(self.git))
            self.execute(namespace)
        except (KeyboardInterrupt, EOFError):
            puts()
            self.exit()

        self.finalize()

    def execute(self, namespace):
        """Execute this command.

        :param namespace: Command-line argument namespace.
        """
        raise NotImplementedError

    def exit(self):
        """Handle command exit.
        """
        exit()

    def finalize(self):
        """Finalize this command.
        """
        pass

    def get_section(self, name):
        """Get a git configuration section.

        :param name: The name of the section to retrieve.
        """
        ret_val = self.git.get_configuration(name)

        if not ret_val:
            message = "Missing '{0}' git configuration.".format(name)
            exit(message)

        return ret_val

    def get_value(self, section, key):
        """Get a git configuration value.

        :param section: The configuration section.
        :param key: The key to retrieve a value for.
        """
        configuration = self.get_section(section)

        try:
            ret_val = configuration[key]
        except KeyError:
            message = "Missing '{0}.{1}' git configuration.".format(section,
                    key)
            exit(message)

        return ret_val

    @cached_property
    def git(self):
        """Git accessor.
        """
        try:
            ret_val = Git()
        except GitException:
            puts_err("fatal: Not a git repository.")
            exit(128)

        return ret_val

    def initialize(self, parser):
        """Initialize this command.

        :param parser: Command-line argument parser.
        """
        pass

    @cached_property
    def tracker(self):
        """Configured tracker accessor.
        """
        try:
            configuration = self.git.get_configuration("continuity")

            if configuration:
                ret_val = configuration.get("tracker", "pivotal")
            else:
                ret_val = None
        except GitException:
            ret_val = None

        return ret_val


class GitHubCommand(GitCommand):
    """Base GitHub command.
    """

    def get_issues(self, **parameters):
        """Get a list of issues, ordered by milestone.

        :param parameters: Parameter keyword-arguments.
        """
        ret_val = []
        milestones = self.github.get_milestones()

        for milestone in milestones:
            parameters["milestone"] = milestone.number
            issues = self.github.get_issues(**parameters)
            ret_val.extend(issues)

        parameters["milestone"] = None
        issues = self.github.get_issues(**parameters)
        ret_val.extend(issues)

        return ret_val

    @cached_property
    def github(self):
        """GitHub accessor.
        """
        token = self.get_value("github", "oauth-token")

        return GitHub(self.git, token)

    @cached_property
    def issue(self):
        """Current branch issue accessor.
        """
        configuration = self.git.get_configuration("branch",
                self.git.branch.name)

        if configuration:
            try:
                number = configuration["issue"]
                ret_val = self.github.get_issue(number)
            except KeyError:
                ret_val = None
        else:
            ret_val = None

        if not ret_val:
            exit("fatal: Not an issue branch.")

        return ret_val


class CommitCommand(object):
    """Git prepare commit message hook.
    """

    def __call__(self, arguments):
        """Call this commit command.

        :param arguments: Command-line arguments.
        """
        commit = arguments.get(0)
        git = Git()

        if commit and git.branch:
            configuration = git.get_configuration("branch", git.branch.name)

            if configuration:
                continuity = git.get_configuration("continuity")

                try:
                    if continuity.get("tracker") == "github":
                        number = configuration["issue"]
                    else:
                        number = configuration["story"]

                    with open(commit) as file:
                        message = file.read()

                    message = "[#{0}] {1}".format(number, message)

                    with open(commit, 'w') as file:
                        file.write(message)
                except KeyError:
                    exit()
            else:
                exit()
        else:
            exit()


class FinishCommand(GitCommand):
    """Finish work on a branch.
    """

    def execute(self, namespace):
        """Execute this finish command.

        :param namespace: Command-line argument namespace.
        """
        target = self.get_section("continuity").get("integration-branch")
        arguments = namespace[1]

        try:
            self.git.merge_branch(target, self.message, arguments)
            puts("Merged branch '{0}' into {1}.".format(self.branch,
                self.git.branch.name))
        except GitException, error:
            paths = self.git.repo.index.unmerged_blobs()

            if paths:
                for path in paths:
                    puts_err("Merge conflict: {0}".format(path))
            else:
                self.git.get_branch(self.branch)
                puts_err(error.message)
                exit(error.status)

    def finalize(self):
        """Finalize this finish command.
        """
        try:
            self.git.delete_branch(self.branch)
            puts("Deleted branch {0}.".format(self.branch))
        except GitException:
            exit("conflict: Fix conflicts and then commit the result.")

    def initialize(self, parser):
        """Initialize this finish command.

        :param parser: Command-line argument parser.
        """
        parser.parse_args = parser.parse_known_args
        self.branch = self.git.branch.name
        self.message = None


class HelpCommand(object):
    """Display help for continuity.
    """

    def __call__(self, arguments):
        """Call this help command.

        :param arguments: Command-line arguments.
        """
        puts("usage: continuity [--version]")

        with indent(18):
            puts("[--help]")
            puts("<command> [<args>]")

        command_documentation = {}
        width = 0

        for command, instance in commands.iteritems():
            if isinstance(instance, GitCommand):
                documentation = instance.__doc__.split('\n', 1)[0][:-1]
                command_documentation[command] = documentation
                width = len(command) if len(command) > width else width

        puts()
        puts("The continuity commands are:")

        with indent():
            for command, documentation in sorted(command_documentation.
                    iteritems()):
                puts(columns([command, width + 2], [documentation, None]).
                    rstrip())


class InitCommand(GitCommand):
    """Initialize a git repository for use with continuity.
    """

    def execute(self, namespace):
        """Execute this init command.

        :param namespace: Command-line argument namespace.
        """
        self.git.set_configuration("continuity", **self.continuity)
        self.git.set_configuration("github", **self.github)
        self.git.set_configuration("pivotal", **self.pivotal)
        self.git.set_configuration("alias", **self.aliases)

        if self.pivotal:
            github = GitHub(self.git, self.github["oauth-token"])
            hooks = github.get_hooks()
            token = hooks.get("pivotaltracker", {}).get("config", {}).\
                get("token")

            if not token:
                token = self.pivotal["api-token"]
                github.create_hook("pivotaltracker", token=token)

        filename = "{0}/hooks/prepare-commit-msg".format(self.git.repo.git_dir)

        if exists(filename):
            backup = "{0}.bak".format(filename)

            if not exists(backup):
                rename(filename, backup)

        with open(filename, 'w') as hook:
            hook.write('#!/bin/sh\n\ncontinuity commit "$@"')

        chmod(filename, 0755)

    def exit(self):
        """Handle init command exit.
        """
        puts("Initialization aborted. Changes NOT saved.")
        super(InitCommand, self).exit()

    def finalize(self):
        """Finalize this init command.
        """
        puts()
        puts("Configured git for continuity:")

        with indent():
            for key, value in self.pivotal.iteritems():
                puts("pivotal.{0}={1}".format(key, value))

            for key, value in self.github.iteritems():
                puts("github.{0}={1}".format(key, value))

            for key, value in self.continuity.iteritems():
                if isinstance(value, bool):
                    value = str(value).lower()

                puts("continuity.{0}={1}".format(key, value))

        puts()
        puts("Aliased git commands:")

        with indent():
            for command in sorted(self.aliases.iterkeys()):
                puts(command)

    def initialize(self, parser):
        """Initialize this init command.

        :param parser: Command-line argument parser.
        """
        self.git  # Git repository validation.
        puts("Enter values or accept [defaults] with Enter.")
        puts()
        self.continuity = self.initialize_continuity()

        if self.continuity["tracker"] == "pivotal":
            puts()
            self.pivotal = self.initialize_pivotal()
            name = "continuity.cli.pt"
        else:
            self.pivotal = {}
            name = "continuity.cli.github"

        puts()
        self.github = self.initialize_github()
        commands = common_commands
        module = __import__(name, fromlist=["commands"])
        commands.update(module.commands)
        self.aliases = {}

        for command, instance in commands.iteritems():
            if isinstance(instance, GitCommand):
                alias = "continuity" if command == "init" else command
                self.aliases[alias] = "!continuity {0} \"$@\"".format(command)

    def initialize_continuity(self):
        """Initialize continuity data.
        """
        configuration = self.git.get_configuration("continuity")
        branch = configuration.get("integration-branch", self.git.branch.name)
        branch = prompt("Integration branch", branch)
        tracker = configuration.get("tracker")
        tracker = prompt("Configure for (P)ivotal Tracker or (G)itHub Issues?",
                tracker, characters="PG")

        if tracker == 'P':
            tracker = "pivotal"
        elif tracker == 'G':
            tracker = "github"

        exclusive = configuration.get("exclusive", False)

        if tracker == "github":
            exclusive = confirm("Exclude issues not assigned to you?",
                    default=exclusive)
        else:
            exclusive = confirm("Exclude stories which you do not own?",
                    default=exclusive)

        return {
            "integration-branch": branch,
            "tracker": tracker,
            "exclusive": exclusive
        }

    def initialize_github(self):
        """Initialize github data.
        """
        configuration = self.git.get_configuration("github")
        token = configuration.get("oauth-token")

        if token:
            token = prompt("GitHub OAuth token", token)
        else:
            user = prompt("GitHub user", configuration.get("user"))
            password = getpass("GitHub password: ")
            name = "continuity:{0}".format(self.git.repo.working_dir)
            url = "https://github.com/jzempel/continuity"
            token = GitHub.create_token(user, password, name, url)

            if not token:
                exit("Invalid GitHub credentials.")

        return {"oauth-token": token}

    def initialize_pivotal(self):
        """Initialize pivotal data.
        """
        configuration = self.git.get_configuration("pivotal")
        token = configuration.get("api-token")
        project_id = configuration.get("project-id")
        email = configuration.get("email")
        owner = configuration.get("owner")

        if token:
            token = prompt("Pivotal Tracker API token", token)
        else:
            email = prompt("Pivotal Tracker email", email)
            password = getpass("Pivotal Tracker password: ")
            token = PivotalTracker.get_token(email, password)

            if not token:
                exit("Invalid Pivotal Tracker credentials.")

        pt = PivotalTracker(token)
        projects = pt.get_projects()

        if projects:
            if not project_id:
                for project in projects:
                    message = "{0} - {1}".format(colored.yellow(project.id),
                            project.name)
                    puts(message)

            project_id = prompt("Pivotal Tracker project ID", project_id)
            project = pt.get_project(project_id)

            if project:
                try:
                    password
                except NameError:
                    email = prompt("Pivotal Tracker email", email)

                for member in project.members:
                    if member.email == email:
                        owner = member.name
                        break
                else:
                    exit("Invalid project member email.")
            else:
                exit("Invalid project ID.")
        else:
            exit("No Pivotal Tracker projects found.")

        return {
            "api-token": token,
            "project-id": project_id,
            "email": email,
            "owner": owner,
        }


class ReviewCommand(GitHubCommand):
    """Open a GitHub pull request for branch review.
    """

    def execute(self, namespace):
        """Execute this review command.

        :param namespace: Command-line argument namespace.
        """
        puts("Creating pull request...")

        try:
            self.git.push_branch()
            self.pull_request = self.github.create_pull_request(
                self.title_or_number, self.description, self.branch)
        except GitHubException:
            exit("Unable to create pull request.")

    def exit(self):
        """Handle review command exit.
        """
        puts("Aborted branch review.")
        super(ReviewCommand, self).exit()

    def finalize(self):
        """Finalize this review command.
        """
        puts("Opened pull request: {0}".format(self.pull_request.url))

    def initialize(self, parser):
        """Initialize this review command.

        :param parser: Command-line argument parser.
        """
        self.branch = self.get_value("continuity", "integration-branch")
        self.description = None
        self.title_or_number = None


class StartCommand(GitCommand):
    """Start work on a branch.
    """

    def execute(self, namespace):
        """Execute this start command.

        :param namespace: Command-line argument namespace.
        """
        if self.branch == self.git.branch.name:
            name = prompt("Enter branch name")
            ret_val = '-'.join(name.split())

            try:
                self.git.create_branch(ret_val)
                puts("Switched to a new branch '{0}'".format(ret_val))
            except GitException, e:
                exit(e)
        else:
            message = "error: Attempted start from non-integration branch; switch to '{0}'."  # NOQA
            exit(message.format(self.branch))

        return ret_val

    def initialize(self, parser):
        """Initialize this start command.

        :param parser: Command-line argument parser.
        """
        self.branch = self.get_value("continuity", "integration-branch")


class VersionCommand(object):
    """Display the version of continuity.
    """

    def __call__(self, arguments):
        """Call this version command.

        :param arguments: Command-line arguments.
        """
        message = "continuity version {0}".format(__version__)
        puts(message)


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


common_commands = {
    "--help": HelpCommand(),
    "--version": VersionCommand(),
    "commit": CommitCommand(),
    "finish": FinishCommand(),
    "init": InitCommand(),
    "review": ReviewCommand(),
    "start": StartCommand(),
}
commands = common_commands.copy()
