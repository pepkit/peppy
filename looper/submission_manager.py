""" Pipeline job submission orchestration """

from functools import partial
import logging
from looper.models import Sample
from looper.utils import create_looper_args_text

__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


_LOGGER = logging.getLogger(__name__)



class SubmissionConductor(object):
    """ Management of submission of pipeline jobs. """


    def __init__(self, pipeline_key, pipeline_interface, cmd_base, prj,
                 extra_args=None, sample_subtype=None,
                 partition=None, max_cmds=None, max_size=None):

        super(SubmissionConductor, self).__init__()

        self.pl_key = pipeline_key
        self.pl_iface = pipeline_interface
        self.pl_name = pipeline_interface.get_pipeline_name(pipeline_key)
        self.cmd_base = cmd_base
        self.sample_subtype = sample_subtype or Sample
        self.partition = partition
        self.extra_args = extra_args or []
        self.uses_looper_args = \
                pipeline_interface.uses_looper_args(pipeline_key)
        self.prj = prj

        if max_cmds < 1 or max_size < 0:
            raise ValueError(
                    "If specified, max per-job command count must positive, "
                    "and max per-job total file size must be nonnegative")
        if max_cmds is None and max_size is None:
            self.max_cmds = 1
        else:
            self.max_cmds = max_cmds
        self.max_size = max_size or float("inf")

        self._submissions = []
        self._curr_size = 0


    @property
    def is_full(self):
        return self.max_cmds == len(self._submissions) or \
               self._curr_size >= self.max_size


    def add(self, sample_data):

        if self.is_full:
            self.submit()



    def submit(self):
        _LOGGER.info("Determining submission settings for %d sample(s) "
                     "(%.2f Gb)", len(self._submissions), self._curr_size)
        settings = self.pl_iface.choose_resource_package(
                self.pl_key, self._curr_size)
        if self.partition:
            settings["partition"] = self.partition
        if self.uses_looper_args:
            looper_argtext = \
                create_looper_args_text(self.pl_key, settings, self.prj)
        else:
            looper_argtext = ""
        prj_argtext = self.prj.get_arg_string(self.pl_key)
        assert all(map(lambda cmd_part: cmd_part is not None,
                       [self.cmd_base, prj_argtext, looper_argtext])), \
                "No command component may be null"
        # TODO: get sample argstrings
        commands = []
        self._reset()


    def _reset(self):
        self._submissions = []
        self._curr_size = 0
