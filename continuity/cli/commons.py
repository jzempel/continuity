# -*- coding: utf-8 -*-
"""
    continuity.cli.commons
    ~~~~~~~~~~~~~~~~~~~~~~

    Continuity command line commons.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .utils import confirm, prompt, render
from argparse import REMAINDER, SUPPRESS
from clint.textui import colored, indent, puts, puts_err
from continuity.services.commons import ServiceException
from continuity.services.git import GitException, GitService
from continuity.services.github import (GitHubException,
        GitHubRequestException, GitHubService)
from continuity.services.jira import JiraService
from continuity.services.pt import PivotalTrackerService
from continuity.services.utils import cached_property
from os import chmod, rename
from os.path import exists
from requests.exceptions import ConnectionError
from sys import exit


MESSAGES = {
    "continuity_integration_branch": "Integration branch",
    "continuity_tracker": "Configure for (G)itHub Issues, (J)ira, or (P)ivotal Tracker?",  # NOQA
    "git_branch": "Enter branch name",
    "github_2fa_code": "GitHub two-factor authentication code",
    "github_exclusive": "Exclude issues not assigned to you?",
    "github_oauth_token": "GitHub OAuth token",
    "github_password": "GitHub password",
    "github_user": "GitHub user",
    "jira_password": "JIRA password",
    "jira_project_key": "JIRA project key",
    "jira_transition_review": "Transition workflow on review?",
    "jira_transition_finish": "Transition workflow on finish?",
    "jira_url": "JIRA base url",
    "jira_user": "JIRA username",
    "pivotal_api_token": "Pivotal Tracker API token",
    "pivotal_email": "Pivotal Tracker email",
    "pivotal_exclusive": "Exclude stories which you do not own?",
    "pivotal_password": "Pivotal Tracker password",
    "pivotal_project_id": "Pivotal Tracker project ID"
}
MESSAGES["jira_exclusive"] = MESSAGES["github_exclusive"]


class BaseCommand(object):
    """Base command.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    def __init__(self, parser, namespace):
        self.namespace = namespace

    @classmethod
    def _help(cls):
        """Get help text for this command.
        """
        try:
            ret_val = getattr(cls, "help")
        except AttributeError:
            ret_val = cls.__doc__.split('\n', 1)[0][:-1]

        return ret_val


class GitCommand(BaseCommand):
    """Base Git command.
    """

    def __call__(self):
        """Call this command.
        """
        self.branch = self.git.branch

        try:
            self.execute()
        except (ConnectionError, ServiceException):
            puts("fatal: unable to access remote.")
            self.exit()
        except (KeyboardInterrupt, EOFError):
            puts()
            self.exit()

        self.finalize()

    def execute(self):
        """Execute this command.
        """
        raise NotImplementedError

    def exit(self):
        """Handle command exit.
        """
        exit()

    def finalize(self):
        """Finalize this command.
        """
        pass

    def get_section(self, name):
        """Get a git configuration section.

        :param name: The name of the section to retrieve.
        """
        ret_val = self.git.get_configuration(name)

        if not ret_val:
            message = "Missing '{0}' git configuration.".format(name)
            exit(message)

        return ret_val

    def get_template(self, name, default=None, **kwargs):
        """Get a continuity template.

        :param name: The name of the template to render.
        :param default: The value to render if the template does not exist.
        :param **kwargs: Template rendering context keyword-arguments.
        """
        continuity = self.git.get_configuration("continuity")
        tracker = continuity["tracker"]
        template = self.git.get_configuration(tracker, "template").get(
            name)

        if template:
            context = self.git.configuration
            context["git"] = self.git
            context.update(kwargs)
            ret_val = render(template, **context)
        else:
            ret_val = default

        return ret_val

    def get_value(self, section, key):
        """Get a git configuration value.

        :param section: The configuration section.
        :param key: The key to retrieve a value for.
        """
        configuration = self.get_section(section)

        try:
            ret_val = configuration[key]
        except KeyError:
            message = "Missing '{0}.{1}' git configuration.".format(section,
                    key)
            exit(message)

        return ret_val

    @cached_property
    def git(self):
        """Git accessor.
        """
        try:
            ret_val = GitService()
        except GitException:
            puts_err("fatal: Not a git repository.")
            exit(128)

        return ret_val


