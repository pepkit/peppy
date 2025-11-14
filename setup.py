import os
import sys




# Additional keyword arguments for setup().





with open("README.md") as f:
    long_description = f.read()

setup(
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    license="BSD2",
    entry_points={
        ],
    },
    include_package_data=True,
    setup_requires=(
        ["pytest-runner"] if {"test", "pytest", "ptr"} & set(sys.argv) else []
    ),
    **extra,
)
