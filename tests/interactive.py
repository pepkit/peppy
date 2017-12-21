# This is just a little helper script to set up an interactive session
# to help writing test cases.
# You must be in the pep tests dir:
# cd ${CODE}/peppy/tests
# ipython

import conftest

print("Establishing Project for testing and exploration")
proj, pi = conftest.interactive()
