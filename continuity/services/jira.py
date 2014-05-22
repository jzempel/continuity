# -*- coding: utf-8 -*-
"""
    continuity.services.jira
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Jira API.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from .commons import RemoteService, ServiceException
from requests import RequestException
from requests.auth import _basic_auth_str
from urlparse import urljoin


class JiraException(ServiceException):
    """Base Jira exception.
    """


class JiraService(RemoteService):
    """Jira service.

    :param base: The service base URL.
    :param token: The authentication token to use.
    """

    URI = "/rest/api/2/"

    def __init__(self, base, token):
        url = urljoin(base, JiraService.URI)
        super(JiraService, self).__init__(url)
        self.token = token

    def _request(self, method, resource, **kwargs):
        """Send a Jira request.

        :param method: The HTTP method.
        :param resource: The URI resource.
        :param kwargs: Request keyword-arguments.
        """
        headers = kwargs.get("headers", {})
        headers["Authorization"] = "Basic {0}".format(self.token)
        kwargs["headers"] = headers

        try:
            ret_val = super(JiraService, self)._request(method, resource,
                    **kwargs)
        except RequestException, e:
            raise JiraException(e)

        return ret_val

    @staticmethod
    def get_token(user, password):
        """Get an auth token for the given user.

        :param user: The user name to get a token for.
        :param password: The user password.
        """
        token = _basic_auth_str(user, password)

        return token.split(None, 1)[-1]

    def get_user(self, name=None):
        """Get a user.

        :param name: Default `None`. Optional user name, otherwise get the
            authenticated user.
        """
        resource = "user" if name else "myself"
        self._request("get", resource)
