# -*- coding: utf-8 -*-
"""
    continuity.cli
    ~~~~~~~~~~~~~~

    Continuity command line interface.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from . import __version__
from .git import Git, GitException
from .github import GitHub, GitHubException
from .pt import PivotalTracker
from clint import args
from clint.textui import colored, columns, indent, puts, puts_err
from getpass import getpass
from os import chmod
from sys import exit


def _commit(arguments):
    """Git prepare commit message hook.

    :param arguments: Command line arguments.
    """
    commit = arguments.get(0)

    if commit:
        git = Git()
        configuration = git.get_configuration("branch", git.branch.name)

        if configuration:
            try:
                story_id = configuration["story"]

                with open(commit) as file:
                    message = file.read()

                message = "[#{0}] {1}".format(story_id, message)

                with open(commit, 'w') as file:
                    file.write(message)
            except KeyError:
                exit()
        else:
            exit()
    else:
        exit()


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
    branch = configuration.get("integration-branch") or git.branch.name
    branch = _prompt("Integration branch", branch)

    return {"integration-branch": branch}


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


def _prompt(message, default=None):
    """Prompt for input.

    :param default: Default `None`. The default input value.
    """
    if default:
        message = "{0} [{1}]".format(message, default)

    while True:
        ret_val = raw_input("{0}: ".format(message)).strip() or default

        if ret_val:
            break

    return ret_val


def finish(arguments):
    """Finish a story branch.

    :param arguments: Command line arguments.
    """
    git = _git()
    branch = git.branch.name
    story_id = _get_story_id(git)
    message = "[finish #{0}]".format(story_id)
    target = _get_section(git, "continuity").get("integration-branch")
    git.merge_branch(target, message)
    puts("Merged branch '{0}' into {1}.".format(branch, git.branch.name))
    git.delete_branch(branch)
    puts("Deleted branch {0}.".format(branch))
    git.push_branch()
    puts("Finished story #{0}.".format(story_id))


def help(arguments):
    """Display help for continuity.

    :param arguments: Command line arguments (ignored).
    """
    puts("usage: continuity [--version]")

    with indent(18):
        puts("[--help]")
        puts("<command> [<args>]")

    puts()
    command_documentation = {}
    width = 0

    for command, function in commands.iteritems():
        if not (command.startswith("--") or function.__name__.startswith('_')):
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
        configuration = git.get_configuration("pivotal")
        pivotal = _init_pivotal(configuration)
        puts()
        configuration = git.get_configuration("github")
        github = _init_github(configuration, pivotal)
        puts()
        configuration = git.get_configuration("continuity")
        continuity = _init_continuity(configuration)
    except KeyboardInterrupt:
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
            puts("continuity.{0}={1}".format(key, value))

    aliases = {
        "finish": "!continuity finish \"$@\"",
        "review": "!continuity review \"$@\"",
        "start": "!continuity start \"$@\"",
        "task": "!continuity task \"$@\""
    }
    git.set_configuration("alias", **aliases)
    puts()
    puts("Aliased git commands:")

    with indent():
        for command in sorted(aliases.iterkeys()):
            puts(command)

    filename = "{0}/hooks/prepare-commit-msg".format(git.repo.git_dir)

    with open(filename, 'w') as hook:
        hook.write('#!/bin/sh\n\ncontinuity commit "$@"')

    chmod(filename, 0755)
    exit()


def main():
    """Main entry point.
    """
    command = args.get(0) or "--help"

    if command in commands:
        args.remove(command)
        commands[command].__call__(args)


def review(arguments):
    """Open a GitHub pull request for story branch review.

    :param arguments: Command line arguments.
    """
    git = _git()
    story_id = _get_story_id(git)
    token = _get_value(git, "pivotal", "api-token")
    pt = PivotalTracker(token)
    project_id = _get_value(git, "pivotal", "project-id")
    token = _get_value(git, "github", "oauth-token")

    try:
        github = GitHub(git, token)
        title = _prompt("Pull request title", git.branch.name)
        description = raw_input("Pull request description (optional): ")
        story = pt.get_story(project_id, story_id)

        if story:
            if description:
                "{0}\n\n{1}".format(story.url, description)
            else:
                description = story.url

        git.push_branch()
        branch = _get_value(git, "continuity", "integration-branch")
        pull_request = github.create_pull_request(title, description,
                branch)
        puts("Opened pull request: {0}".format(pull_request["url"]))
    except GitHubException, e:
        puts_err("Unable to create pull request.")
        exit(128)


def start(arguments):
    """Start a branch linked to a Pivotal Tracker story.

    :param arguments: Command line arguments.
    """
    git = _git()
    token = _get_value(git, "pivotal", "api-token")
    pt = PivotalTracker(token)
    owner = _get_value(git, "pivotal", "owner")
    filter = "owner:{0} state:unstarted,rejected".format(owner)
    puts("Retrieving next story from Pivotal Tracker for {0}…".\
            format(owner))
    project_id = _get_value(git, "pivotal", "project-id")
    story = pt.get_story(project_id, filter)

    if not story:
        filter = "state:unstarted"
        story = pt.get_story(project_id, filter)

    if story:
        puts("Story: {0}".format(story.name))

        if story.owner != owner:
            story = pt.set_story(project_id, story.id, story.state, owner)

        # Verify that owner got the story.
        if story.owner == owner:
            try:
                name = _prompt("Enter branch name")
                git.create_branch(name)
                git.set_configuration("branch", name, story=story.id)
                pt.set_story(project_id, story.id, "started")
                puts("Switched to a new branch '{0}'".format(name))
            except KeyboardInterrupt:
                puts()
                puts("Aborted story branch!")
        else:
            puts("Unable to update story owner.")
    else:
        puts("No estimated stories found in the backlog.")


def task(arguments):
    """List and manage story tasks.

    :param arguments: Command line arguments.
    """
    git = _git()
    story_id = _get_story_id(git)
    token = _get_value(git, "pivotal", "api-token")
    pt = PivotalTracker(token)
    project_id = _get_value(git, "pivotal", "project-id")
    tasks = pt.get_tasks(project_id, story_id)

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
    "commit": _commit,
    "finish": finish,
    "init": init,
    "review": review,
    "start": start,
    "task": task
}
