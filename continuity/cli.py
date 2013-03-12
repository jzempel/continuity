# -*- coding: utf-8 -*-
"""
    continuity.cli
    ~~~~~~~~~~~~~~

    Continuity command line interface.

    :copyright: 2013 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from . import __version__
from .git import Git, GitException
from .github import GitHub, GitHubException, Issue
from .pt import PivotalTracker, Story
from argparse import ArgumentParser, Namespace
from clint import args
from clint.textui import colored, columns, indent, puts, puts_err
from curses.ascii import ctrl, CR, EOT, ETX, isctrl, LF
from getch.getch import getch
from getpass import getpass
from os import chmod, rename
from os.path import exists
from pydoc import pipepager
from StringIO import StringIO
from sys import exit


class ContinuityNamespace(Namespace):
    """Continuity argument namespace.

    :param git: Git repository.
    """

    def __init__(self, git, **kwargs):
        super(ContinuityNamespace, self).__init__(**kwargs)

        self.configuration = git.get_configuration("continuity")

    @property
    def exclusive(self):
        """Determine if continuity is operating in exclusive mode.
        """
        return self.configuration.get("exclusive", False) or \
            getattr(self, "assignedtoyou", False) or \
            getattr(self, "mywork", False)


def _commit(arguments):
    """Git prepare commit message hook.

    :param arguments: Command line arguments.
    """
    commit = arguments.get(0)

    if commit:
        git = Git()
        configuration = git.get_configuration("branch", git.branch.name)

        if configuration:
            continuity = git.get_configuration("continuity")

            try:
                if continuity.get("tracker") == "github":
                    number = configuration["issue"]
                else:
                    number = configuration["story"]

                with open(commit) as file:
                    message = file.read()

                message = "[#{0}] {1}".format(number, message)

                with open(commit, 'w') as file:
                    file.write(message)
            except KeyError:
                exit()
        else:
            exit()
    else:
        exit()


def _confirm(message, default=False):
    """Prompt for confirmation.

    :param message: The confirmation message.
    :param default: Default `False`.
    """
    if default is True:
        options = "Y/n"
    elif default is False:
        options = "y/N"
    else:
        options = "y/n"

    message = "{0} ({1})".format(message, options)
    ret_val = _prompt(message, default=default, characters="YN")

    if ret_val == 'Y':
        ret_val = True
    elif ret_val == 'N':
        ret_val = False

    return ret_val


def _filter_issues(github, user, number=None, exclusive=False):
    """Filter issues for the given parameters.

    :param github: GitHub object instance.
    :param user: The user to filter by.
    :param number: Default `None`. The issue number to filter by.
    :param exclusive: Default `False`. Determine whether to filter for the
        current user.
    """
    ret_val = None
    available = lambda issue: issue and issue.state == Issue.STATE_OPEN and \
        not("started" in issue.labels or "finished" in issue.labels) and \
        issue.pull_request.url is None

    if number and exclusive:
        puts("Retrieving issue #{0} from GitHub for {1}…".format(number, user))
        issue = github.get_issue(number)

        if available(issue) and issue.assignee and issue.assignee == user:
            ret_val = issue
    elif number:
        puts("Retrieving issue #{0} from GitHub…".format(number))
        issue = github.get_issue(number)

        if available(issue):
            ret_val = issue
    elif exclusive:
        puts("Retrieving next issue from GitHub for {0}…".format(user))
        issues = _get_issues(github, assignee=user.login)

        if issues:
            for issue in issues:
                if available(issue):
                    ret_val = issue
                    break
    else:
        puts("Retrieving next available issue from GitHub…")
        issues = _get_issues(github)

        for issue in issues:
            if available(issue) and (issue.assignee is None or
                    issue.assignee == user):
                ret_val = issue
                break

    return ret_val


def _filter_stories(pt, project_id, owner, story_id=None, exclusive=False):
    """Filter stories for the given parameters.

    :param pt: Pivotal Tracker object instance.
    :param project_id: The project ID to filter stories for.
    :param owner: The owner to filter by.
    :param story_id: Default `None`. The story ID to filter by.
    :param exclusive: Default `False`. Determine whether to filter for the
        current user.
    """
    if story_id and exclusive:
        puts("Retrieving story #{0} from Pivotal Tracker for {1}…".format(
            story_id, owner))
        filter = "id:{0} owner:{1} state:unstarted,rejected".format(story_id,
            owner)
    elif story_id:
        puts("Retrieving story #{0} from Pivotal Tracker…".format(story_id))
        filter = "id:{0} state:unstarted,rejected".format(story_id)
    elif exclusive:
        puts("Retrieving next story from Pivotal Tracker for {0}…".format(
            owner))
        filter = "owner:{0} state:unstarted,rejected".format(owner)
    else:
        filter = None

    if filter:
        ret_val = pt.get_story(project_id, filter)
    else:
        puts("Retrieving next available story from Pivotal Tracker…")
        stories = pt.get_backlog(project_id)

        for story in stories:
            if story.type in (Story.TYPE_FEATURE, Story.TYPE_BUG,
                    Story.TYPE_CHORE) and (story.owner is None or
                    story.owner == owner):
                ret_val = story
                break
        else:
            ret_val = None

    return ret_val


def _get_commands():
    """Get the available commands.
    """
    ret_val = {}

    try:
        git = Git()
        configuration = git.get_configuration("continuity")

        if configuration:
            tracker = configuration.get("tracker", "pivotal")
        else:
            tracker = None
    except GitException:
        tracker = None

    for command, function in commands.iteritems():
        if not (command.startswith("--") or function.__name__.startswith('_')):
            if tracker and ":tracker" in function.__doc__:
                if ":tracker {0}:".format(tracker) in function.__doc__:
                    ret_val[command] = function
            else:
                ret_val[command] = function

    return ret_val


def _get_issue_number(git):
    """Get the issue number for the current Git branch.

    :param git: Git repository.
    """
    configuration = git.get_configuration("branch", git.branch.name)

    if configuration:
        try:
            ret_val = configuration["issue"]
        except KeyError:
            ret_val = None
    else:
        ret_val = None

    if not ret_val:
        puts_err("fatal: Not an issue branch.")
        exit(1)

    return ret_val


def _get_issues(github, **parameters):
    """Get a list of issues from GitHub, ordered by milestone.

    :param github: GitHub object instance.
    :param parameters: Parameter keyword-arguments.
    """
    ret_val = []
    milestones = github.get_milestones()

    for milestone in milestones:
        parameters["milestone"] = milestone.number
        issues = github.get_issues(**parameters)
        ret_val.extend(issues)

    parameters["milestone"] = None
    issues = github.get_issues(**parameters)
    ret_val.extend(issues)

    return ret_val


def _get_section(git, name):
    """Get a git configuration section.

    :param git: Git repository.
    :param name: The name of the section to retrieve.
    """
    ret_val = git.get_configuration(name)

    if not ret_val:
        message = "Missing '{0}' git configuration.".format(name)
        puts_err(message)
        exit(1)

    return ret_val


def _get_story_id(git):
    """Get the story ID for the current Git branch.

    :param git: Git repository.
    """
    configuration = git.get_configuration("branch", git.branch.name)

    if configuration:
        try:
            ret_val = configuration["story"]
        except KeyError:
            ret_val = None
    else:
        ret_val = None

    if not ret_val:
        puts_err("fatal: Not a story branch.")
        exit(1)

    return ret_val


def _get_value(git, section, key):
    """Get a git configuration value.

    :param git: Git repository.
    :param section: The configuration section.
    :param key: The key to retrieve a value for.
    """
    configuration = _get_section(git, section)

    try:
        ret_val = configuration[key]
    except KeyError:
        message = "Missing '{0}.{1}' git configuration.".\
            format(section, key)
        puts(message)
        exit(1)

    return ret_val


def _git():
    """Get git.
    """
    try:
        ret_val = Git()
    except GitException:
        puts_err("fatal: Not a git repository.")
        exit(128)

    return ret_val


def _init_continuity(configuration):
    """Initialize Continuity data.

    :param configuration: The git configuration to initialize for.
    """
    git = Git()
    branch = configuration.get("integration-branch", git.branch.name)
    branch = _prompt("Integration branch", branch)
    tracker = configuration.get("tracker")
    tracker = _prompt("Configure for (P)ivotal Tracker or (G)itHub Issues?",
            tracker, characters="PG")

    if tracker == 'P':
        tracker = "pivotal"
    elif tracker == 'G':
        tracker = "github"

    exclusive = configuration.get("exclusive", False)

    if tracker == "github":
        exclusive = _confirm("Exclude issues not assigned to you?",
                default=exclusive)
    else:
        exclusive = _confirm("Exclude stories which you do not own?",
                default=exclusive)

    return {
        "integration-branch": branch,
        "tracker": tracker,
        "exclusive": exclusive
    }


def _init_github(configuration, pivotal):
    """Initialize GitHub data.

    :param configuration: The GitHub configuration to intialize for.
    :param pivotal: The Pivotal configuration to initialize for.
    """
    git = Git()
    token = configuration.get("oauth-token")

    if token:
        token = _prompt("GitHub OAuth token", token)
    else:
        user = _prompt("GitHub user", configuration.get("user"))
        password = getpass("GitHub password: ")
        name = "continuity:{0}".format(git.repo.working_dir)
        url = "https://github.com/jzempel/continuity"
        token = GitHub.create_token(user, password, name, url)

        if not token:
            puts_err("Invalid GitHub credentials.")
            exit(1)

    ret_val = {"oauth-token": token}

    if pivotal:
        github = GitHub(git, token)
        hooks = github.get_hooks()
        token = hooks.get("pivotaltracker", {}).get("config", {}).get("token")

        if not token:
            token = pivotal["api-token"]
            github.create_hook("pivotaltracker", token=token)

    return ret_val


def _init_pivotal(configuration):
    """Initialize pivotal data.

    :param configuration: The git configuration to initialize for.
    """
    token = configuration.get("api-token")
    project_id = configuration.get("project-id")
    email = configuration.get("email")
    owner = configuration.get("owner")

    if token:
        token = _prompt("Pivotal Tracker API token", token)
    else:
        email = _prompt("Pivotal Tracker email", email)
        password = getpass("Pivotal Tracker password: ")
        token = PivotalTracker.get_token(email, password)

        if not token:
            puts_err("Invalid Pivotal Tracker credentials.")
            exit(1)

    pt = PivotalTracker(token)
    projects = pt.get_projects()

    if projects:
        if not project_id:
            for project in projects:
                message = "{0} - {1}".format(colored.yellow(project.id),
                        project.name)
                puts(message)

        project_id = _prompt("Pivotal Tracker project ID", project_id)
        project = pt.get_project(project_id)

        if project:
            try:
                password
            except NameError:
                email = _prompt("Pivotal Tracker email", email)

            for member in project.members:
                if member.email == email:
                    owner = member.name
                    break
            else:
                puts_err("Invalid project member email.")
        else:
            puts_err("Invalid project ID.")
            exit(1)
    else:
        puts_err("No Pivotal Tracker projects found.")
        exit(1)

    return {
        "api-token": token,
        "project-id": project_id,
        "email": email,
        "owner": owner,
    }


def _prompt(message, default=None, characters=None):
    """Prompt for input.

    :param message: The prompt message.
    :param default: Default `None`. The default input value.
    :param characters: Default `None`. Case-insensitive constraint for single-
        character input.
    """
    if isinstance(default, basestring):
        message = "{0} [{1}]".format(message, default)

    if characters:
        puts("{0} ".format(message), newline=False)
    else:
        message = "{0}: ".format(message)

    while True:
        if characters:
            ret_val = getch()

            if default is not None and ret_val in (chr(CR), chr(LF)):
                puts()
                ret_val = default
                break
            if ret_val in characters.lower() or ret_val in characters.upper():
                puts()

                if ret_val not in characters:
                    ret_val = ret_val.swapcase()

                break
            elif isctrl(ret_val) and ctrl(ret_val) in (chr(ETX), chr(EOT)):
                raise KeyboardInterrupt()
        else:
            ret_val = raw_input(message).strip() or default

            if ret_val:
                break

    return ret_val


def backlog(arguments):
    """List backlog stories.

    :param arguments: Command line arguments.

    :tracker pivotal:
    """
    git = _git()
    token = _get_value(git, "pivotal", "api-token")
    parser = ArgumentParser()
    parser.add_argument("-m", "--mywork", action="store_true",
            help="list stories owned by you")
    namespace = ContinuityNamespace(git)
    parser.parse_args(arguments.all, namespace=namespace)
    pt = PivotalTracker(token)
    owner = _get_value(git, "pivotal", "owner")
    project_id = _get_value(git, "pivotal", "project-id")
    project = pt.get_project(project_id)
    stories = pt.get_backlog(project.id)
    output = StringIO()

    for story in stories:
        if story.state in [Story.STATE_UNSCHEDULED, Story.STATE_UNSTARTED] \
                and (namespace.mywork is False or story.owner == owner):
            id = colored.yellow(str(story.id))

            if story.estimate is None:
                type = story.type.upper()
            elif story.estimate >= 0:
                type = "{0} ({1:d})".format(story.type.upper(), story.estimate)
            else:
                type = "{0} (?)".format(story.type.upper())

            name = story.name

            if story.owner:
                for member in project.members:
                    if member.name == story.owner:
                        name = "{0} ({1})".format(story.name, member.initials)
                        break

            message = "{0} {1}: {2}\n".format(id, type, name)
            output.write(message)

    pipepager(output.getvalue(), cmd="less -FRSX")


def finish(arguments):
    """Finish a story/issue branch.

    :param arguments: Command line arguments.
    """
    git = _git()
    tracker = _get_section(git, "continuity").get("tracker")

    if tracker == "github":
        number = _get_issue_number(git)
        verb = "close"
    else:
        number = _get_story_id(git)
        verb = "finish"

    branch = git.branch.name
    target = _get_section(git, "continuity").get("integration-branch")
    message = "[{0} #{1}]".format(verb, number)
    git.merge_branch(target, message)
    puts("Merged branch '{0}' into {1}.".format(branch, git.branch.name))

    if tracker == "github":
        token = _get_value(git, "github", "oauth-token")
        github = GitHub(git, token)
        github.add_labels(number, "finished")
        github.remove_label(number, "started")
        puts("Finished issue #{0}.".format(number))
    else:
        token = _get_value(git, "pivotal", "api-token")
        pt = PivotalTracker(token)
        project_id = _get_value(git, "pivotal", "project-id")
        pt.set_story(project_id, number, Story.STATE_FINISHED)
        puts("Finished story #{0}.".format(number))

    git.delete_branch(branch)
    puts("Deleted branch {0}.".format(branch))


def help(arguments):
    """Display help for continuity.

    :param arguments: Command line arguments (ignored).
    """
    puts("usage: continuity [--version]")

    with indent(18):
        puts("[--help]")
        puts("<command> [<args>]")

    puts()

    commands = _get_commands()
    command_documentation = {}
    width = 0

    for command, function in commands.iteritems():
        documentation = function.__doc__.split("\n\n", 1)[0][:-1]
        command_documentation[command] = documentation
        width = len(command) if len(command) > width else width

    puts("The continuity commands are:")

    with indent():
        for command in sorted(command_documentation):
            documentation = command_documentation[command]
            puts(columns([command, width + 2], [documentation, None]).rstrip())


def init(arguments):
    """Initialize a git repository for use with continuity.

    :param arguments: Command line arguments
    """
    git = _git()

    try:
        puts("Enter values or accept [defaults] with Enter.")
        puts()
        configuration = git.get_configuration("continuity")
        continuity = _init_continuity(configuration)
        puts()

        if continuity["tracker"] == "pivotal":
            configuration = git.get_configuration("pivotal")
            pivotal = _init_pivotal(configuration)
            puts()
        else:
            pivotal = {}

        configuration = git.get_configuration("github")
        github = _init_github(configuration, pivotal)
    except (KeyboardInterrupt, EOFError):
        puts()
        puts("Initialization aborted. Changes NOT saved.")
        exit()

    git.set_configuration("pivotal", **pivotal)
    git.set_configuration("github", **github)
    git.set_configuration("continuity", **continuity)
    puts()
    puts("Configured git for continuity:")

    with indent():
        for key, value in pivotal.iteritems():
            puts("pivotal.{0}={1}".format(key, value))

        for key, value in github.iteritems():
            puts("github.{0}={1}".format(key, value))

        for key, value in continuity.iteritems():
            if key == "exclusive":
                value = str(value).lower()

            puts("continuity.{0}={1}".format(key, value))

    commands = _get_commands()
    aliases = {}

    for command, function in commands.iteritems():
        alias = "continuity" if command == "init" else command
        command = "!continuity {0} \"$@\"".format(function.func_name)
        aliases[alias] = command

    git.set_configuration("alias", **aliases)
    puts()
    puts("Aliased git commands:")

    with indent():
        for command in sorted(aliases.iterkeys()):
            puts(command)

    filename = "{0}/hooks/prepare-commit-msg".format(git.repo.git_dir)

    if exists(filename):
        backup = "{0}.bak".format(filename)

        if not exists(backup):
            rename(filename, backup)

    with open(filename, 'w') as hook:
        hook.write('#!/bin/sh\n\ncontinuity commit "$@"')

    chmod(filename, 0755)
    exit()


def issue(arguments):
    """Display issue branch information.

    :param arguments: Command line arguments.

    :tracker github:
    """
    git = _git()
    token = _get_value(git, "github", "oauth-token")
    github = GitHub(git, token)
    number = _get_issue_number(git)
    issue = github.get_issue(number)

    if issue:
        puts(issue.title)

        if issue.milestone:
            puts()
            puts("Milestone: {0}".format(issue.milestone))

        if issue.description:
            puts()
            puts(colored.cyan(issue.description))

        puts()
        puts(colored.white("Created by {0} on {1}".format(issue.user.login,
            issue.created.strftime("%d %b %Y, %I:%M%p"))))
        puts(colored.white(issue.url))
    else:
        puts("GitHub issue not found")
        exit(128)


def issues(arguments):
    """List open issues.

    :param arguments: Command line arguments.

    :tracker github:
    """
    git = _git()
    token = _get_value(git, "github", "oauth-token")
    parser = ArgumentParser()
    parser.add_argument("-u", "--assignedtoyou", action="store_true",
            help="list issues assigned to you")
    namespace = ContinuityNamespace(git)
    parser.parse_args(arguments.all, namespace=namespace)
    github = GitHub(git, token)

    if namespace.assignedtoyou:
        user = github.get_user()
        issues = _get_issues(github, assignee=user.login)
    else:
        issues = _get_issues(github)

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
                information = "{0}, {1}".format(information, issue.milestone)
        else:
            information = issue.milestone

        if information:
            title = "{0} ({1})".format(title, information)

        message = "{0}: {1}\n".format(number, title.strip())
        output.write(message)

    pipepager(output.getvalue(), cmd="less -FRSX")


def main():
    """Main entry point.
    """
    command = args.get(0) or "--help"

    if command in commands:
        args.remove(command)
        commands[command].__call__(args)
    else:
        message = "continuity: '{0}' is not a continuity command. See 'continuity --help'."  # NOQA
        puts(message.format(command))
        exit(1)


def review(arguments):
    """Open a GitHub pull request for story/issue branch review.

    :param arguments: Command line arguments.
    """
    git = _git()
    tracker = _get_section(git, "continuity").get("tracker", "pivotal")
    token = _get_value(git, "github", "oauth-token")
    branch = _get_value(git, "continuity", "integration-branch")

    try:
        github = GitHub(git, token)

        if tracker == "github":
            puts("Creating pull request…")
            git.push_branch()
            number = _get_issue_number(git)
            pull_request = github.create_pull_request(number, branch)
        else:
            title = _prompt("Pull request title", git.branch.name)
            description = raw_input("Pull request description (optional): ")
            puts("Creating pull request…")
            token = _get_value(git, "pivotal", "api-token")
            pt = PivotalTracker(token)
            project_id = _get_value(git, "pivotal", "project-id")
            story_id = _get_story_id(git)
            story = pt.get_story(project_id, story_id)

            if story:
                if description:
                    "{0}\n\n{1}".format(story.url, description)
                else:
                    description = story.url

            git.push_branch()
            pull_request = github.create_pull_request(title, description,
                    branch)

        puts("Opened pull request: {0}".format(pull_request.url))
    except GitHubException:
        puts_err("Unable to create pull request.")
        exit(128)
    except (KeyboardInterrupt, EOFError):
        puts()
        puts("Aborted branch review!")


def start(arguments):
    """Start a branch linked to a story/issue.

    :param arguments: Command line arguments.
    """
    git = _git()
    tracker = _get_section(git, "continuity").get("tracker", "pivotal")
    parser = ArgumentParser()

    if tracker == "github":
        parser.add_argument("-n", "--number", help="start the specified issue",
                type=int)
        parser.add_argument("-u", "--assignedtoyou", action="store_true",
                help="only start issues assigned to you")
    else:
        parser.add_argument("-i", "--id", help="start the specified story",
                type=int)
        parser.add_argument("-m", "--mywork", action="store_true",
                help="only start stories owned by you")

    namespace = ContinuityNamespace(git)
    parser.parse_args(arguments.all, namespace=namespace)
    integration_branch = _get_value(git, "continuity", "integration-branch")

    if git.branch.name != integration_branch:
        message = "error: Attempted start from non-integration branch, switch to '{0}'."  # NOQA
        puts_err(message.format(integration_branch))
        exit(128)

    if tracker == "github":
        token = _get_value(git, "github", "oauth-token")
        github = GitHub(git, token)
        user = github.get_user()
        issue = _filter_issues(github, user, namespace.number,
                namespace.exclusive)

        if issue:
            puts("Issue: {0}".format(issue.title))

            if issue.assignee is None:
                issue = github.set_issue(issue.number, assignee=user.login)

            # Verify that user got the issue.
            if issue.assignee == user:
                try:
                    name = _prompt("Enter branch name")
                    name = '-'.join(name.split())
                    git.create_branch(name)
                    git.set_configuration("branch", name, issue=issue.number)
                    github.add_labels(issue.number, "started")
                    puts("Switched to a new branch '{0}'".format(name))
                except (KeyboardInterrupt, EOFError):
                    puts()
                    puts("Aborted issue branch!")
            else:
                puts("Unable to update issue assignee.")
        else:
            if namespace.number and namespace.exclusive:
                puts("No available issue #{0} found assigned to you.".format(
                    namespace.number))
            elif namespace.number:
                puts("No available issue #{0} found.".format(namespace.number))
            elif namespace.exclusive:
                puts("No available issues found assigned to you.")
            else:
                puts("No available issues found.")
    else:
        token = _get_value(git, "pivotal", "api-token")
        pt = PivotalTracker(token)
        project_id = _get_value(git, "pivotal", "project-id")
        owner = _get_value(git, "pivotal", "owner")
        story = _filter_stories(pt, project_id, owner, namespace.id,
                namespace.exclusive)

        if story:
            puts("Story: {0}".format(story.name))

            if story.owner is None:
                story = pt.set_story(project_id, story.id, story.state, owner)

            # Verify that owner got the story.
            if story.owner == owner:
                try:
                    name = _prompt("Enter branch name")
                    name = '-'.join(name.split())
                    git.create_branch(name)
                    git.set_configuration("branch", name, story=story.id)
                    pt.set_story(project_id, story.id, Story.STATE_STARTED)
                    puts("Switched to a new branch '{0}'".format(name))
                except (KeyboardInterrupt, EOFError):
                    puts()
                    puts("Aborted story branch!")
            else:
                puts("Unable to update story owner.")
        else:
            if namespace.id and namespace.exclusive:
                puts("No estimated story #{0} found assigned to you.".format(
                    namespace.id))
            elif namespace.id:
                puts("No estimated story #{0} found in the backlog.".format(
                    namespace.id))
            elif namespace.exclusive:
                puts("No estimated stories found in my work.")
            else:
                puts("No estimated stories found in the backlog.")


def story(arguments):
    """Display story branch information.

    :param arguments: Command line arguments.

    :tracker pivotal:
    """
    git = _git()
    story_id = _get_story_id(git)
    token = _get_value(git, "pivotal", "api-token")
    pt = PivotalTracker(token)
    project_id = _get_value(git, "pivotal", "project-id")
    filter = "id:{0}".format(story_id)
    story = pt.get_story(project_id, filter)

    if story:
        puts(story.name)
        puts()

        if story.estimate is None:
            puts(story.type.capitalize())
        elif story.estimate >= 0:
            puts("{0} Estimate: {1:d} points".format(story.type.capitalize(),
                story.estimate))
        else:
            puts("{0} Unestimated.".format(story.type.capitalize()))

        if story.description:
            puts()
            puts(colored.cyan(story.description))

        puts()
        puts(colored.white("Requested by {0} on {1}".format(story.requester,
            story.created.strftime("%d %b %Y, %I:%M%p"))))
        puts(colored.white(story.url))
    else:
        puts("Pivotal Tracker story not found")
        exit(128)


def tasks(arguments):
    """List and manage story tasks.

    :param arguments: Command line arguments.

    :tracker pivotal:
    """
    git = _git()
    story_id = _get_story_id(git)
    token = _get_value(git, "pivotal", "api-token")
    pt = PivotalTracker(token)
    project_id = _get_value(git, "pivotal", "project-id")
    tasks = pt.get_tasks(project_id, story_id)
    parser = ArgumentParser()
    parser.add_argument("-x", "--check", metavar="number")
    parser.add_argument("-o", "--uncheck", metavar="number")
    namespace = parser.parse_args(arguments.all)

    if namespace.check or namespace.uncheck:
        number = int(namespace.check or namespace.uncheck) - 1
        task = tasks[number]
        checked = True if namespace.check else False
        task = pt.set_task(project_id, story_id, task.id, checked)
        tasks[number] = task

    for task in tasks:
        checkmark = 'x' if task.is_checked else ' '
        message = "[{0}] {1}. {2}".format(checkmark, task.number,
                task.description)
        puts(message)


def version(arguments):
    """Display the version of Continuity.

    :param arguments: Command line arguments (ignored).
    """
    message = "continuity version {0}".format(__version__)
    puts(message)


commands = {
    "--help": help,
    "--version": version,
    "backlog": backlog,
    "commit": _commit,
    "finish": finish,
    "init": init,
    "issue": issue,
    "issues": issues,
    "review": review,
    "start": start,
    "story": story,
    "tasks": tasks
}