class GitHubCommand(GitCommand):
    """Base GitHub command.
    """

    @cached_property
    def github(self):
        """GitHub accessor.
        """
        token = self.get_value("github", "oauth-token")

        return GitHubService(self.git, token)


class CommitCommand(BaseCommand):
    """Git prepare commit message hook.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    help = SUPPRESS
    name = "commit"

    def __init__(self, parser, namespace):
        parser.add_argument("file", metavar="<file>")
        parser.add_argument("parameters", help=SUPPRESS, nargs=REMAINDER)
        super(CommitCommand, self).__init__(parser, namespace)

    def __call__(self):
        """Call this commit command.
        """
        try:
            git = GitService()

            if git.branch:
                configuration = git.get_configuration("branch",
                        git.branch.name)

                if configuration:
                    continuity = git.get_configuration("continuity")
                    tracker = continuity.get("tracker")

                    try:
                        if tracker == "jira":
                            mention = configuration["issue"]
                        else:
                            if continuity.get("tracker") == "github":
                                number = configuration["issue"]
                            else:
                                number = configuration["story"]

                            mention = "#{0}".format(number)

                        with open(self.namespace.file, 'r') as file:
                            message = file.read()

                        if mention not in message:
                            if tracker == "jira":
                                message = "{0} #comment {1}".format(mention,
                                    message)
                            else:
                                message = "[{0}] {1}".format(mention, message)

                            with open(self.namespace.file, 'w') as file:
                                file.write(message)
                    except KeyError:
                        exit()
                else:
                    exit()
            else:
                exit()
        except GitException:
            exit()


class FinishCommand(GitHubCommand):
    """Finish work on a branch.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "finish"

    def __init__(self, parser, namespace):
        parser.add_argument("branch", metavar="<branchname>")
        parser.add_argument("parameters", help=SUPPRESS, nargs=REMAINDER)
        super(FinishCommand, self).__init__(parser, namespace)

    def _merge_branch(self, branch, *args):
        """Merge a branch.

        :param branch: The name of the branch to merge.
        :param *args: Merge argument list.
        """
        raise NotImplementedError

    def execute(self):
        """Execute this finish command.
        """
        if self.branch.name == self.namespace.branch:
            exit("Already up-to-date.")

        configuration = self.git.get_configuration("branch",
                self.namespace.branch)
        branch = configuration.get("integration-branch",
                self.get_value("continuity", "integration-branch"))

        if branch == self.branch.name:
            try:
                self._merge_branch(self.namespace.branch,
                        *self.namespace.parameters)
                puts("Merged branch '{0}' into {1}.".format(
                    self.namespace.branch, self.branch.name))

                try:
                    self.git.delete_branch(self.namespace.branch)
                    puts("Deleted branch {0}.".format(self.namespace.branch))
                except GitException:
                    exit("conflict: Fix conflicts and then commit the result.")
            except GitException, error:
                paths = self.git.repo.index.unmerged_blobs()

                if paths:
                    for path in paths:
                        puts_err("Merge conflict: {0}".format(path))
                else:
                    puts_err(error.message)
                    exit(error.status)
        else:
            message = "error: Attempted finish from non-integration branch; switch to '{0}'."  # NOQA
            exit(message.format(branch))

    def finalize(self):
        """Finalize this finish command.
        """
        try:
            self.github.remove_branch(self.namespace.branch)
            self.git.prune_branches()
        except GitHubException:
            pass


