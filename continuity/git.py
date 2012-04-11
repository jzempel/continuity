# -*- coding: utf-8 -*-
"""
    git
    ~~~

    Git API.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import
from ConfigParser import NoSectionError
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.repo.base import Repo
from sys import exc_info


class GitException(Exception):
    """Base git exception.
    """


class Git(object):
    """Git service.

    :param path: Default `None`. The path to the git repository. Defaults to
        the current directory.
    """

    def __init__(self, path=None):
        try:
            self.repo = Repo(path)
        except (InvalidGitRepositoryError, NoSuchPathError):
            raise GitException("Invalid path"), None, exc_info()[2]

    @property
    def branch(self):
        """Branch accessor.
        """
        return self.repo.head.ref

    def create_branch(self, name, push=True):
        """Create the given branch name.

        :param name: The name of the branch to checkout.
        :param push: Default `True`. Determine whether to push to remote.
        """
        try:
            command = ["git", "checkout", "-b", str(name)]
            ret_val = self.repo.git.execute(command)
        except GitCommandError:
            command = ["git", "checkout", str(name)]
            ret_val = self.repo.git.execute(command)

        if push:
            remote = self.repo.remotes.origin
            command = ["git", "push", remote.name, self.branch.name]
            self.repo.git.execute(command)

        return ret_val

    def get_configuration(self, section):
        """Get the git configuration for the given section.

        :param section: The git configuration section to retrieve.
        """
        ret_val = {}
        reader = self.repo.config_reader()

        try:
            for name, value in reader.items(section):
                ret_val[name] = value
        except NoSectionError:
            ret_val = None

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
