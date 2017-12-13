#! /usr/bin/env python

import os
from setuptools import setup
import sys


# Additional keyword arguments for setup().
extra = {}

# Ordinary dependencies
DEPENDENCIES = []
with open("requirements/requirements-all.txt", "r") as reqs_file:
    for line in reqs_file:
        if not line.strip():
            continue
        #DEPENDENCIES.append(line.split("=")[0].rstrip("<>"))
        DEPENDENCIES.append(line)

# numexpr for pandas
try:
    import numexpr
except ImportError:
    # No numexpr is OK for pandas.
    pass
else:
    # pandas 0.20.2 needs updated numexpr; the claim is 2.4.6, but that failed.
    DEPENDENCIES.append("numexpr==2.6.2")

# 2to3
if sys.version_info >= (3, ):
    extra["use_2to3"] = True
extra["install_requires"] = DEPENDENCIES


# Additional files to include with package
def get_static(name, condition=None):
    static = [os.path.join(name, f) for f in os.listdir(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), name))]
    if condition is None:
        return static
    else:
        return [i for i in filter(lambda x: eval(condition), static)]

# scripts to be added to the $PATH
# scripts = get_static("scripts", condition="'.' in x")
# scripts removed (TO remove this)
scripts = None

with open("pep/_version.py", 'r') as versionfile:
    version = versionfile.readline().split()[-1].strip("\"'\n")

setup(
    name="pep",
    packages=["pep"],
    version=version,
    description="",
    long_description=open('README.md').read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics"
    ],
    keywords="bioinformatics, sequencing, ngs, workflow",
    url="https://github.com/pepkit/pep",
    author=u"Nathan Sheffield, Johanna Klughammer, Andre Rendeiro, Charles Dietz",
    license="GPL2",
    scripts=scripts,
    package_data={"looper": ["submit_templates/*"]},
    include_package_data=True,
    test_suite="tests",
    tests_require=(["mock", "pytest"]),
    setup_requires=(["pytest-runner"] if {"test", "pytest", "ptr"} & set(sys.argv) else []),
    **extra
)
