# -*- coding: utf-8 -*-
"""
    continuity.pt
    ~~~~~~~~~~~~~

    Pivotal Tracker API.

    :copyright: 2012 by Jonathan Zempel.
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

    :param project: Project DOM element.
    """

    def __init__(self, project):
        super(Project, self).__init__(project)

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

    :param story: Story DOM element.
    """

    def __init__(self, story):
        super(Story, self).__init__(story)

    @datetime_property
    def created(self):
        """Story created accessor.
        """
        return self.child("created_at").value

    @property
    def description(self):
        """Story description accessor.
        """
        return self.child("description").value

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

    :param task: Task DOM element.
    """

    def __init__(self, task):
        super(Task, self).__init__(task)

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

    def get_story(self, project_id, filter):
        """Get the next story for the given filter.

        :param project_id: The ID of the project to use.
        :param filter: The PT API filter. See
            `https://www.pivotaltracker.com/help#howcanasearchberefined` for
            details.
        """
        project = self.get_project(project_id)
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

    def get_tasks(self, project_id, story_id):
        """Get the tasks for the given story.

        :param project_id: The ID of the project to use.
        :param story_id: The ID of the story to use.
        """
        ret_val = []
        project = self.get_project(project_id)
        filter = "id:{0:d}".format(int(story_id))
        story = self.get_story(project.id, filter)

        if story:
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

    def set_story(self, project_id, id, state, owner=None):
        """Set the state of the story for the given ID.

        :param project_id: The ID of the project to use.
        :param id: The ID of the story to update.
        :param state: The updated story state: ``'unscheduled'``,
            ``'unstarted'``, ``'started'``, ``'finished'``, ``'delivered'``,
            ``'accepted'``, or ``'rejected'``.
        :param owner: Default `None`. Optional story owner.
        """
        project = self.get_project(project_id)
        s = 's' if project.is_secure else ''
        path = "projects/{0:d}/stories/{1:d}".format(project.id, id)
        url = self.URI_TEMPLATE.format(s=s, path=path)
        parameters = {"story[current_state]": state}

        if owner:
            parameters["story[owned_by]"] = owner

        story = self.get_xml(url, method="PUT", **parameters)

        return Story(story)
