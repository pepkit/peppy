# This is just a little helper script to set up an interactive session
# to help writing test cases.
# You must be in the looper tests dir:
# cd $CODEBASE/looper/tests
# ipython

import looper
import conftest
proj, pi = conftest.interactive()
