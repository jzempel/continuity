# -*- coding: utf-8 -*-
"""
    continuity.cli.pt
    ~~~~~~~~~~~~~~~~~

    Continuity Pivotal Tracker CLI commands.

    :copyright: 2013 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import (cached_property, FinishCommand as BaseFinishCommand,
        GitCommand, prompt, ReviewCommand as BaseReviewCommand,
        StartCommand as BaseStartCommand)
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
    """List backlog stories.
    """

    def execute(self, namespace):
        """Execute this backlog command.

        :param namespace: Command-line argument namespace.
        """
        owner = self.get_value("pivotal", "owner")
        stories = self.pt.get_backlog(self.project)
        output = StringIO()

        for story in stories:
            if story.state in [Story.STATE_UNSCHEDULED,
                    Story.STATE_UNSTARTED] and (namespace.mywork is False
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

    def initialize(self, parser):
        """Initialize the backlog command.

        :param parser: Command-line argument parser.
        """
        parser.add_argument("-m", "--mywork", action="store_true",
                help="list stories owned by you")


class FinishCommand(BaseFinishCommand, PivotalTrackerCommand):
    """Finish a story branch.
    """

    def finalize(self):
        """Finalize this finish command.
        """
        self.pt.set_story(self.project, self.story, Story.STATE_FINISHED)
        puts("Finished story #{0:d}.".format(self.story.id))
        super(FinishCommand, self).finalize()

    def initialize(self, parser):
        """Initialize this finish command.

        :param parser: Command-line argument parser.
        """
        super(FinishCommand, self).initialize(parser)
        self.message = "[finish #{0:d}]".format(self.story.id)


class ReviewCommand(BaseReviewCommand, PivotalTrackerCommand):
    """Open a GitHub pull request for story branch review.
    """

    def initialize(self, parser):
        """Initialize this review command.

        :param parser: Command-line argument parser.
        """
        super(ReviewCommand, self).initialize(parser)
        self.title_or_number = prompt("Pull request title",
                self.git.branch.name)
        description = raw_input("Pull request description (optional): ")

        if description:
            self.description = "{0}\n\n{1}".format(self.story.url, description)
        else:
            self.description = self.story.url


class StoryCommand(PivotalTrackerCommand):
    """Display story branch information.
    """

    def execute(self, namespace):
        """Execute the story command.

        :param namespace: Command-line argument namespace.
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


class StartCommand(BaseStartCommand, PivotalTrackerCommand):
    """Start a branch linked to a story.
    """

    def execute(self, namespace):
        """Execute this start command.

        :param namespace: Command-line argument namespace.
        """
        self.namespace = namespace

        if self.story:
            puts("Story: {0}".format(self.story.name))
            owner = self.get_value("pivotal", "owner")

            if self.story.owner is None:
                self.story = self.pt.set_story(self.project, self.story,
                        self.story.state, owner)

            # Verify that owner got the story.
            if self.story.owner == owner:
                branch = super(StartCommand, self).execute(namespace)
                self.git.set_configuration("branch", branch,
                        story=self.story.id)
                self.pt.set_story(self.project, self.story,
                        Story.STATE_STARTED)
            else:
                exit("Unable to update story owner.")
        else:
            if namespace.id and namespace.exclusive:
                exit("No estimated story #{0} found assigned to you.".format(
                    namespace.id))
            elif namespace.id:
                exit("No estimated story #{0} found in the backlog.".format(
                    namespace.id))
            elif namespace.exclusive:
                exit("No estimated stories found in my work.")
            else:
                exit("No estimated stories found in the backlog.")

    def exit(self):
        """Handle start command exit.
        """
        puts("Aborted story branch.")
        super(StartCommand, self).exit()

    def initialize(self, parser):
        """Initialize this start command.

        :param parser: Command-line argument parser.
        """
        parser.add_argument("-i", "--id", help="start the specified story",
                type=int)
        parser.add_argument("-m", "--mywork", action="store_true",
                help="only start stories owned by you")
        super(StartCommand, self).initialize(parser)

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


class TasksCommand(PivotalTrackerCommand):
    """List and manage story tasks.
    """

    def execute(self, namespace):
        """Execute the tasks command.

        :param namespace: Command-line argument namespace.
        """
        tasks = self.pt.get_tasks(self.project, self.story)

        if namespace.check or namespace.uncheck:
            number = int(namespace.check or namespace.uncheck) - 1
            task = tasks[number]
            checked = True if namespace.check else False
            task = self.pt.set_task(self.project, self.story, task, checked)
            tasks[number] = task

        for task in tasks:
            checkmark = 'x' if task.is_checked else ' '
            message = "[{0}] {1}. {2}".format(checkmark, task.number,
                    task.description)
            puts(message)

    def initialize(self, parser):
        """Initialize this Pivotal Tracker tasks command.

        :param parser: Command-line argument parser.
        """
        parser.add_argument("-x", "--check", metavar="number")
        parser.add_argument("-o", "--uncheck", metavar="number")


commands = {
    "backlog": BacklogCommand(),
    "finish": FinishCommand(),
    "review": ReviewCommand(),
    "story": StoryCommand(),
    "start": StartCommand(),
    "tasks": TasksCommand()
}
