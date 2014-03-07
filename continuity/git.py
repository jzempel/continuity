# -*- coding: utf-8 -*-
"""
    continuity.git
    ~~~~~~~~~~~~~~

    Git API.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import
from ConfigParser import NoSectionError
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.repo.base import Repo
from os import environ
from sys import exc_info


class GitException(Exception):
    """Base git exception.

    :param message: Exception message.
    :param status: Default `None`. Exception status.
    """

    def __init__(self, message, status=None):
        super(GitException, self).__init__(message)
        self.status = status


class Git(object):
    """Git service.

    :param path: Default `None`. The path to the git repository. Defaults to
        the current directory.
    """

    def __init__(self, path=None):
        self.git = environ.get("GIT_PYTHON_GIT_EXECUTABLE", "git")

        try:
            self.repo = Repo(path)
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

    def create_branch(self, name, push=True):
        """Create the given branch name.

        :param name: The name of the branch to create.
        :param push: Default `True`. Determine whether to push to remote.
        """
        command = [self.git, "checkout", "-b", str(name)]

        try:
            ret_val = self.repo.git.execute(command)
        except GitCommandError:
            ret_val = self.get_branch(name)

        if push:
            self.push_branch()

        return ret_val

    def delete_branch(self, name):
        """Delete the given branch name.

        :param name: The name of the branch to delete.
        """
        command = [self.git, "branch", "-d", str(name)]

        try:
            ret_val = self.repo.git.execute(command)
        except GitCommandError, error:
            exception = GitException(error.stderror, error.status)

            raise exception, None, exc_info()[2]

        return ret_val

    def get_branch(self, name):
        """Get the given branch name.

        :param name: The name of the branch to checkout.
        """
        command = [self.git, "checkout", str(name)]

        try:
            ret_val = self.repo.git.execute(command)
        except GitCommandError:
            raise GitException("Invalid branch"), None, exc_info()[2]

        return ret_val

    def get_configuration(self, section, subsection=None):
        """Get the git configuration for the given section.

        :param section: The git configuration section to retrieve.
        :param subsection: Default `None`. Optional subsection.
        """
        ret_val = {}
        reader = self.repo.config_reader()

        if subsection:
            section = '{0} "{1}"'.format(section, subsection)

        try:
            for name, value in reader.items(section):
                if value == "true":
                    value = True
                elif value == "false":
                    value = False

                ret_val[name] = value
        except NoSectionError:
            pass

        return ret_val

    def merge_branch(self, name, message=None, arguments=None):
        """Merge the given branch name into the current branch.

        :param name: The name of the branch to merge.
        :param message: Default `None`. An optional message to prepend to the
            merge message.
        :param arguments: Default `None`. List of arguments to pass to
            git-merge.
        """
        command = [self.git, "merge", name]

        if arguments:
            command.extend(arguments)

        if message:
            message = "{0} Merge branch '{1}' into {2}".format(message, name,
                    self.branch.name)
            command.extend(["--no-ff", "-m", message])

        try:
            ret_val = self.repo.git.execute(command)
        except GitCommandError, error:
            exception = GitException(error.stderr, error.status)

            raise exception, None, exc_info()[2]

        return ret_val

    def push_branch(self, name=None):
        """Push the given branch name.

        :param name: Default `None`. The name of the branch to push.
        """
        if name:
            self.get_branch(name)

        remote = self.repo.remotes.origin
        command = [self.git, "push", remote.name, self.branch.name]

        try:
            ret_val = self.repo.git.execute(command)
        except GitCommandError, error:
            exception = GitException(error.stderr, error.status)

            raise exception, None, exc_info()[2]

        return ret_val

    @property
    def remote(self):
        """Remote accessor.
        """
        try:
            remote = self.repo.remotes.origin
            remote_reference = remote.refs[self.branch.name]
            ret_val = self.repo.remotes[remote_reference.remote_name]
        except IndexError:
            ret_val = None

        return ret_val

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
