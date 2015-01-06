# -*- coding: utf-8 -*-
"""
    continuity.cli.jira
    ~~~~~~~~~~~~~~~~~~~

    Continuity JIRA CLI commands.

    :copyright: 2015 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import (FinishCommand as BaseFinishCommand, GitCommand,
        ReviewCommand as BaseReviewCommand, StartCommand as BaseStartCommand,
        TasksCommand as BaseTasksCommand)
from .utils import edit, less, prompt, puts
from clint.textui import colored, indent
from continuity.services.jira import Issue, JiraException, JiraService
from continuity.services.utils import cached_property
from StringIO import StringIO
from sys import exit


class JiraCommand(GitCommand):
    """Base JIRA command.
    """

    def get_issues(self, status, **parameters):
        """Get a list of issues.

        :param status: A status list to filter by.
        :param parameters: Query field-value parameters.
        """
        parameters["project"] = self.project.key
        parameters["statusCategory"] = status
        jql = "{0} AND issueType in standardIssueTypes() \
                ORDER BY created ASC".format(self.get_jql(**parameters))

        return self.jira.get_issues(jql)

    @staticmethod
    def get_jql(**parameters):
        """Get simple formatted JQL for the given keyword-arguments.

        :param parameters: Query field-value parameters.
        """
        ret_val = ''

        for field, value in parameters.iteritems():
            if value:
                if isinstance(value, basestring):
                    jql = "{0} = \"{1}\"".format(field, value)
                else:
                    formatted = lambda value: "NULL" if value is None \
                        else "'{0}'".format(value)
                    values = [formatted(item) for item in value]
                    jql = "{0} in ({1})".format(field, ','.join(values))

                if ret_val:
                    ret_val = "{0} AND {1}".format(ret_val, jql)
                else:
                    ret_val = jql

        return ret_val

    def get_transition(self, status, do_prompt=False, default=None):
        """Prompt for a transition for the given status.

        :param status: A status to filter transitions by.
        :param do_prompt: Default `False`. Prevent auto-transition.
        :param default: Default `None`. Transition prompt default.
        """
        transition = None
        resolution = None
        transitions = self.jira.get_issue_transitions(self.issue, status)

        if transitions:
            if len(transitions) > 1 or do_prompt:
                characters = ''
                transition_map = {}

                for index, transition in enumerate(transitions):
                    key = str(index + 1)
                    puts("{0}. {1}".format(colored.yellow(key),
                        transition))
                    characters = "{0}{1}".format(characters, key)
                    transition_map[key] = transition

                if default is None:
                    message = "Select transition:"
                else:
                    message = "Select transition (optional):"

                index = prompt(message, default=default, characters=characters)
                transition = transition_map.get(index)
            else:
                transition = transitions[0]

            if transition and transition.resolutions:
                if len(transition.resolutions) > 1:
                    characters = ''
                    resolution_map = {}

                    for index, resolution in enumerate(transition.resolutions):
                        key = str(index + 1)
                        puts("{0}. {1}".format(colored.yellow(key),
                            resolution))
                        characters = "{0}{1}".format(characters, key)
                        resolution_map[key] = resolution

                    if transition.resolution.get("required"):
                        index = prompt("Select resolution:",
                                characters=characters)
                    else:
                        index = prompt("Select resolution (optional):",
                                default=False, characters=characters)

                    resolution = resolution_map.get(index)
                else:
                    resolution = transition.resolutions[0]

        return (transition, resolution)

    @cached_property
    def jira(self):
        """JIRA accessor.
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
                jql = self.get_jql(issue=configuration["issue"])
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

        transition = self.get_value("jira", "finish-transition")

        if transition:
            (self.transition, self.resolution) = self.get_transition(
                Issue.STATUS_COMPLETE)
        else:
            self.transition = None

        if self.transition:
            message = "{0} #{1}".format(self.issue.key, self.transition.slug)
        else:
            message = None

        self.git.merge_branch(branch, message, args)

    def finalize(self):
        """Finalize this finish command.
        """
        if self.transition:
            try:
                self.jira.set_issue_transition(self.issue, self.transition,
                        self.resolution)
            except JiraException:
                pass  # transition may have been set by smart commit.

        puts("Finished issue {0}.".format(self.issue.key))
        super(FinishCommand, self).finalize()


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
            for comment in self.jira.get_comments(self.issue):
                puts()
                puts(colored.yellow("{0} ({1})".format(
                    comment.author.name, comment.created)))
                puts()
                puts(comment)


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
        status = [Issue.STATUS_NEW, Issue.STATUS_IN_PROGRESS]

        if self.namespace.myissues:
            issues = self.get_issues(status, assignee=self.user.name)
        else:
            issues = self.get_issues(status)

        output = StringIO()

        for issue in issues:
            key = colored.yellow(issue.key)
            detail = issue.type.upper()

            if issue.priority:
                detail = "{0} ({1})".format(detail, issue.priority.lower())

            if issue.status_name:
                detail = "{0} [{1}]".format(detail, issue.status_name.upper())

            information = issue.summary

            if issue.assignee:
                information = "{0} ({1})".format(information, issue.assignee)

            message = "{0} {1}: {2}\n".format(key, detail, information)
            output.write(message)

        less(output)


