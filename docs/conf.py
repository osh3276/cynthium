# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Path setup --------------------------------------------------------------

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "cynthium"
copyright = "2026, Oliver Huang"
author = "Oliver Huang"
release = "0.0a4"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
	"sphinx.ext.autodoc",
	"sphinx.ext.autosummary",
	"sphinx.ext.napoleon",
	"sphinx.ext.viewcode",
	"sphinx.ext.mathjax",
	"sphinx.ext.intersphinx",
]

intersphinx_mapping = {
	"python": ("https://docs.python.org/3", None),
	"numpy": ("https://numpy.org/doc/stable", None),
	"PySide6": ("https://doc.qt.io/qtforpython-6", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "bizstyle"
html_static_path = ["_static"]
html_theme_options = {
	# "description": "Lunar rover traversal planning & terrain analysis",
	# "github_user": "osh3276",
	# "github_repo": "cynthium",
	# "github_button": True,
	# "fixed_sidebar": True,
	# "sidebar_collapse": True,
	# "page_width": "1080px",
	# "sidebar_width": "280px",
}
