# This is just a little helper script to set up an interactive session
# to help writing test cases.
# You must be in the looper tests dir:
# cd $CODEBASE/looper/tests
# ipython

from __future__ import absolute_import
import looper
from . import conftest

print("Running interactive.py tests")
proj, pi = conftest.interactive()
