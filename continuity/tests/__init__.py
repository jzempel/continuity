# -*- coding: utf-8 -*-
"""
    continuity.tests
    ~~~~~~~~~~~~~~~~

    Continuity test suite.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from ConfigParser import SafeConfigParser
from continuity.cli import main
from continuity.cli.commons import MESSAGES
from continuity.services.git import GitService
from shlex import split
from unittest import TestCase
import os


PARSER = SafeConfigParser()
file_path = os.path.abspath(__file__)
directory_path = os.path.dirname(file_path)
file_name = os.path.join(directory_path, os.pardir, "tests.cfg")
PARSER.read([file_name])


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

    def command(self, line):
        """Execute the given command line.

        :param line: The command line to execute.
        """
        arguments = split(line)
        main(*arguments)

    def get_input(self, message, *args, **kwargs):
        """Get the test-configured input for the given message.

        :param message: The message to get input for.
        :param *args: Argument list.
        :param **kwargs: Keyword-arguments.
        """
        section = self.id()

        for key, value in MESSAGES.iteritems():
            if value == message:
                option = key
                break
        else:
            option = None

        return PARSER.get(section, option)

    def setup(self):
        """Setup this test case.
        """
        key = "GIT_PYTHON_GIT_PATH"
        path = PARSER.get("environment", key)
        self.git = GitService(path)
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
        os.environ[key] = path

    def setUp(self):
        """Delegate to `setup`.
        """
        self.setup()
