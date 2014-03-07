# -*- coding: utf-8 -*-
"""
    continuity.cli.commons
    ~~~~~~~~~~~~~~~~~~~~~~

    Continuity command line commons.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .utils import cached_property, confirm, prompt
from argparse import REMAINDER, SUPPRESS
from clint.textui import colored, indent, puts, puts_err
from continuity.git import Git, GitException
from continuity.github import GitHub, GitHubException
from continuity.pt import PivotalTracker
from getpass import getpass
from os import chmod, rename
from os.path import exists
from requests.exceptions import ConnectionError
from sys import exit


class BaseCommand(object):
    """Base command.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    def __init__(self, parser, namespace):
        self.namespace = namespace


class GitCommand(BaseCommand):
    """Base Git command.
    """

    def __call__(self):
        """Call this command.
        """
        self.branch = self.git.branch

        try:
            self.execute()
        except (ConnectionError, GitException):
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
            ret_val = Git()
        except GitException:
            puts_err("fatal: Not a git repository.")
            exit(128)

        return ret_val


class GitHubCommand(GitCommand):
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
    def github(self):
        """GitHub accessor.
        """
        token = self.get_value("github", "oauth-token")

        return GitHub(self.git, token)

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
            git = Git()

            if git.branch:
                configuration = git.get_configuration("branch",
                        git.branch.name)

                if configuration:
                    continuity = git.get_configuration("continuity")

                    try:
                        if continuity.get("tracker") == "github":
                            number = configuration["issue"]
                        else:
                            number = configuration["story"]

                        mention = "#{0}".format(number)

                        with open(self.namespace.file, 'r') as file:
                            message = file.read()

                        if mention not in message:
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


class FinishCommand(GitCommand):
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


class InitCommand(GitCommand):
    """Initialize a git repository for use with continuity.
    """

    name = "init"

    def execute(self):
        """Execute this init command.
        """
        puts("Enter values or accept [defaults] with Enter.")
        puts()
        self.continuity = self.initialize_continuity()

        if self.continuity["tracker"] == "pivotal":
            puts()
            self.pivotal = self.initialize_pivotal()
        else:
            self.pivotal = {}

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
        self.git.set_configuration("pivotal", **self.pivotal)
        self.git.set_configuration("alias", **self.aliases)

        if self.pivotal:
            github = GitHub(self.git, self.github["oauth-token"])
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
        configuration = self.git.get_configuration("continuity")
        branch = configuration.get("integration-branch", self.branch.name)
        branch = prompt("Integration branch", branch)
        tracker = configuration.get("tracker")
        tracker = prompt("Configure for (P)ivotal Tracker or (G)itHub Issues?",
                tracker, characters="PG")

        if tracker == 'P':
            tracker = "pivotal"
        elif tracker == 'G':
            tracker = "github"

        exclusive = configuration.get("exclusive", False)

        if tracker == "github":
            exclusive = confirm("Exclude issues not assigned to you?",
                    default=exclusive)
        else:
            exclusive = confirm("Exclude stories which you do not own?",
                    default=exclusive)

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

        if token:
            token = prompt("GitHub OAuth token", token)
        else:
            user = prompt("GitHub user", configuration.get("user"))
            password = getpass("GitHub password: ")
            name = "continuity:{0}".format(self.git.repo.working_dir)
            url = "https://github.com/jzempel/continuity"
            token = GitHub.create_token(user, password, name, url)

            if not token:
                exit("Invalid GitHub credentials.")

        return {"oauth-token": token}

    def initialize_pivotal(self):
        """Initialize pivotal data.
        """
        configuration = self.git.get_configuration("pivotal")
        token = configuration.get("api-token")
        project_id = configuration.get("project-id")
        email = configuration.get("email")
        owner = configuration.get("owner")

        if token:
            token = prompt("Pivotal Tracker API token", token)
        else:
            email = prompt("Pivotal Tracker email", email)
            password = getpass("Pivotal Tracker password: ")
            token = PivotalTracker.get_token(email, password)

            if not token:
                exit("Invalid Pivotal Tracker credentials.")

        pt = PivotalTracker(token)
        projects = pt.get_projects()

        if projects:
            if not project_id:
                for project in projects:
                    message = "{0} - {1}".format(colored.yellow(project.id),
                            project.name)
                    puts(message)

            project_id = prompt("Pivotal Tracker project ID", project_id)
            project = pt.get_project(project_id)

            if project:
                try:
                    password
                except NameError:
                    email = prompt("Pivotal Tracker email", email)

                for member in project.members:
                    if member.email == email:
                        owner = member.name
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
            "owner": owner,
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
                    message = "{0} - {1}{2}.".format(message,
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
            name = prompt("Enter branch name")
            ret_val = '-'.join(name.split())

            try:
                self.git.create_branch(ret_val)

                if self.namespace.force:
                    kwargs = {"integration-branch": self.branch.name}
                    self.git.set_configuration("branch", ret_val, **kwargs)

                puts("Switched to a new branch '{0}'".format(ret_val))
            except GitException, e:
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
        parser.add_argument("-x", "--check", metavar="number")
        parser.add_argument("-o", "--uncheck", metavar="number")
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
        git = Git()

        if not tracker:
            continuity = git.get_configuration("continuity")
            tracker = continuity.get("tracker")

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
    except GitException:
        from .commons import (FinishCommand, ReviewCommand, StartCommand,
                TasksCommand)

        ret_val.update({
            FinishCommand.name: FinishCommand,
            ReviewCommand.name: ReviewCommand,
            StartCommand.name: StartCommand,
            TasksCommand.name: TasksCommand
        })

    return ret_val
