# -*- coding: utf-8 -*-
"""
    cli
    ~~~

    Continuity command line interface.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .git import Git, GitException
from .github import GitHub, GitHubException
from .pt import PivotalTracker
from clint import args
from clint.textui import colored, indent, puts, puts_err
from getpass import getpass
from os import chmod
from sys import exit


def _git():
    """Get git.
    """
    try:
        ret_val = Git()
    except GitException:
        puts_err("Not a git repository.")
        exit(128)

    return ret_val


def _init_github(configuration):
    """Initialize GitHub data.

    :param configuration: The GitHub configuration to intialize for.
    """
    token = configuration.get("oauth-token")
    branch = configuration.get("merge-branch")

    if token:
        token = _prompt("GitHub OAuth token", token)
    else:
        user = _prompt("GitHub user", configuration.get("user"))
        password = getpass("GitHub password: ")
        git = Git()
        name = "continuity:{0}".format(git.repo.working_dir)
        url = "https://github.com/jzempel/continuity"
        token = GitHub.create_token(user, password, name, url)

        if not token:
            puts_err("Invalid GitHub credentials.")
            exit(1)

    branch = _prompt("GitHub merge branch", branch)

    return {
        "oauth-token": token,
        "merge-branch": branch
    }


def _init_pivotal(configuration):
    """Initialize pivotal data.

    :param configuration: The git configuration to initialize for.
    """
    token = configuration.get("api-token")
    project_id = configuration.get("project-id")
    email = configuration.get("email")
    owner = configuration.get("owner")
    branch = configuration.get("integration-branch")

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

    if not branch:
        git = Git()
        branch = git.branch.name

    branch = _prompt("Pivotal Tracker story integration branch", branch)

    return {
        "api-token": token,
        "project-id": project_id,
        "email": email,
        "owner": owner,
        "integration-branch": branch
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


def commit(arguments):
    """Git prepare commit message hook.

    :param arguments: Command line arguments.
    """
    commit = arguments.get(0)

    if commit:
        git = Git()

        try:
            story_id = int(git.prefix)

            with open(commit) as file:
                message = file.read()

            message = "[#{0:d}] {1}".format(story_id, message)

            with open(commit, 'w') as file:
                file.write(message)
        except ValueError:
            exit()  # Not committing on a story branch.
    else:
        exit()


def finish(arguments):
    """Handle git request to finish a story branch.

    :param arguments: Command line arguments.
    """
    git = _git()

    try:
        branch = git.branch.name
        story_id = int(git.prefix)
        message = "[finish #{0:d}]".format(story_id)
        configuration = git.get_configuration("pivotal")

        if configuration:
            target = configuration.get("integration-branch")
        else:
            target = None

        git.merge_branch(target, message)
        puts("Merged branch '{0}' into {1}.".format(branch, git.branch.name))
        git.delete_branch(branch)
        puts("Deleted branch {0}.".format(branch))
        git.push_branch()
        puts("Finished story #{0:d}.".format(story_id))
    except ValueError:
        puts_err("Not a story branch.")
        exit(128)


def init(arguments):
    """Initialize a git repository for use with continuity.

    :param arguments: Command line arguments
    """
    git = _git()

    try:
        puts("Enter values or accept [defaults] with Enter.")
        puts()
        pivotal = _init_pivotal(git.get_configuration("pivotal"))
        puts()
        configuration = git.get_configuration("github")
        configuration["merge-branch"] = pivotal.get("integration-branch")
        github = _init_github(configuration)
    except KeyboardInterrupt:
        puts()
        puts("Initialization aborted. Changes NOT saved.")
        exit()

    puts()
    puts("continuity git configuration:")

    with indent():
        for key, value in pivotal.iteritems():
            puts("pivotal.{0}={1}".format(key, value))

        for key, value in github.iteritems():
            puts("github.{0}={1}".format(key, value))

    git.set_configuration("pivotal", pivotal)
    git.set_configuration("github", github)
    aliases = {
        "finish": "!continuity finish \"$@\"",
        "review": "!continuity review \"$@\"",
        "story": "!continuity story \"$@\""
    }
    git.set_configuration("alias", aliases)
    filename = "{0}/hooks/prepare-commit-msg".format(git.repo.git_dir)

    with open(filename, 'w') as hook:
        hook.write('#!/bin/sh\n\ncontinuity commit "$@"')

    chmod(filename, 0755)
    exit()


def main():
    """Main entry point.
    """
    command = args.get(0)

    if command in commands:
        args.remove(command)
        commands[command].__call__(args)


def review(arguments):
    """Handle github branch pull request.

    :param arguments: Command line arguments.
    """
    git = _git()
    configuration = git.get_configuration("github")

    if configuration:
        try:
            token = configuration["oauth-token"]
        except KeyError, e:
            puts_err("Missing 'github.{0}' git configuration.".\
                    format(e.message))
            exit(1)

        try:
            github = GitHub(git, token)
            title = '-'.join(git.branch.name.split('-')[1:])
            message = "Pull request title [{0}]: ".format(title)
            title = raw_input(message) or title
            description = raw_input("Pull request description (optional): ")
            git.push_branch()
            branch = configuration.get("merge-branch")
            pull_request = github.create_pull_request(title, description,
                    branch)
            puts("Opened pull request: {0}".format(pull_request["url"]))
        except GitHubException, e:
            puts_err("Unable to create pull request.")
            exit(128)
    else:
        puts_err("Missing 'github' git configuration.")


def story(arguments):
    """Handle git branching and story state for the next story in PT.

    :param arguments: Command line arguments.
    """
    git = _git()
    configuration = git.get_configuration("pivotal")

    if configuration:
        try:
            token = configuration["api-token"]
            project_id = configuration["project-id"]
            owner = configuration["owner"]
        except KeyError, e:
            puts_err("Missing 'pivotal.{0}' git configuration.".\
                    format(e.message))
            exit(1)

        pt = PivotalTracker(token)
        filter = "owner:{0} state:unstarted,rejected".format(owner)
        puts("Retrieving next story from Pivotal Tracker for {0}…".\
                format(owner))
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
                message = "Enter branch name: {0:d}-".format(story.id)

                try:
                    suffix = raw_input(message)
                    name = "{0:d}-{1}".format(story.id, suffix)
                    git.create_branch(name)
                    pt.set_story(project_id, story.id, "started")
                    puts("Switched to a new branch '{0}'".format(name))
                except KeyboardInterrupt:
                    puts()
                    puts("Aborted story branch!")
            else:
                puts("Unable to update story owner.")
        else:
            puts("No estimated stories found in the backlog.")
    else:
        puts_err("Missing 'pivotal' git configuration.")
        exit(1)


commands = {
    "commit": commit,
    "finish": finish,
    "init": init,
    "review": review,
    "story": story
}
