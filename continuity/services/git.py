# -*- coding: utf-8 -*-
"""
    continuity.services.git
    ~~~~~~~~~~~~~~~~~~~~~~~

    Git API.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import
from .commons import ServiceException
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.repo.base import Repo
from os import environ, utime
from os.path import basename, exists, expanduser, join
from sys import exc_info
import re


PATTERN_SUBSECTION = re.compile(r"^(?P<section>.+)\s+\"(?P<subsection>.+)\"$",
        re.U)


class GitException(ServiceException):
    """Base git exception.

    :param message: Exception message.
    :param status: Default `None`. Exception status.
    """

    def __init__(self, message, status=None):
        super(GitException, self).__init__(message)
        self.status = status


class GitRepository(Repo):
    """Git repository.
    """

    config_level = ("system", "user", "global", "repository")

    def _get_config_path(self, config_level):
        """Override to support the "user" configuration level until
           `https://github.com/gitpython-developers/GitPython/issues/160` is
           fixed.

        :param config_level: The configuration level to get a path for.
        """
        if config_level == "user":
            config_home = environ.get("XDG_CONFIG_HOME") or join(environ.get(
                "HOME", '~'), ".config")
            ret_val = expanduser(join(config_home, "git", "config"))
        else:
            ret_val = super(GitRepository, self)._get_config_path(config_level)

        return ret_val


class GitService(object):
    """Git service.

    :param path: Default `None`. The path to the git repository. Defaults to
        the current directory.
    :param origin: Default `None`. The remote origin URL.
    """

    KEY_GIT_PATH = "CONTINUITY_GIT_PATH"

    def __init__(self, path=None, origin=None):
        self.git = environ.get("GIT_PYTHON_GIT_EXECUTABLE", "git")
        path = path or environ.get(GitService.KEY_GIT_PATH)
        mkdir = path is not None and not exists(path)

        try:
            if mkdir:
                self.repo = Repo.init(path)
                name = join(path, ".gitignore")

                with file(name, 'a'):
                    utime(name, None)

                self.execute("add", basename(name))
                self.execute("commit", "-m", "Initial commit")
            else:
                self.repo = GitRepository(path)

            if origin:
                try:
                    self.repo.create_remote("origin", origin)
                except GitCommandError:
                    self.execute("remote", "set-url",
                            self.repo.remotes.origin.name, origin)

                if mkdir:
                    self.execute("push", "-u", self.repo.remotes.origin.name,
                            self.branch.name)
        except (InvalidGitRepositoryError, NoSuchPathError):
            raise GitException("Invalid path"), None, exc_info()[2]

    @property
    def branch(self):
        """Branch accessor.
        """
        head = self.repo.head

        if head.is_detached:
            ret_val = None
        else:
            ret_val = head.ref

        return ret_val

    @property
    def configuration(self):
        """Configuration dictionary accessor.
        """
        ret_val = {}
        reader = self.repo.config_reader()

        for section in reader.sections():
            for name, value in reader.items(section):
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

                match = re.match(PATTERN_SUBSECTION, section)

                if match:
                    ret_val.setdefault(match.group("section"), {}).setdefault(
                        match.group("subsection"), {})[name] = value
                else:
                    ret_val.setdefault(section, {})[name] = value

        return ret_val

    def create_branch(self, name, push=True):
        """Create the given branch name.

        :param name: The name of the branch to create.
        :param push: Default `True`. Determine whether to push to remote.
        """
        try:
            ret_val = self.execute("checkout", "-b", str(name))
        except GitCommandError:
            ret_val = self.get_branch(name)

        if push:
            self.push_branch()

            if not self.remote:
                raise GitException("Invalid remote")

        return ret_val

    def delete_branch(self, name):
        """Delete the given branch name.

        :param name: The name of the branch to delete.
        """
        try:
            ret_val = self.execute("branch", "-d", str(name))
        except GitCommandError, error:
            traceback = exc_info()[2]

            raise GitException(error.stderr, error.status), None, traceback

        return ret_val

    @property
    def editor(self):
        """Get the configured git editor.
        """
        return self.execute("var", "GIT_EDITOR")

    def execute(self, *args):
        """Execute the given git command.

        :param *args: Command argument list.
        """
        command = [self.git] + list(args)

        return self.repo.git.execute(command)

    def get_branch(self, name):
        """Get the given branch name.

        :param name: The name of the branch to checkout.
        """
        try:
            ret_val = self.execute("checkout", str(name))
        except GitCommandError, error:
            traceback = exc_info()[2]

            raise GitException(error.stderr, error.status), None, traceback

        return ret_val

    def get_configuration(self, section, subsection=None):
        """Get the git configuration for the given section.

        :param section: The git configuration section to retrieve.
        :param subsection: Default `None`. Optional subsection.
        """
        ret_val = self.configuration.get(section, {})

        if subsection:
            ret_val = ret_val.get(subsection, {})

        for name, value in ret_val.items():
            if value == "true":
                value = True
            elif value == "false":
                value = False

            ret_val[name] = value

        return ret_val

    def merge_branch(self, name, message=None, arguments=None):
        """Merge the given branch name into the current branch.

        :param name: The name of the branch to merge.
        :param message: Default `None`. An optional message to prepend to the
            merge message.
        :param arguments: Default `None`. List of arguments to pass to
            git-merge.
        """
        command = ["merge", name]

        if arguments:
            command.extend(arguments)

        if message:
            message = "{0} Merge branch '{1}' into {2}".format(message, name,
                    self.branch.name)
            command.extend(["--no-ff", "-m", message])

        try:
            ret_val = self.execute(*command)
        except GitCommandError, error:
            traceback = exc_info()[2]

            raise GitException(error.stderr, error.status), None, traceback

        return ret_val

    def prune_branches(self):
        """Prune stale remote branches.
        """
        return self.execute("remote", "prune", self.repo.remotes.origin.name)

    def push_branch(self, name=None):
        """Push the given branch name.

        :param name: Default `None`. The name of the branch to push.
        """
        if name:
            self.get_branch(name)

        remote = self.repo.remotes.origin

        try:
            ret_val = self.execute("push", remote.name, self.branch.name)
        except GitCommandError, error:
            traceback = exc_info()[2]

            raise GitException(error.stderr, error.status), None, traceback

        return ret_val

    @property
    def remote(self):
        """Remote accessor.
        """
        if self.repo.remotes:
            try:
                remote = self.repo.remotes.origin
                remote_reference = remote.refs[self.branch.name]
                ret_val = self.repo.remotes[remote_reference.remote_name]
            except (AssertionError, IndexError):
                ret_val = None
        else:
            ret_val = None

        return ret_val

    def remove_configuration(self, section, subsection=None, *options):
        """Remove the git configuration data.

        :param section: The git configuration section to remove from.
        :param subsection: Default `None`. Optional subsection.
        :param *options: A list of options to remove. If empty, then remove
            the entire section.
        """
        writer = self.repo.config_writer()

        if subsection:
            section = '{0} "{1}"'.format(section, subsection)

        if writer.has_section(section):
            if options:
                for option in options:
                    writer.remove_option(section, option)
            else:
                writer.remove_section(section)

    def set_configuration(self, section, subsection=None, **kwargs):
        """Set the git configuration data for the given section.

        :param section: The git configuration section to update.
        :param subsection: Default `None`. Optional subsection.
        :param kwargs: Configuration option-value pairs.
        """
        writer = self.repo.config_writer()

        if subsection:
            section = '{0} "{1}"'.format(section, subsection)

        if not writer.has_section(section):
            writer.add_section(section)

        for option, value in kwargs.items():
            if value is True or value is False:
                value = str(value).lower()

            writer.set(section, option, value)
