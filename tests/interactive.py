# This is just a little helper script to set up an interactive session
# to help writing test cases.
# You must be in the pep tests dir:
# cd ${CODE}/peppy/tests
# ipython

import conftest

print("Establishing Project for testing and exploration")
proj = conftest.interactive()


import peppy
import os
reload(peppy)
peppy._LOGGER.setLevel(50)
p = peppy.Project(os.path.expandvars("$CODEBASE/example_peps/example2/project_config.yaml"))

p.get_sample("frog_1").subsamples

p.sample_table
p.subsample_table


p.get_sample("frog_2").subsamples
p.get_sample("frog_2").subsamples[0].subsample_name

p.get_subsample(sample_name="frog_1", subsample_name="2")


subsamples = []
type(subsamples)
for n, row in p.subsample_table.iterrows():
	print n
	print row
	subsamples.append(peppy.SubSample(row))

subsamples

peppy.Sample(row)

peppy.SubSample(row)
