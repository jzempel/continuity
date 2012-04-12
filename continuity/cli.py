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
from sys import argv, exit


def _git():
    """Get git.
    """
    try:
        ret_val = Git()
    except GitException:
        print "Not a git repository."
        exit(128)

    return ret_val


def commit():
    """Git prepare commit message hook.
    """
    if len(argv) >= 2:
        git = Git()

        try:
            story_id = int(git.prefix)

            with open(argv[1]) as file:
                message = file.read()

            message = "[#{0:d}] {1}".format(story_id, message)

            with open(argv[1], 'w') as file:
                file.write(message)
        except ValueError:
            exit(0)  # Not committing on a story branch.
    else:
        exit(0)


def finish():
    """Handle git request to finish a story branch.
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
        print "Merged branch '{0}' into {1}.".format(branch, git.branch.name)
        git.delete_branch(branch)
        print "Deleted branch {0}.".format(branch)
        git.push_branch()
        print "Finished story #{0:d}.".format(story_id)
    except ValueError:
        print "Not a story branch."
        exit(128)


def review():
    """Handle github branch pull request.
    """
    git = _git()
    configuration = git.get_configuration("github")

    if configuration:
        try:
            user = configuration["user"]
            password = configuration["password"]
        except KeyError, e:
            print "Missing 'github.{0}' git configuration.".format(e.message)
            exit(1)

        try:
            github = GitHub(git, user, password)
            title = '-'.join(git.branch.name.split('-')[1:])
            message = "Pull request title [{0}]: ".format(title)
            title = raw_input(message) or title
            description = raw_input("Pull request description (optional): ")
            git.push_branch()
            branch = configuration.get("merge-branch")
            pull_request = github.create_pull_request(title, description,
                    branch)
            print "Opened pull request: {0}".format(pull_request["url"])
        except GitHubException, e:
            print "Unable to create pull request."
            exit(128)
    else:
        print "Missing 'github' git configuration."


def story():
    """Handle git branching and story state for the next story in PT.
    """
    git = _git()
    configuration = git.get_configuration("pivotal")

    if configuration:
        try:
            api_token = configuration["api-token"]
            project_id = configuration["project-id"]
            owner = configuration["owner"]
        except KeyError, e:
            print "Missing 'pivotal.{0}' git configuration.".\
                    format(e.message)
            exit(1)

        pt = PivotalTracker(api_token, project_id)
        filter = "owner:{0} state:unstarted,rejected".format(owner)
        print "Retrieving next story from Pivotal Tracker for {0}…".\
                format(owner)
        story = pt.get_story(filter)

        if not story:
            filter = "state:unstarted"
            story = pt.get_story(filter)

        if story:
            print "Story: {0}".format(story.name)

            if story.owner != owner:
                story = pt.set_story(story.id, story.state, owner)

            # Verify that owner got the story.
            if story.owner == owner:
                message = "Enter branch name: {0:d}-".format(story.id)

                try:
                    suffix = raw_input(message)
                    name = "{0:d}-{1}".format(story.id, suffix)
                    git.create_branch(name)
                    pt.set_story(story.id, "started")
                    print "Switched to a new branch '{0}'".format(name)
                except KeyboardInterrupt:
                    print "\nCancelled story branch!"
            else:
                print "Unable to update story owner."
        else:
            print "No estimated stories found in the backlog."
    else:
        print "Missing 'pivotal' git configuration."
