# -*- coding: utf-8 -*-
"""
    continuity.tests.commons
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Continuity test commons.

    :copyright: 2015 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from . import ContinuityTestCase


class InitCommandTestCase(ContinuityTestCase):
    """Initialize command test case.
    """

    def test_new_github(self):
        """init: new GitHub configuration.
        """
        self.command("init --new", continuity_tracker='G')
        configuration = self.git.get_configuration("continuity")
        self.assert_equal(configuration["tracker"], "github")
        self.assert_false(configuration["exclusive"])
        configuration = self.git.get_configuration("github")
        self.assert_in("oauth-token", configuration)
        configuration = self.git.get_configuration("alias")
        self.assert_in("issue", configuration)
        self.assert_in("issues", configuration)

    def test_new_pivotal(self):
        """init: new Pivotal Tracker configuration.
        """
        self.github.remove_hook("pivotaltracker")
        self.command("init --new", continuity_tracker='P')
        configuration = self.git.get_configuration("continuity")
        self.assert_equal(configuration["tracker"], "pivotal")
        self.assert_false(configuration["exclusive"])
        configuration = self.git.get_configuration("pivotal")
        self.assert_in("api-token", configuration)
        configuration = self.git.get_configuration("alias")
        self.assert_in("backlog", configuration)
        self.assert_in("story", configuration)
        hooks = self.github.get_hooks()
        self.assert_in("pivotaltracker", hooks)

    def test_re_github(self):
        """init: re-configure for GitHub.
        """
        self.command("init --new", continuity_tracker='G')
        configuration = self.git.get_configuration("github")
        user = configuration["user"]
        self.command("init", github_user=None)
        configuration = self.git.get_configuration("github")
        self.assert_equal(user, configuration["user"])

    def test_re_pivotal(self):
        """init: re-configure for Pivotal Tracker.
        """
        self.command("init --new", continuity_tracker='P')
        configuration = self.git.get_configuration("pivotal")
        email = configuration["email"]
        self.command("init", pivotal_password=None)
        configuration = self.git.get_configuration("pivotal")
        self.assert_equal(email, configuration["email"])

    def test_refresh_github(self):
        """init: refresh GitHub configuration.
        """
        self.command("init", continuity_tracker='G')
        configuration = self.git.get_configuration("github")
        token = configuration["oauth-token"]
        self.command("init --new", continuity_tracker='G',
                github_oauth_token=None)
        configuration = self.git.get_configuration("github")
        self.assert_equal(token, configuration["oauth-token"])

    def test_refresh_pivotal(self):
        """init: refresh Pivotal Tracker configuration.
        """
        self.command("init", continuity_tracker='P')
        configuration = self.git.get_configuration("pivotal")
        token = configuration["api-token"]
        self.command("init --new", continuity_tracker='P',
                pivotal_api_token=None)
        configuration = self.git.get_configuration("pivotal")
        self.assert_equal(token, configuration["api-token"])
