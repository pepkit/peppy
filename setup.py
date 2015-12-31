#! /usr/bin/env python

import sys
import os
import shutil
import pipelines

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

# looper configs from /config
looper_configs = get_static("config")
# pipeline configs from /pipelines/.*\.yaml
pipeline_configs = get_static("pipelines", condition="'yaml' in x")

# scripts to be added to the $PATH
scripts = get_static("pipelines/tools", condition="'.' in x")
scripts += get_static("scripts", condition="'.' in x")


# temporarily copy looper to the pipelines package
# this is just for installation purposes
shutil.copy("looper.py", "pipelines/looper.py")

# setup
setup(
	name="pipelines",
	packages=["pipelines"],
	version=pipelines.__version__,
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
	author=u"Nathan Sheffield, Johanna Klughammer, Andre Rendeiro, Charles Dietz",
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
	data_files=[
		("configs", looper_configs + pipeline_configs)
	],
	include_package_data=True,
	**extra
)

# remove the copied looper
os.remove("pipelines/looper.py")
