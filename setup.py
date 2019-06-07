#! /usr/bin/env python

import os
from setuptools import setup
import sys


REQDIR = "requirements"


def read_reqs(reqs_name):
    deps = []
    with open(os.path.join(REQDIR, "requirements-{}.txt".format(reqs_name)), 'r') as f:
        for l in f:
            if not l.strip():
                continue
            #deps.append(l.split("=")[0].rstrip("<>"))
            deps.append(l)
    return deps


# Additional keyword arguments for setup().
extra = {}

# Ordinary dependencies
DEPENDENCIES = read_reqs("all")

# numexpr for pandas
try:
    import numexpr
except ImportError:
    # No numexpr is OK for pandas.
    pass
else:
    # pandas 0.20.2 needs updated numexpr; the claim is 2.4.6, but that failed.
    DEPENDENCIES.append("numexpr>=2.6.2")

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
scripts = None

with open("peppy/_version.py", 'r') as versionfile:
    version = versionfile.readline().split()[-1].strip("\"'\n")

# Handle the pypi README formatting.
try:
    import pypandoc
    long_description = pypandoc.convert_file('README.md', 'rst')
    print("Pandoc conversion succeeded")
except(IOError, ImportError, OSError):
    print("Warning: pandoc conversion failed!")
    long_description = open('README.md').read()


setup(
    name="peppy",
    packages=["peppy"],
    version=version,
    description="A python-based project metadata manager for portable encapsulated projects",
    long_description=long_description,
    long_description_content_type='text/markdown', 
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Scientific/Engineering :: Bio-Informatics"
    ],
    keywords="project, metadata, bioinformatics, sequencing, ngs, workflow",
    url='https://github.com/pepkit/peppy/',
    author=u"Nathan Sheffield, Vince Reuter, Andre Rendeiro",
    license="BSD2",
    scripts=scripts,
    include_package_data=True,
    test_suite="tests",
    tests_require=read_reqs("dev"),
    setup_requires=(["pytest-runner"] if {"test", "pytest", "ptr"} & set(sys.argv) else []),
    **extra
)
