# -*- coding: utf-8 -*-
"""
    conf
    ~~~~

    Sphinx documentation configuration

    :copyright: 2014 by Jonathan Zempel.
    :license: BSD, see LICENSE for more details.
"""

from datetime import datetime
import continuity

_description = "continuous dev inspired by GitHub Flow"
master_doc = "index"

copyright = "{0}, {1}".format(datetime.now().year, continuity.__author__)
exclude_patterns = ["_build"]
html_static_path = ["_static"]
html_theme = "default"
htmlhelp_basename = "{0}doc".format(continuity.__name__)
latex_documents = [(
    master_doc,
    "{0}.tex".format(continuity.__name__),
    _description,
    continuity.__author__,
    "manual"
)]
latex_elements = {}
man_pages = [(
    master_doc,
    continuity.__name__,
    _description,
    [continuity.__author__],
    1
)]
project = continuity.__name__
pygments_style = "sphinx"
release = continuity.__version__
source_suffix = ".rst"
templates_path = ["_templates"]
texinfo_documents = [(
    master_doc,
    continuity.__name__,
    '',
    continuity.__author__,
    continuity.__name__,
    _description,
    "Miscellaneous"
)]
version = continuity.__version__
