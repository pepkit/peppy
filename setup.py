#! /usr/bin/env python

import sys
import os
import shutil

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

# scripts to be added to the $PATH
scripts = os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts"))
# scripts += os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), "pipelines/tools"))
scripts = ["scripts/%s" % f for f in scripts if "." in f]

print scripts
# templates to be copied with the code upon installation
templates = ["templates/%s" % f for f in os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates"))]

# temporarily copy looper to the pipelines package
# this is just for installation purposes
shutil.copy("looper.py", "pipelines/looper.py")

# setup
setup(
	name="pipelines",
	packages=["pipelines"],
	version="0.2",
	description="NGS pipelines in Python.",
	long_description=open('README.md').read(),
	classifiers=[
		"Development Status :: 3 - Alpha",
		"License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
		"Programming Language :: Python :: 2.7",
		"Topic :: Scientific/Engineering :: Bio-Informatics"
	],
	keywords="bioinformatics, sequencing, ngs, ATAC-Seq, ChIP-seq, RNA-seq, RRBS, WGBS",
	url="https://github.com/epigen/pipelines",
	author=u"Nathan Sheffield, Johanna Klughammer, Andre Rendeiro",
	license="GPL2",
	install_requires=["pyyaml", "pandas"],
	entry_points={
		"console_scripts": [
			'looper = pipelines.looper:main',
			'atacseq_pipeline = pipelines.atacseq:main',
			'chipseq_pipeline = pipelines.chipseq:main',
			'cpgseq_pipeline = pipelines.cpgseq:main',
			'interactions_pipeline = pipelines.interactions:main',
			'quantseq_pipeline = pipelines.quantseq:main',
			'rrbs_pipeline = pipelines.rrbs:main',
			'rnaTopHat_pipeline = pipelines.rnaTopHat:main',
			'rnaBitSeq_pipeline = pipelines.rnaBitSeq:main',
			'wgbs_pipeline = pipelines.wgbs:main'
		],
	},
	scripts=scripts,
	data_files=[("templates", templates)],
	# include_package_data=True
)

# remove the copied looper
os.remove("pipelines/looper.py")
