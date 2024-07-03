# type: ignore
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

sys.path.insert(0, os.path.abspath("../"))

project = "Picodi"
copyright = "2024, yakimka"
author = "yakimka"

with open("../pyproject.toml") as f:
    for line in f:
        if line.startswith("version"):
            version = line.split("=")[1].strip().strip('"')
            break
    else:
        raise ValueError("Version not found in pyproject.toml")

release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.coverage",
    "sphinx.ext.intersphinx",
    "sphinx.ext.doctest",
]
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
autodoc_member_order = "bysource"
autodoc_inherit_docstrings = False

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_logo = "_static/picodi_logo.png"


signatures_for_replace = {
    "~picodi._scopes.AutoScope": "AutoScope",
    "~picodi._scopes.ContextVarScope": "ContextVarScope",
    "~picodi._scopes.ManualScope": "ManualScope",
    "~picodi._scopes.NullScope": "NullScope",
    "~picodi._scopes.ScopeType": "ScopeType",
    "~picodi._scopes.Scope": "Scope",
    "~picodi._scopes.SingletonScope": "SingletonScope",
    "<class 'picodi._scopes.ManualScope'>": "ManualScope",
    "<class 'picodi._scopes.NullScope'>": "NullScope",
    "<class 'picodi._scopes.SingletonScope'>": "SingletonScope",
    "<class 'picodi._scopes.ContextVarScope'>": "ContextVarScope",
}


def process_signature(app, what, name, obj, options, signature, return_annotation):
    if signature:
        for old, new in signatures_for_replace.items():
            signature = signature.replace(old, new)
    if return_annotation:
        for old, new in signatures_for_replace.items():
            return_annotation = return_annotation.replace(old, new)
    return signature, return_annotation


def setup(app):
    app.connect("autodoc-process-signature", process_signature)
