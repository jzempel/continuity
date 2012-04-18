# -*- coding: utf-8 -*-
"""
    pt
    ~~

    Pivotal Tracker API.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime
from requests import get, request, RequestException
from urlparse import urljoin
from xml.dom import minidom


class Person(object):
    """Pivotal Tracker person object.

    :param person: Person DOM element.
    """

    def __init__(self, person):
        self.person = person

    @property
    def email(self):
        """Person email accessor.
        """
        element = self.person.getElementsByTagName("email")[0]

        return element.firstChild.nodeValue

    @property
    def initials(self):
        """Person initials accessor.
        """
        element = self.person.getElementsByTagName("initials")[0]

        return element.firstChild.nodeValue

    @property
    def name(self):
        """Person name accessor.
        """
        element = self.person.getElementsByTagName("name")[0]

        return element.firstChild.nodeValue


class Member(Person):
    """Pivotal Tracker member object.

    :param member: Member DOM element.
    """

    def __init__(self, member):
        self.member = member
        person = member.getElementsByTagName("person")[0]

        super(Member, self).__init__(person)

    @property
    def id(self):
        """Member ID accessor.
        """
        element = self.member.getElementsByTagName("id")[0]
        value = element.firstChild.nodeValue

        return int(value)

    @property
    def role(self):
        """Member role accessor.
        """
        element = self.member.getElementsByTagName("role")[0]

        return element.firstChild.nodeValue


class Project(object):
    """Pivotal Tracker project object.

    :param project: Project DOM element.
    """

    def __init__(self, project):
        self.project = project

    @property
    def id(self):
        """Project ID accessor.
        """
        element = self.project.getElementsByTagName("id")[0]
        value = element.firstChild.nodeValue

        return int(value)

    @property
    def members(self):
        """Project membership accessor.
        """
        ret_val = []
        element = self.project.getElementsByTagName("memberships")[0]
        memberships = element.getElementsByTagName("membership")

        for membership in element.getElementsByTagName("membership"):
            member = Member(membership)
            ret_val.append(member)

        return ret_val

    @property
    def name(self):
        """Project name accessor.
        """
        element = self.project.getElementsByTagName("name")[0]

        return element.firstChild.nodeValue


class Story(object):
    """Pivotal Tracker story object.

    :param story: Story DOM element.
    """

    FORMAT_DATETIME = "%Y/%m/%d %H:%M:%S %Z"

    def __init__(self, story):
        self.story = story

    @property
    def created(self):
        """Story created accessor.
        """
        element = self.story.getElementsByTagName("created_at")[0]
        value = element.firstChild.nodeValue

        return datetime.strptime(value, self.FORMAT_DATETIME)

    @property
    def description(self):
        """Story description accessor.
        """
        element = self.story.getElementsByTagName("description")[0]
        text = element.firstChild

        return text.nodeValue if text else None

    @property
    def id(self):
        """Story ID accessor.
        """
        element = self.story.getElementsByTagName("id")[0]
        value = element.firstChild.nodeValue

        return int(value)

    @property
    def name(self):
        """Story name accessor.
        """
        element = self.story.getElementsByTagName("name")[0]

        return element.firstChild.nodeValue

    @property
    def owner(self):
        """Story owner accessor.
        """
        elements = self.story.getElementsByTagName("owned_by")

        if elements:
            ret_val = elements[0].firstChild.nodeValue
        else:
            ret_val = None

        return ret_val

    @property
    def requester(self):
        """Story requester accessor.
        """
        element = self.story.getElementsByTagName("requested_by")[0]

        return element.firstChild.nodeValue

    @property
    def state(self):
        """Story state accessor.
        """
        element = self.story.getElementsByTagName("current_state")[0]

        return element.firstChild.nodeValue

    @property
    def type(self):
        """Story type accessor.
        """
        element = self.story.getElementsByTagName("story_type")[0]

        return element.firstChild.nodeValue

    @property
    def updated(self):
        """Story updated accessor.
        """
        elements = self.story.getElementsByTagName("updated_at")

        if elements:
            value = elements[0].firstChild.nodeValue
            ret_val = datetime.strptime(value, self.FORMAT_DATETIME)
        else:
            ret_val = None

        return ret_val


class PivotalTracker(object):
    """Pivotal Tracker service.

    :param token: The API token to use.
    """

    API_URL = "https://www.pivotaltracker.com/services/v3/"

    def __init__(self, token):
        self.token = token

    def get_project(self, id):
        """Get a project for the given ID.

        :param id: The ID of the project to get.
        """
        path = "projects/{0}".format(id)
        project = self.get_xml(path)

        if project.tagName == "project":
            ret_val = Project(project)
        else:
            ret_val = None

        return ret_val

    def get_projects(self):
        """Get a list of projects.
        """
        ret_val = []
        projects = self.get_xml("projects")

        for project in projects.getElementsByTagName("project"):
            ret_val.append(Project(project))

        return ret_val

    def get_story(self, project_id, filter):
        """Get the next story for the given filter.

        :param project_id: The ID of the project to use.
        :param filter: The PT API filter. See
            `https://www.pivotaltracker.com/help#howcanasearchberefined` for
            details.
        """
        path = "projects/{0:d}/stories".format(project_id)
        filter = "type:feature,chore,bug {0}".format(filter)
        stories = self.get_xml(path, filter=filter, limit=1)
        count = stories.attributes["count"]

        if int(count.value) == 1:
            story = stories.getElementsByTagName("story")[0]
            ret_val = Story(story)
        else:
            ret_val = None

        return ret_val

    @staticmethod
    def get_token(user, password):
        """Get an active token for the given user.

        :param user: The user to get a token for.
        :param password: The user password.
        """
        url = urljoin(PivotalTracker.API_URL, "tokens/active")
        auth = (user, password)
        response = get(url, auth=auth)

        try:
            response.raise_for_status()
            xml = minidom.parseString(response.content)
            element = xml.firstChild.getElementsByTagName("guid")[0]
            ret_val = element.firstChild.nodeValue
        except RequestException:
            ret_val = None

        return ret_val

    def get_xml(self, path, method="GET", **parameters):
        """Get XML for the given path.

        :param path: The path to get XML for.
        :param method: Default ``'GET'``. The HTTP method to use.
        :param parameters: Query parameters.
        """
        url = urljoin(self.API_URL, path)
        headers = {"X-TrackerToken": self.token}

        if method != "GET":
            headers["Content-Length"] = '0'

        response = request(method, url, params=parameters, headers=headers)
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
        path = "projects/{0:d}/stories/{1:d}".format(project_id, id)
        parameters = {"story[current_state]": state}

        if owner:
            parameters["story[owned_by]"] = owner

        story = self.get_xml(path, method="PUT", **parameters)

        return Story(story)
