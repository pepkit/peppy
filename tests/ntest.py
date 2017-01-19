
from looper.models import copy, Paths, AttributeDict
from looper.models import Project, SampleSheet, Sample
from looper.models import PipelineInterface, ProtocolMapper, CommandChecker

import os
p = Project(os.path.expandvars("$CODEBASE/looper/tests/test_config.yaml"))
p.add_sample_sheet()


