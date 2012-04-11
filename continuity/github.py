# -*- coding: utf-8 -*-
"""
    github
    ~~~~~~

    GitHub API.

    :copyright: 2012 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from json import dumps, loads
from requests import post, RequestException
import re


class GitHubException(Exception):
    """Base GitHub exception.
    """


class GitHub(object):
    """GitHub service.

    :param git: Git object instance.
    :param user: GitHub user name.
    :param password: GitHub password.
    """

    PATTERN_REPOSITORY = re.compile(r"^.+:(?P<repository>\w+/\w+)\.git$", re.U)
    URI_TEMPLATE = "https://api.github.com/{0}"

    def __init__(self, git, user, password):
        if git.remote and "github.com" in git.remote.url:
            self.git = git
            self.user = user
            self.password = password
        else:
            raise GitHubException("No github remote configured.")

    def create_pull_request(self, title, description=None, branch=None):
        """Create a pull request.

        :param title: The title for this pull request.
        :param description: Default `None`. The optional description of this
            pull request.
        :param branch: Default `None`. The base branch the pull request is for.
        """
        match = re.match(self.PATTERN_REPOSITORY, self.git.remote.url)
        repository = match.group("repository")
        path = "repos/{0}/pulls".format(repository)
        url = self.URI_TEMPLATE.format(path)
        data = {
            "title": title,
            "body": description,
            "head": self.git.branch.name,
            "base": branch or "master"
        }
        response = post(url, data=dumps(data), auth=(self.user, self.password))

        try:
            response.raise_for_status()
        except RequestException, e:
            raise GitHubException(e)

        return loads(response.content)