class InitCommand(GitCommand):
    """Initialize a git repository for use with continuity.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "init"

    def __init__(self, parser, namespace):
        parser.add_argument("-n", "--new", action="store_true",
                help="reinitialize from scratch")
        super(InitCommand, self).__init__(parser, namespace)
        self.jira = {}
        self.pivotal = {}

    def execute(self):
        """Execute this init command.
        """
        puts("Enter values or accept [defaults] with Enter.")
        puts()
        self.continuity = self.initialize_continuity()

        if self.continuity["tracker"] == "jira":
            puts()
            self.jira = self.initialize_jira()
        elif self.continuity["tracker"] == "pivotal":
            puts()
            self.pivotal = self.initialize_pivotal()

        puts()
        self.github = self.initialize_github()
        self.aliases = {}
        commands = get_commands(self.continuity["tracker"])

        for command, command_class in commands.iteritems():
            if issubclass(command_class, GitCommand):
                alias = "continuity" if command == "init" else command
                self.aliases[alias] = "!continuity {0}".format(command)

        self.git.set_configuration("continuity", **self.continuity)
        self.git.set_configuration("github", **self.github)
        self.git.set_configuration("jira", **self.jira)
        self.git.set_configuration("pivotal", **self.pivotal)
        self.git.set_configuration("alias", **self.aliases)

        if self.pivotal:
            github = GitHubService(self.git, self.github["oauth-token"])
            hooks = github.get_hooks()
            token = hooks.get("pivotaltracker", {}).get("config", {}).\
                get("token")

            if not token:
                token = self.pivotal["api-token"]
                github.create_hook("pivotaltracker", token=token)

        filename = "{0}/hooks/prepare-commit-msg".format(self.git.repo.git_dir)

        if exists(filename):
            backup = "{0}.bak".format(filename)

            if not exists(backup):
                rename(filename, backup)

        with open(filename, 'w') as hook:
            hook.write('#!/bin/sh\n\ncontinuity commit "$@"')

        chmod(filename, 0755)

    def exit(self):
        """Handle init command exit.
        """
        puts("Initialization aborted. Changes NOT saved.")
        super(InitCommand, self).exit()

    def finalize(self):
        """Finalize this init command.
        """
        puts()
        puts("Configured git for continuity:")

        with indent():
            for key, value in self.jira.iteritems():
                puts("jira.{0}={1}".format(key, value))

            for key, value in self.pivotal.iteritems():
                puts("pivotal.{0}={1}".format(key, value))

            for key, value in self.github.iteritems():
                puts("github.{0}={1}".format(key, value))

            for key, value in self.continuity.iteritems():
                if isinstance(value, bool):
                    value = str(value).lower()

                puts("continuity.{0}={1}".format(key, value))

        puts()
        puts("Aliased git commands:")

        with indent():
            for command in sorted(self.aliases.iterkeys()):
                puts(command)

    def initialize_continuity(self):
        """Initialize continuity data.
        """
        if self.namespace.new:
            configuration = {}
        else:
            configuration = self.git.get_configuration("continuity")

        branch = configuration.get("integration-branch", self.branch.name)
        branch = prompt(MESSAGES["continuity_integration_branch"], branch)
        tracker = configuration.get("tracker")
        tracker = prompt(MESSAGES["continuity_tracker"], tracker,
                characters="GJP", echo=False)

        if tracker == 'G':
            tracker = "github"
        elif tracker == 'J':
            tracker = "jira"
        elif tracker == 'P':
            tracker = "pivotal"

        message = MESSAGES["{0}_exclusive".format(tracker)]
        default = configuration.get("exclusive", False)
        exclusive = confirm(message, default=default)

        return {
            "integration-branch": branch,
            "tracker": tracker,
            "exclusive": exclusive
        }

    def initialize_github(self):
        """Initialize github data.
        """
        configuration = self.git.get_configuration("github")
        token = configuration.get("oauth-token")

        if token and not self.namespace.new:
            token = prompt(MESSAGES["github_oauth_token"], token)
        else:
            user = prompt(MESSAGES["github_user"], configuration.get("user"))
            password = prompt(MESSAGES["github_password"], echo=False)
            name = "continuity:{0}".format(self.git.repo.working_dir)
            url = "https://github.com/jzempel/continuity"

            try:
                token = GitHubService.create_token(user, password, name,
                        url=url)
            except GitHubRequestException:
                code = prompt(MESSAGES["github_2fa_code"])
                token = GitHubService.create_token(user, password, name,
                        code=code, url=url)

            if not token:
                exit("Invalid GitHub credentials.")

        return {"oauth-token": token}

    def initialize_jira(self):
        """Initialize jira data.
        """
        if self.namespace.new:
            configuration = {}
        else:
            configuration = self.git.get_configuration("jira")

        url = prompt(MESSAGES["jira_url"], configuration.get("url"))
        token = configuration.get("auth-token")
        project_key = configuration.get("project-key")
        user = prompt(MESSAGES["jira_user"], configuration.get("user"))

        if not token or user != configuration.get("user"):
            password = prompt(MESSAGES["jira_password"], echo=False)
            token = JiraService.get_token(user, password)

        jira = JiraService(url, token)

        try:
            jira.get_user()
        except:
            exit("Invalid JIRA credentials.")

        projects = jira.projects

        if projects:
            if not project_key:
                for project in projects:
                    message = "{0} - {1}".format(colored.yellow(project.key),
                            project.name)
                    puts(message)

            project_key = prompt(MESSAGES["jira_project_key"], project_key)
            project = jira.get_project(project_key)

            if not project:
                exit("Invalid project key.")
        else:
            exit("No JIRA projects found.")

        default = configuration.get("review-transition", False)
        review_transition = confirm(MESSAGES["jira_transition_review"],
                default=default)
        default = configuration.get("finish-transition", True)
        finish_transition = confirm(MESSAGES["jira_transition_finish"],
                default=default)

        return {
            "auth-token": token,
            "finish-transition": finish_transition,
            "project-key": project_key,
            "review-transition": review_transition,
            "url": url,
            "user": user
        }

    def initialize_pivotal(self):
        """Initialize pivotal data.
        """
        if self.namespace.new:
            configuration = {}
        else:
            configuration = self.git.get_configuration("pivotal")

        token = configuration.get("api-token")
        project_id = configuration.get("project-id")
        email = configuration.get("email",
                self.git.get_configuration("user").get("email"))
        owner_id = configuration.get("owner-id")

        if token:
            token = prompt(MESSAGES["pivotal_api_token"], token)
        else:
            email = prompt(MESSAGES["pivotal_email"], email)
            password = prompt(MESSAGES["pivotal_password"], echo=False)
            token = PivotalTrackerService.get_token(email, password)

            if not token:
                exit("Invalid Pivotal Tracker credentials.")

        pt = PivotalTrackerService(token)
        projects = pt.projects

        if projects:
            if not project_id:
                for project in projects:
                    message = "{0} - {1}".format(colored.yellow(project.id),
                            project.name)
                    puts(message)

            project_id = prompt(MESSAGES["pivotal_project_id"], project_id)
            project = pt.get_project(project_id)

            if project:
                try:
                    password
                except NameError:
                    email = prompt(MESSAGES["pivotal_email"], email)

                for member in project.members:
                    if member.email == email:
                        owner_id = member.id
                        break
                else:
                    exit("Invalid project member email.")
            else:
                exit("Invalid project ID.")
        else:
            exit("No Pivotal Tracker projects found.")

        return {
            "api-token": token,
            "project-id": project_id,
            "email": email,
            "owner-id": owner_id,
        }


class ReviewCommand(GitHubCommand):
    """Open a GitHub pull request for branch review.
    """

    name = "review"

    def _create_pull_request(self, branch):
        """Create a pull request.

        :param branch: The base branch the pull request is for.
        """
        raise NotImplementedError

    def execute(self):
        puts("Creating pull request...")

        try:
            self.git.push_branch()
            configuration = self.git.get_configuration("branch",
                    self.branch.name)
            branch = configuration.get("integration-branch",
                    self.get_value("continuity", "integration-branch"))
            pull_request = self._create_pull_request(branch)
            puts("Opened pull request: {0}".format(pull_request.url))
        except GitHubException, e:
            message = "Unable to create pull request"

            for error in getattr(e, "json").get("errors", []):
                if error["code"] == "custom":
                    error_message = error["message"]
                    message = "{0} - {1}{2}".format(message,
                            error_message[:1].lower(), error_message[1:])
                    break
            else:
                message = "{0}.".format(message)

            exit(message)

    def exit(self):
        """Handle review command exit.
        """
        puts("Aborted branch review.")
        super(ReviewCommand, self).exit()


class StartCommand(GitCommand):
    """Start work on a branch.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "start"

    def __init__(self, parser, namespace):
        parser.add_argument("-f", "--force", action="store_true",
                help="allow start from non-integration branch")
        super(StartCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this start command.
        """
        branch = self.get_value("continuity", "integration-branch")

        if self.namespace.force or branch == self.branch.name:
            name = prompt(MESSAGES["git_branch"])
            ret_val = '-'.join(name.split())
            prefix = self.get_template("branch-prefix")

            if prefix and not ret_val.startswith(prefix):
                ret_val = "{0}{1}".format(prefix, ret_val)

            try:
                self.git.create_branch(ret_val)

                if self.namespace.force:
                    kwargs = {"integration-branch": self.branch.name}
                    self.git.set_configuration("branch", ret_val, **kwargs)

                puts("Switched to a new branch '{0}'".format(ret_val))
            except GitException, e:
                if not self.git.remote:
                    self.git.get_branch(branch)
                    self.git.delete_branch(ret_val)

                exit(e)
        else:
            message = "error: Attempted start from non-integration branch; switch to '{0}'.\nUse -f if you really want to start from '{1}'."  # NOQA
            exit(message.format(branch, self.branch.name))

        return ret_val


class TasksCommand(GitCommand):
    """List and manage branch tasks.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "tasks"

    def __init__(self, parser, namespace):
        parser.add_argument("-x", "--check", metavar="<number>")
        parser.add_argument("-o", "--uncheck", metavar="<number>")
        super(TasksCommand, self).__init__(parser, namespace)

    def _get_tasks(self):
        """Task list accessor.
        """
        raise NotImplementedError

    def _set_task(self, task, checked):
        """Task mutator.

        :param task: The task to update.
        :param checked: ``True`` if the task is complete.
        """
        raise NotImplementedError

    def execute(self):
        """Execute this tasks command.
        """
        self.tasks = self._get_tasks()

        if self.namespace.check or self.namespace.uncheck:
            index = int(self.namespace.check or self.namespace.uncheck) - 1

            try:
                task = self.tasks[index]
                checked = True if self.namespace.check else False
                task = self._set_task(task, checked)
                self.tasks[index] = task
            except IndexError:
                exit("error: Task number out of range.")


def get_commands(tracker=None):
    """Get the available continuity commands.

    :param tracker: Default `None`. The tracker to get commands for. Lookup
        based on git configuration if not specified.
    """
    ret_val = {
        CommitCommand.name: CommitCommand,
        InitCommand.name: InitCommand,
    }

    try:
        git = GitService()

        if not tracker:
            continuity = git.get_configuration("continuity")
            tracker = continuity["tracker"]

        if tracker == "github":
            from .github import (FinishCommand, IssueCommand, IssuesCommand,
                    ReviewCommand, StartCommand, TasksCommand)

            ret_val.update({
                FinishCommand.name: FinishCommand,
                IssueCommand.name: IssueCommand,
                IssuesCommand.name: IssuesCommand,
                ReviewCommand.name: ReviewCommand,
                StartCommand.name: StartCommand,
                TasksCommand.name: TasksCommand
            })
        elif tracker == "jira":
            from .jira import (FinishCommand, IssueCommand, IssuesCommand,
                    ReviewCommand, StartCommand, TasksCommand)

            ret_val.update({
                FinishCommand.name: FinishCommand,
                IssueCommand.name: IssueCommand,
                IssuesCommand.name: IssuesCommand,
                ReviewCommand.name: ReviewCommand,
                StartCommand.name: StartCommand,
                TasksCommand.name: TasksCommand
            })
        else:
            from .pt import (BacklogCommand, FinishCommand, ReviewCommand,
                    StoryCommand, StartCommand, TasksCommand)

            ret_val.update({
                BacklogCommand.name: BacklogCommand,
                FinishCommand.name: FinishCommand,
                ReviewCommand.name: ReviewCommand,
                StoryCommand.name: StoryCommand,
                StartCommand.name: StartCommand,
                TasksCommand.name: TasksCommand
            })
    except (GitException, KeyError):
        from .commons import (FinishCommand, ReviewCommand, StartCommand,
                TasksCommand)

        ret_val.update({
            FinishCommand.name: FinishCommand,
            ReviewCommand.name: ReviewCommand,
            StartCommand.name: StartCommand,
            TasksCommand.name: TasksCommand
        })

    return ret_val
