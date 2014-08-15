# -*- coding: utf-8 -*-
"""
    continuity.cli.utils
    ~~~~~~~~~~~~~~~~~~~~

    Continuity command line utilities.

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from clint.textui import puts
from curses.ascii import ctrl, CR, EOT, ETX, isctrl, LF
from getch.getch import getch
from getpass import getpass
from jinja2 import (Environment, FileSystemLoader, Template, TemplateError,
        TemplateSyntaxError, Undefined as BaseUndefined)
from os.path import basename, dirname, expanduser
from pydoc import pipepager
from shlex import split
from StringIO import StringIO
from subprocess import CalledProcessError, check_call
from sys import exit
from tempfile import NamedTemporaryFile


def confirm(message, default=False):
    """Prompt for confirmation.

    :param message: The confirmation message.
    :param default: Default `False`.
    """
    if default is True:
        options = "Y/n"
    elif default is False:
        options = "y/N"
    else:
        options = "y/n"

    message = "{0} ({1})".format(message, options)
    ret_val = prompt(message, default=default, characters="YN", echo=False)

    if ret_val == 'Y':
        ret_val = True
    elif ret_val == 'N':
        ret_val = False

    return ret_val


def edit(git, default=None, suffix=''):
    """Prompt for edit.

    :param git: Used to determine the editor.
    :param default: Default `None`. The default value.
    :param suffix: Default ''. Temporary file suffix.
    """
    ret_val = None

    with NamedTemporaryFile(suffix=suffix) as temp_file:
        if default:
            temp_file.write(default)
            temp_file.flush()

        args = split(git.editor)
        args.append(temp_file.name)

        try:
            check_call(args)
        except CalledProcessError:
            exit("Unable to start editor '{0}'".format(git.editor))

        with file(temp_file.name) as f:
            ret_val = f.read().strip()

    return ret_val


def less(text):
    """View text via 'less' terminal pager.

    :param text: The text to view.
    """
    if isinstance(text, StringIO):
        text = text.getvalue()

    pipepager(text, cmd="less -FRSX")


def prompt(message, default=None, characters=None, echo=True):
    """Prompt for input.

    :param message: The prompt message.
    :param default: Default `None`. The default input value.
    :param characters: Default `None`. Case-insensitive constraint for single-
        character input.
    :param echo: Default `True`. Determine if input is echoed.
    """
    if default and isinstance(default, basestring):
        message = "{0} [{1}]".format(message, default)

    if characters:
        puts("{0} ".format(message), newline=False)
    else:
        message = "{0}: ".format(message)

    while True:
        if characters:
            ret_val = getch()

            if default is not None and ret_val in (chr(CR), chr(LF)):
                puts()
                ret_val = default
                break
            if ret_val in characters.lower() or ret_val in characters.upper():
                if echo:
                    puts(ret_val)
                else:
                    puts()

                if ret_val not in characters:
                    ret_val = ret_val.swapcase()

                break
            elif isctrl(ret_val) and ctrl(ret_val) in (chr(ETX), chr(EOT)):
                raise KeyboardInterrupt
        else:
            if echo:
                get_input = raw_input
            else:
                get_input = getpass

            ret_val = get_input(message).strip() or default

            if ret_val is not None:
                break

    return ret_val


def render(template, **context):
    """Render the given template.

    :param template: The template file name or string to render.
    :param **context: Context keyword-arguments.
    """
    class Undefined(BaseUndefined):
        def _fail_with_undefined_error(self, *args, **kwargs):
            try:
                super(Undefined, self)._fail_with_undefined_error(*args,
                        **kwargs)
            except Exception, error:
                return "{{{{ {0} }}}}".format(error)

    try:
        try:
            template_file = file(expanduser(template))
            loader = FileSystemLoader(dirname(template_file.name))
            environment = Environment(loader=loader, undefined=Undefined)

            try:
                template = environment.get_template(basename(
                    template_file.name))
            except TemplateSyntaxError, error:
                message = "Template {0}:{1}, {2}{3}".format(error.filename,
                    error.lineno, error.message[:1].lower(), error.message[1:])
                exit(message)
        except IOError:
            try:
                template = Template(template, undefined=Undefined)
            except TemplateSyntaxError, error:
                message = "Template \"{0}\" {1}{2}".format(template,
                    error.message[:1].lower(), error.message[1:])
                exit(message)
    except TemplateError, error:
        message = "Template error: {0}".format(error.message)
        exit(message)

    return template.render(context)
