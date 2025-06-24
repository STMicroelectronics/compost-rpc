import sys
import os
sys.path.insert(0, os.path.abspath('../compost_rpc'))
sys.path.insert(0, os.path.abspath('../..'))
import compost_rpc  # noqa: E402

project = 'Compost'
copyright = 'STMicroelectronics'
author = 'Radovan Blažek'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'myst_parser',
    'breathe',
]

myst_enable_extensions = [
    'tasklist',
    'deflist',
    'substitution',
]

myst_substitutions = {
  "version": compost_rpc.__version__.replace("-", ".")
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'node_modules']

breathe_projects = {
    "compost_c": "_doxygen/xml/",
}

breathe_default_project = "compost_c"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_title = f"Compost {compost_rpc.__version__}"
language = "en"
html_static_path = ['_static']

html_theme_options = {
    "light_logo": "image/logo/ST_logo_2020_blue_no_tagline.svg",
    "dark_logo": "image/logo/ST_logo_2020_white_no_tagline.svg",
    "light_css_variables": {
        "color-problematic": "#e6007e",
        "color-sidebar-brand-text": "",
    },
    "dark_css_variables": {
        "color-problematic": "#e6007e",
        "color-sidebar-brand-text": "",
    },
}