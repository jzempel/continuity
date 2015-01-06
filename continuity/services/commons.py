# -*- coding: utf-8 -*-
"""
    continuity.services.commons
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Continuity service commons.

    :copyright: 2015 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from json import dumps
from requests import codes, request
from requests.packages.urllib3 import disable_warnings
from urlparse import urljoin


class DataObject(object):
    """Service data object.

    :param data: Object data dictionary.
    """

    def __init__(self, data):
        self.data = data


class IDObject(DataObject):
    """Service ID object.
    """

    def __cmp__(self, other):
        """Compare ID objects.

        :param other: The object to compare to.
        """
        return cmp(self.id, hash(other))

    def __hash__(self):
        """ID object hash value.
        """
        return self.id

    @property
    def id(self):
        """ID accessor.
        """
        return self.data.get("id")


class RemoteService(object):
    """Remote service.

    :param url: Remote service API URL.
    """

    disable_warnings()

    def __init__(self, url):
        self.url = url

    def _request(self, method, resource, **kwargs):
        """Send a service request.

        :param method: The HTTP method.
        :param resource: The URI resource.
        :param kwargs: Request keyword-arguments.

        :raises: `RequestException` if there was a problem with the request.
        """
        url = urljoin(self.url, resource)
        kwargs["verify"] = False

        if "data" in kwargs:
            kwargs["data"] = dumps(kwargs["data"])

        response = request(method, url, **kwargs)
        response.raise_for_status()

        if response.status_code == codes.no_content:
            ret_val = None
        else:
            ret_val = response.json()

        return ret_val


class ServiceException(Exception):
    """Service exception.
    """
