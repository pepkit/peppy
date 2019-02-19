#!/bin/bash
peppy_home="${CODE}/peppy"
docs_home="${peppy_home}/docs/docs"
pydocmd simple peppy+ peppy.project++ peppy.sample++ peppy.utils++ > ${docs_home}/autodoc_build/peppy.md
