# -*- coding: utf-8 -*-
"""
    continuity.cli.jira
    ~~~~~~~~~~~~~~~~~~~

    Continuity Jira CLI commands.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import (FinishCommand as BaseFinishCommand, GitCommand,
        ReviewCommand as BaseReviewCommand, StartCommand as BaseStartCommand)
from .utils import less
from clint.textui import colored
from continuity.services.jira import JiraService
from continuity.services.utils import cached_property
from StringIO import StringIO


class JiraCommand(GitCommand):
    """Base Jira command.
    """

    @cached_property
    def jira(self):
        """Jira accessor.
        """
        token = self.get_value("jira", "auth-token")
        base = self.get_value("jira", "url")

        return JiraService(base, token)

    @cached_property
    def issue(self):
        """Current branch issue accessor.
        """
        configuration = self.git.get_configuration("branch",
                self.git.branch.name)

        if configuration:
            try:
                id = configuration["issue"]
                ret_val = self.jira.get_issue(id)
            except KeyError:
                ret_val = None
        else:
            ret_val = None

        if not ret_val:
            exit("fatal: Not an issue branch.")

        return ret_val

    @cached_property
    def project(self):
        """Project accessor.
        """
        key = self.get_value("jira", "project-key")

        return self.jira.get_project(key)


class FinishCommand(BaseFinishCommand, JiraCommand):
    """Finish an issue branch.
    """


class IssueCommand(JiraCommand):
    """Display issue branch information.
    """

    name = "issue"


class IssuesCommand(JiraCommand):
    """List open issues.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "issues"

    def __init__(self, parser, namespace):
        parser.add_argument("-m", "--myissues", action="store_true",
                help="list issues assigned to you")
        super(IssuesCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this issues command.
        """
        jql = "project = {0} AND \
                statusCategory != Complete AND \
                issueType in standardIssueTypes() \
                ORDER BY created ASC".format(self.project.key)

        if self.namespace.myissues:
            jql = "{0} {1}".format("assignee = currentUser() AND", jql)

        issues = self.jira.get_issues(jql)
        output = StringIO()

        for issue in issues:
            key = colored.yellow(issue.key)
            type = issue.type.upper()
            information = issue.summary

            if issue.assignee:
                information = "{0} ({1})".format(information, issue.assignee)

            message = "{0} {1}: {2}\n".format(key, type, information)
            output.write(message)

        less(output)


class ReviewCommand(BaseReviewCommand, JiraCommand):
    """Open a GitHub pull request for issue branch review.
    """


class StartCommand(BaseStartCommand, JiraCommand):
    """Start a branch linked to a story.
    """
