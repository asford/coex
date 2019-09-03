#!/usr/bin/env python

import os

from setuptools import find_packages, setup

# Package meta-data.
REQUIRES_PYTHON = "~=3.6"
requires = ["conda>=4.6", "attrs>=18.1", "click=7"]
requires = []
extras = {}


here = os.path.abspath(os.path.dirname(__file__))


def README():
    return open(os.path.join(here, "README.md")).read()


setup(
    name="coex",
    # description
    description="Coex is a utility that creates self-contained conda executables.",
    long_description=README(),
    long_description_content_type="text/markdown",
    license="MIT",
    # version
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    # author
    author="Alex Ford",
    author_email="a.sewall.ford@gmail.com",
    url="https://github.com/asford/coex",
    # package spec
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    # requirements
    python_requires=REQUIRES_PYTHON,
    install_requires=requires,
    extras_require=extras,
)
