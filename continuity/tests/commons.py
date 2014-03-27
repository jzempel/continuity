# -*- coding: utf-8 -*-
"""
    continuity.tests.commons
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Continuity test commons.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from . import ContinuityTestCase
from mock import DEFAULT, patch


class InitCommandTestCase(ContinuityTestCase):
    """Initialize command test cases.
    """

    def test_new_github(self):
        """init: new GitHub configuration.
        """
        with patch.multiple("continuity.cli.commons", confirm=DEFAULT,
                prompt=DEFAULT, puts=DEFAULT) as mocks:
            mocks["confirm"].side_effect = self.get_input
            mocks["prompt"].side_effect = self.get_input
            self.command("init --new")

        configuration = self.git.get_configuration("continuity")
        self.assert_equal(configuration["tracker"], "github")
        self.assert_false(configuration["exclusive"])
        configuration = self.git.get_configuration("github")
        self.assert_in("oauth-token", configuration)
