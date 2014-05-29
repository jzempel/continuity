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
from .utils import less, prompt
from clint.textui import colored, puts
from continuity.services.jira import Issue, JiraService
from continuity.services.utils import cached_property
from StringIO import StringIO


class JiraCommand(GitCommand):
    """Base Jira command.
    """

    def get_issues(self, **parameters):
        """Get a list of issues.

        :param parameters: Query field-value parameters.
        """
        jql = "project = {0} AND \
                statusCategory = {1} AND \
                issueType in standardIssueTypes() \
                ORDER BY created ASC".format(self.project.key,
                        Issue.STATUS_NEW)

        for field, value in parameters.iteritems():
            jql = "{0} = {1} AND {2}".format(field, value, jql)

        return self.jira.get_issues(jql)

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
                jql = "issue = {0}".format(configuration["issue"])
                ret_val = self.jira.get_issue(jql)
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

    @cached_property
    def user(self):
        """User accessor.
        """
        name = self.get_value("jira", "user")

        return self.jira.get_user(name)


class FinishCommand(BaseFinishCommand, JiraCommand):
    """Finish an issue branch.
    """


class IssueCommand(JiraCommand):
    """Display issue branch information.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "issue"

    def __init__(self, parser, namespace):
        parser.add_argument("-c", "--comments", action="store_true",
                help="include issue comments")
        super(IssueCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this issue command.
        """
        puts(self.issue.summary)

        if self.issue.description:
            puts()
            puts(colored.cyan(self.issue.description))

        puts()
        puts(colored.white("Created by {0} on {1}".format(
            self.issue.creator,
            self.issue.created.strftime("%d %b %Y, %I:%M%p"))))
        puts(colored.white(self.jira.get_issue_url(self.issue)))

        if self.namespace.comments:
            for comment in self.github.get_comments(self.issue):
                puts()
                puts(colored.yellow("{0} ({1})".format(
                    comment.user.login, comment.created)))
                puts()
                puts(str(comment))


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
        if self.namespace.myissues:
            issues = self.get_issues(assignee="currentUser()")
        else:
            issues = self.get_issues()

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

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    def __init__(self, parser, namespace):
        parser.add_argument("key", help="start the specified issue",
                nargs='?')
        parser.add_argument("-m", "--myissues", action="store_true",
                help="only start issues assigned to me")
        super(StartCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this start command.
        """
        if self.issue:
            puts("Issue: {0}".format(self.issue))

            if self.issue.assignee is None:
                self.issue = self.jira.set_issue_assignee(self.issue,
                        self.user)

            # Verify that user got the issue.
            if self.issue.assignee == self.user:
                transitions = self.jira.get_issue_transitions(self.issue,
                        Issue.STATUS_IN_PROGRESS)

                if transitions:
                    if len(transitions) > 1:
                        characters = ''
                        transition_map = {}

                        for index, transition in enumerate(transitions):
                            key = str(index + 1)
                            puts("{0}. {1}".format(colored.yellow(key),
                                transition))
                            characters = "{0}{1}".format(characters, key)
                            transition_map[key] = transition

                        index = prompt("Select transition:",
                                characters=characters)
                        transition = transition_map[index]
                    else:
                        transition = transitions[0]
                else:
                    transition = None

                branch = super(StartCommand, self).execute()
                self.git.set_configuration("branch", branch,
                        issue=self.issue.key)

                if transition:
                    self.jira.set_issue_transition(self.issue, transition)
            else:
                exit("Unable to update issue assignee.")
        else:
            if self.namespace.key and not self.namespace.key.startswith(
                    self.project.key):
                exit("No issue {0} found in project {1}.".format(
                    self.namespace.key, self.project))
            if self.namespace.key and self.namespace.exclusive:
                exit("No available issue {0} found assigned to you.".format(
                    self.namespace.key))
            elif self.namespace.key:
                exit("No available issue {0} found.".format(
                    self.namespace.key))
            elif self.namespace.exclusive:
                exit("No available issues found assigned to you.")
            else:
                exit("No available issues found.")

    def exit(self):
        """Handle start command exit.
        """
        puts("Aborted issue branch.")
        super(StartCommand, self).exit()

    @cached_property
    def issue(self):
        """Target issue accessor.
        """
        ret_val = None

        try:
            id = int(self.namespace.key)
            self.namespace.key = "{0}-{1}".format(self.project.key, id)
        except:
            pass

        key = self.namespace.key
        exclusive = self.namespace.exclusive

        if key and exclusive:
            puts("Retrieving issue {0} from Jira for {1}...".format(key,
                self.user))
            jql = "project = {0} AND \
                    statusCategory = {1} AND \
                    issue = {2} AND \
                    assignee = {3}".format(
                self.project.key, Issue.STATUS_NEW, key, self.user)
            ret_val = self.jira.get_issue(jql)
        elif key:
            puts("Retrieving issue {0} from Jira...".format(key))
            jql = "project = {0} AND \
                    statusCategory = {1} AND \
                    issue = {2}".format(
                self.project.key, Issue.STATUS_NEW, key)
            ret_val = self.jira.get_issue(jql)
        elif exclusive:
            puts("Retrieving next issue from Jira for {0}...".format(
                self.user))
            issues = self.get_issues(assignee=self.user)

            if issues:
                ret_val = issues[0]
        else:
            puts("Retrieving next available issue from Jira...")
            issues = self.get_issues()

            if issues:
                ret_val = issues[0]

        return ret_val
