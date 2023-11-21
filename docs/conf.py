# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import time
from os import environ
from os.path import abspath, join
from pathlib import Path
from pyTooling.Packaging import extractVersionInformation

sys.path.insert(0, abspath('.'))
sys.path.insert(0, abspath('..'))
sys.path.insert(0, abspath('../src/simplhdl'))

packageInformationFile = Path("../src/simplhdl/__init__.py")
info = extractVersionInformation(packageInformationFile)

project = 'SimplHDL'
author = info.Author
copyright = f"2016-{time.strftime('%Y')}, {author}"

version = info.Version
release = info.Version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

# templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']
html_logo = join(abspath('.'), html_static_path[0], 'simplhdl_light_1.png')

html_theme_options = {
    "source_repository": "https://github.com/SimplHDL/simplhdl",
    "source_branch": environ.get("GITHUB_REF_NAME", "main"),
    "source_directory": "",
    "sidebar_hide_name": True,
    "footer_icons": [
        {
            "name": "Gitter hdl/community",
            "url": "https://gitter.im/hdl/community",
            "html": "",
            "class": "fa-solid fa-brands fa-gitter",
        },
        {
            "name": "GitHub https://github.com/SimplHDL/simplhdl",
            "url": "https://github.com/SimplHDL/simplhdl",
            "html": "",
            "class": "fa-solid fa-brands fa-github",
        },
    ],
}
