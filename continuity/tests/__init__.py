# -*- coding: utf-8 -*-
"""
    continuity.tests
    ~~~~~~~~~~~~~~~~

    Continuity test suite.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from ConfigParser import SafeConfigParser, NoSectionError
from continuity.cli import main
from continuity.cli.commons import MESSAGES
from continuity.services.git import GitService
from continuity.services.github import GitHubService
from continuity.services.utils import cached_property
from mock import DEFAULT, patch
from shlex import split
from unittest import TestCase
import os
import re


class ConfigParser(SafeConfigParser):
    """Custom configuration parser that handles option list values.
    """

    def get(self, section, option, raw=False, vars=None, index=-1):
        """Get a configuration value.

        :param section: The section to get a value from.
        :param option: The option value to get.
        :param raw: Default ``False``. Determine if % interpolations are
            expanded.
        :param vars: A preferred dictionary of option-values.
        :param index: Default ``-1``. The index of the item to get from a list
            of values. By default, the option value or list (if multiple
            values are configured) is returned.
        """
        ret_val = SafeConfigParser.get(self, section, option, raw, vars)

        if vars is None or option not in vars:
            lines = ret_val.splitlines()
            ret_val = filter(None, (line.strip() for line in lines))

            if index >= 0:
                ret_val = ret_val[index]
            elif len(ret_val) == 1:
                ret_val = ret_val[0]

        return ret_val


PARSER = ConfigParser()
file_path = os.path.abspath(__file__)
directory_path = os.path.dirname(file_path)
file_names = [
    os.path.join(directory_path, os.pardir, "tests.cfg"),
    os.path.join(directory_path, os.pardir, ".tests.cfg"),
    os.path.join(os.path.expanduser('~'), ".continuity.cfg")
]
PARSER.read(file_names)


class ContinuityTestCase(TestCase):
    """Base continuity test case.
    """

    def assert_equal(self, a, b, message=None):
        """Delegate to `assertEqual`.
        """
        return self.assertEqual(a, b, message)

    def assert_false(self, x, message=None):
        """Delegate to `assertFalse`.
        """
        return self.assertFalse(x, message)

    def assert_in(self, a, b, message=None):
        """Delegate to `assertIn`.
        """
        return self.assertIn(a, b, message)

    def assert_is(self, a, b, message=None):
        """Delegate to `assertIs`.
        """
        return self.assertIs(a, b, message)

    def assert_is_none(self, x, message=None):
        """Delegate to `assertIsNone`.
        """
        return self.assertIsNone(x, message)

    def assert_is_not(self, a, b, message=None):
        """Delegate to `assertIsNot`.
        """
        return self.assertIsNot(a, b, message)

    def assert_is_not_none(self, x, message=None):
        """Delegate to `assertIsNotNone`.
        """
        return self.assertIsNotNone(x, message)

    def assert_not_in(self, a, b, message=None):
        """Delegate to `assertNotIn`.
        """
        return self.assertNotIn(a, b, message)

    def assert_true(self, x, message=None):
        """Delegate to `assertTrue`.
        """
        return self.assertTrue(x, message)

    def command(self, line, **input):
        """Execute the given command line.

        :param line: The command line to execute.
        :param **input: Message key-value input to the command prompts.
        """
        def get_input(message, *args, **kwargs):
            section = self.id()

            for key, value in MESSAGES.iteritems():
                if value == message:
                    option = key
                    break
            else:
                option = None

            vars = self.configuration
            vars.update(input)

            return PARSER.get(section, option, vars=vars,
                    index=self.command_count)

        arguments = split(line)

        with patch.multiple("continuity.cli.commons", confirm=DEFAULT,
                prompt=DEFAULT, puts=DEFAULT) as mocks:
            mocks["confirm"].side_effect = get_input
            mocks["prompt"].side_effect = get_input
            main(*arguments)

        self.command_count += 1

    @property
    def configuration(self):
        """Get the configuration for this test case.
        """
        try:
            items = PARSER.items(self.id())
            ret_val = dict(items)
        except NoSectionError:
            ret_val = {}

        for section in ("continuity", "github", "pivotal"):
            configuration = self.git.get_configuration(section)

            for key, value in configuration.iteritems():
                suffix = '_'.join(re.split(r"\.|\-", key))
                key = "{0}_{1}".format(section, suffix)
                ret_val[key] = value

        return ret_val

    @cached_property
    def git(self):
        """Get the git service instance for this test case.
        """
        path = PARSER.get("DEFAULT", GitService.KEY_GIT_PATH)
        os.environ[GitService.KEY_GIT_PATH] = path

        if os.path.exists(path):
            origin = None
        else:
            name = os.path.basename(path)
            user = PARSER.get("DEFAULT", "github_user")
            repository = GitHubService.create_repository(self.token, name,
                    user)
            origin = repository["clone_url"]

        return GitService(path, origin=origin)

    @cached_property
    def github(self):
        """Get the github service instance for this test case.
        """
        return GitHubService(self.git, self.token)

    def setup(self):
        """Setup this test case.
        """
        options = [
            "backlog",
            "continuity",
            "finish",
            "issue",
            "issues",
            "review",
            "start",
            "story",
            "tasks"
        ]
        self.git.remove_configuration("alias", None, *options)
        self.git.remove_configuration("continuity")
        self.git.remove_configuration("github", None, "oauth-token")
        options = ["api-token", "email", "owner-id", "project-id"]
        self.git.remove_configuration("pivotal", None, *options)
        self.command_count = 0

    def setUp(self):
        """Delegate to `setup`.
        """
        self.setup()

    @cached_property
    def token(self):
        """Get the GitHub token for this test case.
        """
        user = PARSER.get("DEFAULT", "github_user")
        password = PARSER.get("DEFAULT", "github_password")
        path = PARSER.get("DEFAULT", GitService.KEY_GIT_PATH)
        name = "continuity:{0}".format(path)
        url = "https://github.com/{0}/{1}".format(user, os.path.basename(path))

        return GitHubService.create_token(user, password, name, url=url)
