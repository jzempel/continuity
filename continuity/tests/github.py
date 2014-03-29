# -*- coding: utf-8 -*-
"""
    continuity.tests.github
    ~~~~~~~~~~~~~~~~~~~~~~~

    Continuity GitHub tests.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from . import ContinuityTestCase


class GitHubCommandTestCase(ContinuityTestCase):
    """Base GitHub command test case.
    """

    def setup(self):
        """Setup this test case.
        """
        super(GitHubCommandTestCase, self).setup()
        continuity = {
            "exclusive": self.configuration["github_exclusive"],
            "tracker": "github",
            "integration-branch": self.configuration[
                "continuity_integration_branch"]
        }
        self.git.set_configuration("continuity", **continuity)
        github = {"oauth-token": self.github.token}
        self.git.set_configuration("github", **github)


class IssuesCommandTestCase(GitHubCommandTestCase):
    """Issues command test case.
    """

    def test_issues(self):
        """issues: list open GitHub issues.
        """
        self.command("issues")

    def test_user_issues(self):
        """issues: list open GitHub issues assigned to you.
        """
        self.command("issues --assignedtoyou")
