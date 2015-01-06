# -*- coding: utf-8 -*-
"""
    continuity.cli.github
    ~~~~~~~~~~~~~~~~~~~~~

    Continuity GitHub CLI commands.

    :copyright: 2015 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import (FinishCommand as BaseFinishCommand,
        GitHubCommand as BaseGitHubCommand,
        ReviewCommand as BaseReviewCommand, StartCommand as BaseStartCommand,
        TasksCommand as BaseTasksCommand)
from .utils import less, puts
from clint.textui import colored
from continuity.services.github import Issue
from continuity.services.utils import cached_property
from StringIO import StringIO
from sys import exit


class GitHubCommand(BaseGitHubCommand):
    """Base GitHub command.
    """

    def get_issues(self, **parameters):
        """Get a list of issues, ordered by milestone.

        :param parameters: Parameter keyword-arguments.
        """
        ret_val = []
        milestones = self.github.get_milestones()

        for milestone in milestones:
            parameters["milestone"] = milestone.number
            issues = self.github.get_issues(**parameters)
            ret_val.extend(issues)

        parameters["milestone"] = None
        issues = self.github.get_issues(**parameters)
        ret_val.extend(issues)

        return ret_val

    @cached_property
    def issue(self):
        """Current branch issue accessor.
        """
        configuration = self.git.get_configuration("branch",
                self.git.branch.name)

        if configuration:
            try:
                number = configuration["issue"]
                ret_val = self.github.get_issue(number)
            except KeyError:
                ret_val = None
        else:
            ret_val = None

        if not ret_val:
            exit("fatal: Not an issue branch.")

        return ret_val


class FinishCommand(BaseFinishCommand, GitHubCommand):
    """Finish an issue branch.
    """

    def _merge_branch(self, branch, *args):
        """Merge a branch.

        :param branch: The name of the branch to merge.
        :param *args: Merge argument list.
        """
        try:
            self.git.get_branch(branch)
            self.issue  # Cache the branch issue.
        finally:
            self.git.get_branch(self.branch)

        message = "[close #{0:d}]".format(self.issue.number)
        self.git.merge_branch(branch, message, args)

    def finalize(self):
        """Finalize this finish command.
        """
        self.github.add_labels(self.issue, "finished")
        self.github.remove_label(self.issue, "started")
        puts("Finished issue #{0:d}.".format(self.issue.number))
        super(FinishCommand, self).finalize()


class IssueCommand(GitHubCommand):
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

        if self.namespace.comments:
            for comment in self.github.get_comments(self.issue):
                puts()
                puts(colored.yellow("{0} ({1})".format(
                    comment.user.login, comment.created)))
                puts()
                puts(comment)


class IssuesCommand(GitHubCommand):
    """List open issues.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "issues"

    def __init__(self, parser, namespace):
        parser.add_argument("-u", "--assignedtoyou", action="store_true",
                help="list issues assigned to you")
        super(IssuesCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this issues command.
        """
        if self.namespace.assignedtoyou:
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

        less(output)


class ReviewCommand(BaseReviewCommand, GitHubCommand):
    """Open a GitHub pull request for issue branch review.
    """

    def _create_pull_request(self, branch):
        """Create a pull request.

        :param branch: The base branch the pull request is for.
        """
        return self.github.create_pull_request(self.issue.number,
                branch=branch)


class StartCommand(BaseStartCommand, GitHubCommand):
    """Start a branch linked to an issue.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    def __init__(self, parser, namespace):
        parser.add_argument("number", help="start the specified issue",
                nargs='?', type=int)
        parser.add_argument("-u", "--assignedtoyou", action="store_true",
                help="only start issues assigned to you")
        parser.add_argument("-i", "--ignore", action="store_true",
                help="ignore issue status")
        super(StartCommand, self).__init__(parser, namespace)

    @property
    def error(self):
        """Error message accessor.
        """
        if self.namespace.number and self.namespace.exclusive:
            ret_val = "No available issue #{0} found assigned to you.".\
                format(self.namespace.number)

            if not self.namespace.ignore:
                issue = self.github.get_issue(self.namespace.number)

                if issue and issue.state == Issue.STATE_OPEN and \
                        issue.assignee == self.github.get_user():
                    ret_val = "{0}\nUse -i to ignore the status on issues assigned to you.".\
                        format(ret_val)
        elif self.namespace.number:
            ret_val = "No available issue #{0} found.".format(
                self.namespace.number)

            if not self.namespace.ignore:
                issue = self.github.get_issue(self.namespace.number)

                if issue and issue.state == Issue.STATE_OPEN:
                    ret_val = "{0}\nUse -i to ignore issue status.".format(
                        ret_val)
        elif self.namespace.exclusive:
            ret_val = "No available issues found assigned to you."
        else:
            ret_val = "No available issues found."

        return ret_val

    def execute(self):
        """Execute this start command.
        """
        if self.issue:
            puts("Issue: {0}".format(self.issue.title))
            user = self.github.get_user()

            if self.issue.assignee is None:
                self.issue = self.github.set_issue(self.issue.number,
                        assignee=user.login)

            # Verify that user got the issue.
            if self.issue.assignee == user:
                branch = super(StartCommand, self).execute()
                self.git.set_configuration("branch", branch,
                        issue=self.issue.number)
                self.github.add_labels(self.issue, "started")
            else:
                exit("Unable to update issue assignee.")
        else:
            exit(self.error)

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
        available = lambda issue: issue and \
            issue.state == Issue.STATE_OPEN and \
            (self.namespace.ignore or not("started" in issue.labels or "finished" in issue.labels)) and \
            issue.pull_request is None
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


class TasksCommand(BaseTasksCommand, GitHubCommand):
    """List and manage issue tasks.
    """

    def _get_tasks(self):
        """Task list accessor.
        """
        return self.github.get_tasks(self.issue)

    def _set_task(self, task, checked):
        """Task mutator.

        :param task: The task to update.
        :param checked: ``True`` if the task is complete.
        """
        return self.github.set_task(self.issue, task, checked)

    def finalize(self):
        """Finalize this tasks command.
        """
        for index, task in enumerate(self.tasks):
            checkmark = 'x' if task.is_checked else ' '
            message = "[{0}] {1}. {2}".format(checkmark, index + 1,
                    task.description)
            puts(message)
