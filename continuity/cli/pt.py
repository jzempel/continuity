# -*- coding: utf-8 -*-
"""
    continuity.cli.pt
    ~~~~~~~~~~~~~~~~~

    Continuity Pivotal Tracker CLI commands.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import (FinishCommand as BaseFinishCommand, GitCommand,
        ReviewCommand as BaseReviewCommand, StartCommand as BaseStartCommand,
        TasksCommand as BaseTasksCommand)
from .utils import cached_property, prompt
from clint.textui import colored, puts
from continuity.pt import PivotalTracker, Story
from pydoc import pipepager
from StringIO import StringIO
from sys import exit


class PivotalTrackerCommand(GitCommand):
    """Base Pivotal Tracker command.
    """

    @cached_property
    def project(self):
        """Project accessor.
        """
        id = self.get_value("pivotal", "project-id")

        return self.pt.get_project(id)

    @cached_property
    def pt(self):
        """Pivotal Tracker accessor.
        """
        token = self.get_value("pivotal", "api-token")

        return PivotalTracker(token)

    @cached_property
    def story(self):
        """Current branch story accessor.
        """
        configuration = self.git.get_configuration("branch",
                self.git.branch.name)

        if configuration:
            try:
                id = configuration["story"]
                filter = "id:{0}".format(id)
                ret_val = self.pt.get_story(self.project, filter)
            except KeyError:
                ret_val = None
        else:
            ret_val = None

        if not ret_val:
            exit("fatal: Not a story branch.")

        return ret_val


class BacklogCommand(PivotalTrackerCommand):
    """List unstarted backlog stories.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "backlog"

    def __init__(self, parser, namespace):
        parser.add_argument("-m", "--mywork", action="store_true",
                help="list stories owned by you")
        super(BacklogCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this backlog command.
        """
        owner = self.get_value("pivotal", "owner")
        stories = self.pt.get_backlog(self.project)
        output = StringIO()

        for story in stories:
            if story.state in [Story.STATE_UNSCHEDULED,
                    Story.STATE_UNSTARTED] and (self.namespace.mywork is False
                            or story.owner == owner):
                id = colored.yellow(str(story.id))

                if story.estimate is None:
                    type = story.type.upper()
                elif story.estimate >= 0:
                    type = "{0} ({1:d})".format(story.type.upper(),
                            story.estimate)
                else:
                    type = "{0} (?)".format(story.type.upper())

                name = story.name

                if story.owner:
                    for member in self.project.members:
                        if member.name == story.owner:
                            name = "{0} ({1})".format(story.name,
                                    member.initials)
                            break

                message = "{0} {1}: {2}\n".format(id, type, name)
                output.write(message)

        pipepager(output.getvalue(), cmd="less -FRSX")


class FinishCommand(BaseFinishCommand, PivotalTrackerCommand):
    """Finish a story branch.
    """

    def _merge_branch(self, branch, *args):
        """Merge a branch.

        :param branch: The name of the branch to merge.
        :param *args: Merge argument list.
        """
        try:
            self.git.get_branch(branch)
            self.story  # Cache the branch story.
        finally:
            self.git.get_branch(self.branch)

        message = "[finish #{0:d}]".format(self.story.id)
        self.git.merge_branch(branch, message, args)

    def finalize(self):
        """Finalize this finish command.
        """
        self.pt.set_story(self.project, self.story, Story.STATE_FINISHED)
        puts("Finished story #{0:d}.".format(self.story.id))
        super(FinishCommand, self).finalize()


class ReviewCommand(BaseReviewCommand, PivotalTrackerCommand):
    """Open a GitHub pull request for story branch review.
    """

    def _create_pull_request(self, branch):
        """Create a pull request.

        :param branch: The base branch the pull request is for.
        """
        title = prompt("Pull request title", self.git.branch.name)
        description = raw_input("Pull request description (optional): ")

        if description:
            self.description = "{0}\n\n{1}".format(self.story.url, description)
        else:
            self.description = self.story.url

        return self.github.create_pull_request(title, description, branch)


class StoryCommand(PivotalTrackerCommand):
    """Display story branch information.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    name = "story"

    def __init__(self, parser, namespace):
        parser.add_argument("-c", "--comments", action="store_true",
                help="include story comments")
        super(StoryCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute the story command.
        """
        puts(self.story.name)
        puts()

        if self.story.estimate is None:
            puts(self.story.type.capitalize())
        elif self.story.estimate >= 0:
            puts("{0} Estimate: {1:d} points".format(
                self.story.type.capitalize(), self.story.estimate))
        else:
            puts("{0} Unestimated.".format(self.story.type.capitalize()))

        if self.story.description:
            puts()
            puts(colored.cyan(self.story.description))

        puts()
        puts(colored.white("Requested by {0} on {1}".format(
            self.story.requester,
            self.story.created.strftime("%d %b %Y, %I:%M%p"))))
        puts(colored.white(self.story.url))

        if self.namespace.comments:
            for comment in self.story.comments:
                puts()
                puts(colored.yellow("{0} ({1})".format(comment.author,
                    comment.created)))
                puts()
                puts(comment.text)


class StartCommand(BaseStartCommand, PivotalTrackerCommand):
    """Start a branch linked to a story.

    :param parser: Command-line argument parser.
    :param namespace: Command-line argument namespace.
    """

    def __init__(self, parser, namespace):
        parser.add_argument("id", help="start the specified story", nargs='?',
                type=int)
        parser.add_argument("-m", "--mywork", action="store_true",
                help="only start stories owned by you")
        super(StartCommand, self).__init__(parser, namespace)

    def execute(self):
        """Execute this start command.
        """
        if self.story:
            puts("Story: {0}".format(self.story.name))
            owner = self.get_value("pivotal", "owner")

            if self.story.owner is None:
                self.story = self.pt.set_story(self.project, self.story,
                        self.story.state, owner)

            # Verify that owner got the story.
            if self.story.owner == owner:
                branch = super(StartCommand, self).execute()
                self.git.set_configuration("branch", branch,
                        story=self.story.id)
                self.pt.set_story(self.project, self.story,
                        Story.STATE_STARTED)
            else:
                exit("Unable to update story owner.")
        else:
            if self.namespace.id and self.namespace.exclusive:
                exit("No estimated story #{0} found assigned to you.".format(
                    self.namespace.id))
            elif self.namespace.id:
                exit("No estimated story #{0} found in the backlog.".format(
                    self.namespace.id))
            elif self.namespace.exclusive:
                exit("No estimated stories found in my work.")
            else:
                exit("No estimated stories found in the backlog.")

    def exit(self):
        """Handle start command exit.
        """
        puts("Aborted story branch.")
        super(StartCommand, self).exit()

    @cached_property
    def story(self):
        """Target story accessor.
        """
        story_id = self.namespace.id
        exclusive = self.namespace.exclusive
        owner = self.get_value("pivotal", "owner")

        if story_id and exclusive:
            puts("Retrieving story #{0} from Pivotal Tracker for {1}...".
                format(story_id, owner))
            filter = "id:{0} owner:{1} state:unstarted,rejected".format(
                story_id, owner)
        elif story_id:
            puts("Retrieving story #{0} from Pivotal Tracker...".format(
                story_id))
            filter = "id:{0} state:unstarted,rejected".format(story_id)
        elif exclusive:
            puts("Retrieving next story from Pivotal Tracker for {0}...".
                format(owner))
            filter = "owner:{0} state:unstarted,rejected".format(owner)
        else:
            filter = None

        if filter:
            ret_val = self.pt.get_story(self.project, filter)
        else:
            puts("Retrieving next available story from Pivotal Tracker...")
            stories = self.pt.get_backlog(self.project)

            for story in stories:
                if story.type in (Story.TYPE_FEATURE, Story.TYPE_BUG,
                        Story.TYPE_CHORE) and (story.owner is None or
                        story.owner == owner):
                    ret_val = story
                    break
            else:
                ret_val = None

        return ret_val


class TasksCommand(BaseTasksCommand, PivotalTrackerCommand):
    """List and manage story tasks.
    """

    def _get_tasks(self):
        """Task list accessor.
        """
        return self.pt.get_tasks(self.project, self.story)

    def _set_task(self, task, checked):
        """Task mutator.

        :param task: The task to update.
        :param checked: ``True`` if the task is complete.
        """
        return self.pt.set_task(self.project, self.story, task, checked)

    def finalize(self):
        """Finalize this tasks command.
        """
        for task in self.tasks:
            checkmark = 'x' if task.is_checked else ' '
            message = "[{0}] {1}. {2}".format(checkmark, task.number,
                    task.description)
            puts(message)
