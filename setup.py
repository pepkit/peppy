#! /usr/bin/env python

import sys
import os

# take care of extra required modules depending on Python version
extra = {}

try:
    from setuptools import setup
    if sys.version_info < (2, 7):
        extra['install_requires'] = ['argparse']
    if sys.version_info >= (3,):
        extra['use_2to3'] = True
except ImportError:
    from distutils.core import setup
    if sys.version_info < (2, 7):
        extra['dependencies'] = ['argparse']


# Additional files to include with package
def get_static(name, condition=None):
    static = [os.path.join(name, f) for f in os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), name))]
    if condition is None:
        return static
    else:
        return filter(lambda x: eval(condition), static)

# scripts to be added to the $PATH
scripts = get_static("scripts", condition="'.' in x")

with open("VERSION", 'r') as versionfile:
    version = versionfile.read().strip()

# setup
setup(
    name="looper",
    packages=["looper"],
    version=version,
    description="A pipeline submission engine that parses sample inputs and submits pipelines for each sample.",
    long_description=open('README.md').read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics"
    ],
    keywords="bioinformatics, sequencing, ngs",
    url="https://github.com/epigen/looper",
    author=u"Nathan Sheffield, Johanna Klughammer, Andre Rendeiro, Charles Dietz",
    license="GPL2",
    install_requires=["pyyaml", "pandas"],
    entry_points={
        "console_scripts": [
            'looper = looper.looper:main'
        ],
    },
    scripts=scripts,
    package_data={'looper': ['submit_templates/*']},
    include_package_data=True,
    **extra
)
