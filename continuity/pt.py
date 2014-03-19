# -*- coding: utf-8 -*-
"""
    continuity.pt
    ~~~~~~~~~~~~~

    Pivotal Tracker API.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime
from requests import get, request, RequestException
from xml.dom import minidom


class datetime_property(object):
    """Date/time property decorator.

    :param function: The function to decorate.
    """

    FORMAT_DATETIME = "%Y/%m/%d %H:%M:%S %Z"

    def __init__(self, function):
        self.function = function

    def __get__(self, instance, owner):
        """Attribute accessor - converts a Pivotal Tracker date/time value into
        a Python datetime object.

        :param instance: The instance to get an attribute for.
        :param owner: The owner class.
        """
        try:
            value = self.function(instance)
            ret_val = datetime.strptime(value, self.FORMAT_DATETIME)
        except AttributeError:
            ret_val = None

        return ret_val


class Element(object):
    """Pivotal Tracker element object.

    :param element: DOM element.
    """

    def __init__(self, element):
        self.element = element

    def child(self, name):
        """Get a child element.

        :param name: The name of the child element to get.
        """
        children = self.children(name)

        return Element(children[0]) if children else None

    def children(self, name):
        """Get child elements.

        :param name: The name of the children to get.
        """
        return self.element.getElementsByTagName(name)

    @property
    def value(self):
        """Element value accessor.
        """
        child = self.element.firstChild

        return child.nodeValue if child else None


class IDElement(Element):
    """Pivotal Tracker ID element object.
    """

    @property
    def id(self):
        """ID accessor.
        """
        value = self.child("id").value

        return int(value)


class Comment(IDElement):
    """Pivotal Tracker comment object.

    :param member: Comment DOM element.
    """

    @property
    def author(self):
        """Comment author accessor.
        """
        return self.child("author").value

    @datetime_property
    def created(self):
        """Comment created accessor.
        """
        return self.child("noted_at").value

    @property
    def text(self):
        """Comment text accessor.
        """
        return self.child("text").value


class Iteration(IDElement):
    """Pivotal Tracker iteration object.

    :param iteration: Iteration DOM element.
    """

    def __init__(self, iteration):
        super(Iteration, self).__init__(iteration)

    @datetime_property
    def finished(self):
        """Iteration finished accessor.
        """
        return self.child("finish").value

    @property
    def number(self):
        """Iteration number accessor.
        """
        value = self.child("number").value

        return int(value)

    @datetime_property
    def started(self):
        """Iteration started accessor.
        """
        return self.child("start").value

    @property
    def stories(self):
        """Iteration stories accessor.
        """
        ret_val = []
        stories = self.child("stories")

        for story in stories.children("story"):
            story = Story(story)
            ret_val.append(story)

        return ret_val


class Member(IDElement):
    """Pivotal Tracker member object.

    :param member: Member DOM element.
    """

    def __init__(self, member):
        super(Member, self).__init__(member)

        self.person = self.child("person")

    @property
    def email(self):
        """Person email accessor.
        """
        return self.person.child("email").value

    @property
    def initials(self):
        """Person initials accessor.
        """
        return self.person.child("initials").value

    @property
    def name(self):
        """Person name accessor.
        """
        return self.person.child("name").value

    @property
    def role(self):
        """Member role accessor.
        """
        return self.child("role").value


class Project(IDElement):
    """Pivotal Tracker project object.
    """

    @property
    def is_secure(self):
        """Determine if this project requires HTTPS.
        """
        value = self.child("use_https").value

        return value == "true"

    @property
    def members(self):
        """Project membership accessor.
        """
        ret_val = []
        memberships = self.child("memberships")

        for membership in memberships.children("membership"):
            member = Member(membership)
            ret_val.append(member)

        return ret_val

    @property
    def name(self):
        """Project name accessor.
        """
        return self.child("name").value


class Story(IDElement):
    """Pivotal Tracker story object.
    """

    STATE_UNSCHEDULED = "unscheduled"
    STATE_UNSTARTED = "unstarted"
    STATE_STARTED = "started"
    STATE_FINISHED = "finished"
    STATE_DELIVERED = "delivered"
    STATE_ACCEPTED = "accepted"
    STATE_REJECTED = "rejected"
    TYPE_BUG = "bug"
    TYPE_CHORE = "chore"
    TYPE_FEATURE = "feature"
    TYPE_RELEASE = "release"

    @property
    def comments(self):
        """Story comments accessor.
        """
        ret_val = []
        comments = self.child("notes")

        for comment in comments.children("note"):
            comment = Comment(comment)
            ret_val.append(comment)

        return ret_val

    @datetime_property
    def created(self):
        """Story created accessor.
        """
        return self.child("created_at").value

    @property
    def description(self):
        """Story description accessor.
        """
        child = self.child("description")

        return child.value if child else None

    @property
    def estimate(self):
        """Story estimate accessor.
        """
        child = self.child("estimate")

        return int(child.value) if child else None

    @property
    def name(self):
        """Story name accessor.
        """
        return self.child("name").value

    @property
    def owner(self):
        """Story owner accessor.
        """
        child = self.child("owned_by")

        return child.value if child else None

    @property
    def requester(self):
        """Story requester accessor.
        """
        return self.child("requested_by").value

    @property
    def state(self):
        """Story state accessor.
        """
        return self.child("current_state").value

    @property
    def type(self):
        """Story type accessor.
        """
        return self.child("story_type").value

    @datetime_property
    def updated(self):
        """Story updated accessor.
        """
        return self.child("updated_at").value

    @property
    def url(self):
        """Story URL accessor.
        """
        return self.child("url").value


class Task(IDElement):
    """Pivotal Tracker task object.
    """

    @datetime_property
    def created(self):
        """Task created accessor.
        """
        return self.child("created_at").value

    @property
    def description(self):
        """Task description accessor.
        """
        return self.child("description").value

    @property
    def is_checked(self):
        """Determine if this task is checked.
        """
        value = self.child("complete").value

        return value == "true"

    @property
    def number(self):
        """Task number accessor.
        """
        value = self.child("position").value

        return int(value)


class PivotalTracker(object):
    """Pivotal Tracker service.

    :param token: The API token to use.
    """

    URI_TEMPLATE = "http{s}://www.pivotaltracker.com/services/v3/{path}"

    def __init__(self, token):
        self.token = token
        self.projects = []
        url = self.URI_TEMPLATE.format(s='', path="projects")
        projects = self.get_xml(url)

        for project in projects.getElementsByTagName("project"):
            self.projects.append(Project(project))

    def get_backlog(self, project, limit=None):
        """Get a list of stories in the backlog.

        :param project: The project to use.
        :param limit: Limit the number of iterations to get.
        """
        ret_val = []
        s = 's' if project.is_secure else ''
        path = "projects/{0:d}/iterations/current_backlog".format(project.id)

        if limit:
            path = "{0}?limit={1:d}".format(path, limit)

        url = self.URI_TEMPLATE.format(s=s, path=path)
        xml = self.get_xml(url)
        iterations = xml.getElementsByTagName("iteration")

        if not iterations:
            url = url.replace("current_backlog", "backlog", 1)
            xml = self.get_xml(url)
            iterations = xml.getElementsByTagName("iteration")

        for iteration in iterations:
            iteration = Iteration(iteration)
            ret_val.extend(iteration.stories)

        return ret_val

    def get_project(self, id):
        """Get a project for the given ID.

        :param id: The ID of the project to get.
        """
        for project in self.projects:
            if project.id == int(id):
                ret_val = project
                break
        else:
            ret_val = None

        return ret_val

    def get_projects(self):
        """Get a list of projects.
        """
        return self.projects

    def get_story(self, project, filter):
        """Get the next story for the given filter.

        :param project: The project to use.
        :param filter: The PT API filter. See
            `https://www.pivotaltracker.com/help#howcanasearchberefined` for
            details.
        """
        s = 's' if project.is_secure else ''
        path = "projects/{0:d}/stories".format(project.id)
        url = self.URI_TEMPLATE.format(s=s, path=path)
        filter = "type:feature,chore,bug {0}".format(filter)
        stories = self.get_xml(url, filter=filter, limit=1)
        count = stories.attributes["count"]

        if int(count.value) == 1:
            story = stories.getElementsByTagName("story")[0]
            ret_val = Story(story)
        else:
            ret_val = None

        return ret_val

    def get_tasks(self, project, story):
        """Get the tasks for the given story.

        :param project: The project to use.
        :param story: The story to use.
        """
        ret_val = []
        s = 's' if project.is_secure else ''
        path = "projects/{0:d}/stories/{1:d}/tasks".format(project.id,
                story.id)
        url = self.URI_TEMPLATE.format(s=s, path=path)
        tasks = self.get_xml(url)

        for task in tasks.getElementsByTagName("task"):
            ret_val.append(Task(task))

        return ret_val

    @staticmethod
    def get_token(user, password):
        """Get an active token for the given user.

        :param user: The user to get a token for.
        :param password: The user password.
        """
        url = PivotalTracker.URI_TEMPLATE.format(s='s', path="tokens/active")
        auth = (user, password)
        response = get(url, auth=auth, verify=False)

        try:
            response.raise_for_status()
            xml = minidom.parseString(response.content)
            element = xml.firstChild.getElementsByTagName("guid")[0]
            ret_val = element.firstChild.nodeValue
        except RequestException:
            ret_val = None

        return ret_val

    def get_xml(self, url, method="GET", **parameters):
        """Get XML for the given url.

        :param url: The url to get XML for.
        :param method: Default ``'GET'``. The HTTP method to use.
        :param parameters: Query parameters.
        """
        headers = {"X-TrackerToken": self.token}

        if method != "GET":
            headers["Content-Length"] = '0'

        response = request(method, url, params=parameters, headers=headers,
                verify=False)
        xml = minidom.parseString(response.content)

        return xml.firstChild

    def set_story(self, project, story, state, owner=None):
        """Set the state of the story for the given ID.

        :param project: The project to use.
        :param story: The story to update.
        :param state: The updated story state: ``'unscheduled'``,
            ``'unstarted'``, ``'started'``, ``'finished'``, ``'delivered'``,
            ``'accepted'``, or ``'rejected'``.
        :param owner: Default `None`. Optional story owner.
        """
        s = 's' if project.is_secure else ''
        path = "projects/{0:d}/stories/{1:d}".format(project.id, story.id)
        url = self.URI_TEMPLATE.format(s=s, path=path)
        parameters = {"story[current_state]": state}

        if owner:
            parameters["story[owned_by]"] = owner

        story = self.get_xml(url, method="PUT", **parameters)

        return Story(story)

    def set_task(self, project, story, task, checked):
        """Set the completion of the given task.

        :param project: The project to use.
        :param story: The story the task is a part of.
        :param task: The task to update.
        :param checked: ``True`` to check the story as completed, otherwise
            ``False``.
        """
        s = 's' if project.is_secure else ''
        path = "projects/{0:d}/stories/{1:d}/tasks/{2:d}".format(project.id,
                story.id, task.id)
        url = self.URI_TEMPLATE.format(s=s, path=path)

        if checked:
            parameters = {"task[complete]": "true"}
        else:
            parameters = {"task[complete]": "false"}

        task = self.get_xml(url, method="PUT", **parameters)

        return Task(task)
