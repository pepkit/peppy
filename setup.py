from setuptools import setup
import os

setup(
    name="pipelines",
    version="0.1",
    description="Pipelines in Python.",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics"],
    keywords="bioinformatics, sequencing, ngs, ChIP-seq, DNase-seq, ATAC-Seq",
    url="https://github.com/afrendeiro/pipelines",
    author="Andre Rendeiro",
    author_email="arendeiro@cemm.oeaw.ac.at",
    license="GPL2",
    packages=["pipelines"],
    install_requires=["pyyaml", "numpy", "pandas"],
    scripts=[
        "pipelines/ngsProject",
        "pipelines/chipseq-pipeline",
        "pipelines/atacseq-pipeline",
        "pipelines/quantseq-pipeline",
        "lib/shift_reads.py",
        "lib/fix_bedfile_genome_boundaries.py",
        "lib/get5primePosition.py",
        "lib/spp_peak_calling.R"
    ],
    data_files=[(os.path.expanduser("~"), ['.pipelines_config.yaml'])],
    include_package_data=True,
    zip_safe=False
)
