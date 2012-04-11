# -*- coding: utf-8 -*-
"""
    pt
    ~~

    Pivotal Tracker API.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime
from requests import request
from urlparse import urljoin
from xml.dom import minidom


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

    :param api_token: The API token to use.
    :param project_id: The ID of the project to use.
    """

    URI_TEMPLATE = "https://www.pivotaltracker.com/services/v3/projects/{0:d}/"

    def __init__(self, api_token, project_id):
        self.api_token = api_token
        self.project_id = int(project_id)

    def get_story(self, filter):
        """Get the next story for the given filter.

        :param filter: The PT API filter. See
            `https://www.pivotaltracker.com/help#howcanasearchberefined` for
            details.
        """
        stories = self.get_xml("stories", filter=filter, limit=1)
        count = stories.attributes["count"]

        if int(count.value) == 1:
            story = stories.getElementsByTagName("story")[0]
            ret_val = Story(story)
        else:
            ret_val = None

        return ret_val

    def get_xml(self, path, method="GET", **parameters):
        """Get XML for the given path.

        :param path: The path to get XML for.
        :param method: Default ``'GET'``. The HTTP method to use.
        :param parameters: Query parameters.
        """
        url = urljoin(self.URI_TEMPLATE.format(self.project_id), path)
        headers = {"X-TrackerToken": self.api_token}

        if method != "GET":
            headers["Content-Length"] = '0'

        response = request(method, url, params=parameters, headers=headers)
        xml = minidom.parseString(response.content)

        return xml.firstChild

    def set_story(self, id, state, owner=None):
        """Set the state of the story for the given ID.

        :param id: The ID of the story to update.
        :param state: The updated story state: ``'unscheduled'``,
            ``'unstarted'``, ``'started'``, ``'finished'``, ``'delivered'``,
            ``'accepted'``, or ``'rejected'``.
        :param owner: Default `None`. Optional story owner.
        """
        path = "stories/{0}".format(id)
        parameters = {"story[current_state]": state}

        if owner:
            parameters["story[owned_by]"] = owner

        story = self.get_xml(path, method="PUT", **parameters)

        return Story(story)