class ReviewCommand(BaseReviewCommand, JiraCommand):
    """Open a GitHub pull request for issue branch review.
    """

    def _create_pull_request(self, branch):
        """Create a pull request.

        :param branch: The base branch the pull request is for.
        """
        url = self.jira.get_issue_url(self.issue)
        self.issue.url = url
        default = self.get_template("pr-title", default=self.issue.summary,
                issue=self.issue)
        title = prompt("Pull request title", default)
        puts("Pull request description (optional):")
        default = self.get_template("pr-description", default=url,
                issue=self.issue)
        description = edit(self.git, default, suffix=".markdown")

        if description:
            with indent(3, quote=" >"):
                puts(description)

        transition = self.get_value("jira", "review-transition")

        if transition:
            (self.transition, self.resolution) = self.get_transition(
                Issue.STATUS_IN_PROGRESS, do_prompt=True, default=False)
        else:
            self.transition = None

        return self.github.create_pull_request(title, description, branch)

    def finalize(self):
        """Finalize this review command.
        """
        if self.transition:
            self.jira.set_issue_transition(self.issue, self.transition,
                    self.resolution)

        super(ReviewCommand, self).finalize()


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
        parser.add_argument("-i", "--ignore", action="store_true",
                help="ignore issue status")
        super(StartCommand, self).__init__(parser, namespace)

    @property
    def error(self):
        """Error message accessor.
        """
        if self.namespace.key and self.namespace.exclusive:
            ret_val = "No available issue {0} found assigned to you.".\
                format(self.namespace.key)

            if not self.namespace.ignore:
                jql = self.get_jql(issue=self.namespace.key,
                    statusCategory=self.status(True), assignee=str(self.user))

                if self.jira.get_issue(jql):
                    ret_val = "{0}\nUse -i to ignore the status on issues assigned to you.".\
                        format(ret_val)
        elif self.namespace.key:
            ret_val = "No available issue {0} found.".format(
                self.namespace.key)

            if not self.namespace.ignore:
                jql = self.get_jql(issue=self.namespace.key,
                    statusCategory=self.status(True))

                if self.jira.get_issue(jql):
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
            puts("Issue: {0}".format(self.issue))

            if self.issue.assignee is None:
                self.issue = self.jira.set_issue_assignee(self.issue,
                        self.user)

            # Verify that user got the issue.
            if self.issue.assignee == self.user:
                (transition, resolution) = self.get_transition(
                    Issue.STATUS_IN_PROGRESS)
                branch = super(StartCommand, self).execute()
                self.git.set_configuration("branch", branch,
                        issue=self.issue.key)

                if transition:
                    self.jira.set_issue_transition(self.issue, transition,
                            resolution)
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

        try:
            id = int(self.namespace.key)
            self.namespace.key = "{0}-{1}".format(self.project.key, id)
        except:
            pass

        key = self.namespace.key
        exclusive = self.namespace.exclusive
        status = self.status(self.namespace.ignore)

        if key and exclusive:
            puts("Retrieving issue {0} from JIRA for {1}...".format(key,
                self.user))
            parameters = {
                "statusCategory": status,
                "issue": key,
                "assignee": str(self.user)
            }
            jql = self.get_jql(**parameters)
            ret_val = self.jira.get_issue(jql)
        elif key:
            puts("Retrieving issue {0} from JIRA...".format(key))
            parameters = {
                "statusCategory": status,
                "issue": key
            }
            jql = self.get_jql(**parameters)
            ret_val = self.jira.get_issue(jql)
        elif exclusive:
            puts("Retrieving next issue from JIRA for {0}...".format(
                self.user))
            issues = self.get_issues(status, assignee=str(self.user))

            if issues:
                ret_val = issues[0]
        else:
            puts("Retrieving next available issue from JIRA...")
            issues = self.get_issues(status, assignee=[self.user, None])

            if issues:
                ret_val = issues[0]

        return ret_val

    @staticmethod
    def status(ignore):
        """Valid issue status list accessor.

        :param ignore: Determine whether to ignore 'in progress' status.
        """
        if ignore:
            ret_val = [Issue.STATUS_NEW, Issue.STATUS_IN_PROGRESS]
        else:
            ret_val = Issue.STATUS_NEW

        return ret_val


class TasksCommand(BaseTasksCommand, JiraCommand):
    """List and manage issue tasks.
    """
    def __init__(self, parser, namespace):
        super(TasksCommand, self).__init__(parser, namespace)
        parser.add_argument("-i", "--indeterminate", metavar="<number>")

    def _get_tasks(self):
        """Task list accessor.
        """
        return self.issue.tasks

    def _get_transition(self, task, status):
        """Prompt for a transition for the given status.

        :param task: A task to get a transition for.
        :param status: A status to filter transitions by.
        """
        issue = self.issue

        try:
            self.issue = task
            ret_val = self.get_transition(status)
        finally:
            self.issue = issue

        return ret_val

    def _set_task(self, task, checked):
        """Task mutator.

        :param task: The task to update.
        :param checked: ``True`` if the task is complete.
        """
        if checked:
            if self.namespace.indeterminate:
                status = Issue.STATUS_IN_PROGRESS
            else:
                status = Issue.STATUS_COMPLETE
        else:
            status = Issue.STATUS_NEW

        (transition, resolution) = self._get_transition(task, status)

        return self.jira.set_issue_transition(task, transition, resolution)

    def execute(self):
        """Execute this tasks command.
        """
        if self.namespace.indeterminate:
            self.namespace.check = self.namespace.indeterminate

        super(TasksCommand, self).execute()

    def finalize(self):
        """Finalize this tasks command.
        """
        for (index, task) in enumerate(self.tasks):
            if task.status == Issue.STATUS_IN_PROGRESS:
                checkmark = '-'
            elif task.status == Issue.STATUS_COMPLETE:
                checkmark = 'x'
            else:
                checkmark = ' '

            message = "[{0}] {1}. {2}".format(checkmark, index + 1,
                    task.summary)
            puts(message)
