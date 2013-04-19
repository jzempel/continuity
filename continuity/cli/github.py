# -*- coding: utf-8 -*-
"""
    continuity.cli.github
    ~~~~~~~~~~~~~~~~~~~~~

    Continuity GitHub CLI commands.

    :copyright: 2013 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import (cached_property, FinishCommand as BaseFinishCommand,
        GitHubCommand, ReviewCommand as BaseReviewCommand,
        StartCommand as BaseStartCommand)
from clint.textui import colored, puts
from continuity.github import Issue
from pydoc import pipepager
from StringIO import StringIO
from sys import exit


class FinishCommand(BaseFinishCommand, GitHubCommand):
    """Finish an issue branch.
    """

    def finalize(self):
        """Finalize this finish command.
        """
        self.github.add_labels(self.issue, "finished")
        self.github.remove_label(self.issue, "started")
        puts("Finished issue #{0:d}.".format(self.issue.number))
        super(FinishCommand, self).finalize()

    def initialize(self, parser):
        """Initialize this finish command.

        :param parser: Command-line argument parser.
        """
        super(FinishCommand, self).initialize(parser)
        self.message = "[close #{0:d}]".format(self.issue.number)


class IssueCommand(GitHubCommand):
    """Display issue branch information.
    """

    def execute(self, namespace):
        """Execute this issue command.

        :param namespace: Command-line argument namespace.
        """
        puts(self.issue.title)

        if self.issue.milestone:
            puts()
            puts("Milestone: {0}".format(self.issue.milestone))

        if self.issue.description:
            puts()
            puts(colored.cyan(self.issue.description))

        puts()
        puts(colored.white("Created by {0} on {1}".format(
            self.issue.user.login,
            self.issue.created.strftime("%d %b %Y, %I:%M%p"))))
        puts(colored.white(self.issue.url))


class IssuesCommand(GitHubCommand):
    """List open issues.
    """

    def execute(self, namespace):
        """Execute this issues command.

        :param namespace: Command-line argument namespace.
        """
        if namespace.assignedtoyou:
            user = self.github.get_user()
            issues = self.get_issues(assignee=user.login)
        else:
            issues = self.get_issues()

        output = StringIO()

        for issue in issues:
            number = colored.yellow(str(issue.number))

            if "started" in issue.labels:
                title = "{0} [STARTED]".format(issue.title)
            elif "finished" in issue.labels:
                title = "{0} [FINISHED]".format(issue.title)
            else:
                title = issue.title

            information = issue.assignee

            if information:
                if issue.milestone:
                    information = "{0}, {1}".format(information,
                            issue.milestone)
            else:
                information = issue.milestone

            if information:
                title = "{0} ({1})".format(title, information)

            message = "{0}: {1}\n".format(number, title.strip())
            output.write(message)

        pipepager(output.getvalue(), cmd="less -FRSX")

    def initialize(self, parser):
        """Initialize this issues command.

        :param parser: Command-line argument parser.
        """
        parser.add_argument("-u", "--assignedtoyou", action="store_true",
                help="list issues assigned to you")


class ReviewCommand(BaseReviewCommand):
    """Open a GitHub pull request for issue branch review.
    """

    def initialize(self, parser):
        """Initialize this review command.

        :param parser: Command-line argument parser.
        """
        super(ReviewCommand, self).initialize(parser)
        self.title_or_number = self.issue.number


class StartCommand(BaseStartCommand, GitHubCommand):
    """Start a branch linked to an issue.
    """

    def execute(self, namespace):
        """Execute this start command.

        :param namespace: Command-line argument namespace.
        """
        self.namespace = namespace

        if self.issue:
            puts("Issue: {0}".format(self.issue.title))
            user = self.github.get_user()

            if self.issue.assignee is None:
                self.issue = self.github.set_issue(self.issue.number,
                        assignee=user.login)

            # Verify that user got the issue.
            if self.issue.assignee == user:
                branch = super(StartCommand, self).execute(namespace)
                self.git.set_configuration("branch", branch,
                        issue=self.issue.number)
                self.github.add_labels(self.issue, "started")
            else:
                exit("Unable to update issue assignee.")
        else:
            if namespace.number and namespace.exclusive:
                exit("No available issue #{0} found assigned to you.".format(
                    namespace.number))
            elif namespace.number:
                exit("No available issue #{0} found.".format(namespace.number))
            elif namespace.exclusive:
                exit("No available issues found assigned to you.")
            else:
                exit("No available issues found.")

    def exit(self):
        """Handle start command exit.
        """
        puts("Aborted issue branch.")
        super(StartCommand, self).exit()

    def initialize(self, parser):
        """Initialize this start command.

        :param parser: Command-line argument parser.
        """
        parser.add_argument("-n", "--number", help="start the specified issue",
                type=int)
        parser.add_argument("-u", "--assignedtoyou", action="store_true",
                help="only start issues assigned to you")
        super(StartCommand, self).initialize(parser)

    @cached_property
    def issue(self):
        """Target issue accessor.
        """
        ret_val = None
        available = lambda issue: issue and \
            issue.state == Issue.STATE_OPEN and \
            not("started" in issue.labels or "finished" in issue.labels) and \
            issue.pull_request.url is None
        number = self.namespace.number
        exclusive = self.namespace.exclusive
        user = self.github.get_user()

        if number and exclusive:
            puts("Retrieving issue #{0} from GitHub for {1}...".format(number,
                user))
            issue = self.github.get_issue(number)

            if available(issue) and issue.assignee and issue.assignee == user:
                ret_val = issue
        elif number:
            puts("Retrieving issue #{0} from GitHub...".format(number))
            issue = self.github.get_issue(number)

            if available(issue):
                ret_val = issue
        elif exclusive:
            puts("Retrieving next issue from GitHub for {0}...".format(user))
            issues = self.get_issues(assignee=user.login)

            if issues:
                for issue in issues:
                    if available(issue):
                        ret_val = issue
                        break
        else:
            puts("Retrieving next available issue from GitHub...")
            issues = self.get_issues()

            for issue in issues:
                if available(issue) and (issue.assignee is None or
                        issue.assignee == user):
                    ret_val = issue
                    break

        return ret_val


commands = {
    "finish": FinishCommand(),
    "issue": IssueCommand(),
    "issues": IssuesCommand(),
    "review": ReviewCommand(),
    "start": StartCommand()
}
