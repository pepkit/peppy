""" Pipeline job submission orchestration """

import copy
import glob
import logging
import os
import re
import subprocess
import time

from .models import Sample, VALID_READ_TYPES
from .utils import \
    create_looper_args_text, grab_project_data, sample_folder


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


_LOGGER = logging.getLogger(__name__)



class SubmissionConductor(object):
    """
    Orchestration of submission of pipeline jobs.

    This class implements the notion of a 'pool' of commands to submit as a
    single cluster job. Eager to submit a job, each instance's collection of
    commands expands until such time as its parameterization (determined at
    construction time) and the state of its command pool indicate that the
    'pool' has been filled and it's therefore time to submit the job. Total
    input file size and the number of individual commands are the criteria
    that may be used to determine whether it's time to submit a job.

    """


    def __init__(self, pipeline_key, pipeline_interface, cmd_base, prj,
                 dry_run=False, delay=0, sample_subtype=None, extra_args=None,
                 ignore_flags=False, partition=None,
                 max_cmds=None, max_size=None, automatic=True):
        """
        Create a job submission manager.

        The most critical inputs are the pipeline interface and the pipeline
        key, which together determine which provide critical pipeline
        information like resource allocation packages and which pipeline will
        be overseen by this instance, respectively.

        :param str pipeline_key: 'Hook' into the pipeline interface, and the
            datum that determines which pipeline this manager will oversee.
        :param PipelineInterface pipeline_interface: Collection of important
            data for one or more pipelines, like resource allocation packages
            and option/argument specifications
        :param str cmd_base: Base of each command for each job, e.g. the
            script path and command-line options/flags that are constant
            across samples.
        :param prj: Project with which each sample being considered is
            associated (what generated each sample)
        :param bool dry_run: Whether this is a dry run and thus everything
            but the actual job submission should be done.
        :param float delay: Time (in seconds) to wait before submitting a job
            once it's ready
        :param type sample_subtype: Extension of base Sample, for particular
            pipeline for which submissions will be managed by this instance
        :param list extra_args: Additional arguments to add (positionally) to
            each command within each job generated
        :param bool ignore_flags: Whether to ignore flag files present in
            the sample folder for each sample considered for submission
        :param str partition: Name of the cluster partition to which job(s)
            will be submitted
        :param int | NoneType max_cmds: Upper bound on number of commands to
            include in a single job script.
        :param int | float | NoneType max_size: Upper bound on total file
            size of inputs used by the commands lumped into single job script.
        :param bool automatic: Whether the submission should be automatic once
            the pool reaches capacity.
        """

        super(SubmissionConductor, self).__init__()

        self.pl_key = pipeline_key
        self.pl_iface = pipeline_interface
        self.pl_name = pipeline_interface.get_pipeline_name(pipeline_key)
        self.cmd_base = cmd_base.rstrip(" ")

        self.dry_run = dry_run
        self.delay = float(delay)

        self.sample_subtype = sample_subtype or Sample
        self.partition = partition
        if extra_args:
            self.extra_args_text = "{}".format(" ".join(extra_args))
        else:
            self.extra_args_text = ""
        self.uses_looper_args = \
                pipeline_interface.uses_looper_args(pipeline_key)
        self.ignore_flags = ignore_flags
        self.prj = prj
        self.automatic = automatic

        with open(self.prj.compute.submission_template, 'r') as template_file:
            self._template = template_file.read()

        if max_cmds is None and max_size is None:
            self.max_cmds = 1
        elif (max_cmds is not None and max_cmds < 1) or \
                (max_size is not None and max_size < 0):
            raise ValueError(
                    "If specified, max per-job command count must positive, "
                    "and max per-job total file size must be nonnegative")
        else:
            self.max_cmds = max_cmds
        self.max_size = max_size or float("inf")

        self._pool = []
        self._curr_size = 0
        self._num_job_submissions = 0
        self._num_cmds_submitted = 0


    @property
    def is_full(self):
        """
        Determine whether it's time to submit a job for the pool of commands.

        Instances of this class maintain a sort of 'pool' of commands that
        expands as each new command is added, until a time that it's deemed
        'full' and th

        :return:
        """
        return self.max_cmds == len(self._pool) or \
               self._curr_size >= self.max_size


    @property
    def num_cmd_submissions(self):
        """
        Return the number of commands that this conductor has submitted.
        
        :return int: Number of commands submitted so far.
        """
        return self._num_cmds_submitted


    @property
    def num_job_submissions(self):
        """
        Return the number of jobs that this conductor has submitted.
        
        :return int: Number of jobs submitted so far.
        """
        return self._num_job_submissions


    def add(self, sample, sample_subtype=Sample):
        """


        :param Sample sample:
        :param type sample_subtype:
        :return bool: Indication of whether the given sample was added to
            the current 'pool.'
        :raise TypeError: If sample subtype is provided but does not extend
            the base Sample class, raise a TypeError.
        """
        
        if not issubclass(sample_subtype, Sample):
            raise TypeError("If provided, sample_subtype must extend {}".
                            format(Sample.__name__))
        
        sfolder = sample_folder(prj=self.prj, sample=sample)
        # TODO: pep utils --> flag_name for *.flag
        flag_files = glob.glob(os.path.join(sfolder, self.pl_name + "*.flag"))
        # TODO: need to communicate failures to caller, but also disambiguate
        # TODO (cont.): between three cases: flag files, failure(s), and submission.
        # TODO (cont.): this is similar to the 'Missing input files' case.
        skip_reasons = []
        
        if not self.ignore_flags and len(flag_files) > 0:
            flag_files_text = ", ".join(['{}'.format(fp) for fp in flag_files])
            _LOGGER.info("> Skipping sample '%s' for pipeline '%s', "
                         "flag(s) found: %s", sample.name, self.pl_name,
                         flag_files_text)
            _LOGGER.debug("NO SUBMISSION")
        
        else:
            sample = sample_subtype(sample)
            _LOGGER.debug("Created %s instance: %s'",
                          sample_subtype.__name__, sample.name)
            sample.prj = grab_project_data(self.prj)
            
            skip_reasons = []
            
            try:
                # Add pipeline-specific attributes.
                sample.set_pipeline_attributes(
                        self.pl_iface, pipeline_name=self.pl_key)
            except AttributeError:
                # TODO: inform about WHICH missing attribute(s)?
                fail_message = "Pipeline required attribute(s) missing"
                _LOGGER.warn("> Not submitted: %s", fail_message)
                skip_reasons.append(fail_message)
                
            # Check for any missing requirements before submitting.
            _LOGGER.debug("Determining missing requirements")
            error_type, missing_reqs_msg = \
                sample.determine_missing_requirements()
            if missing_reqs_msg:
                if self.prj.permissive:
                    _LOGGER.warn(missing_reqs_msg)
                else:
                    raise error_type(missing_reqs_msg)
                _LOGGER.warn("> Not submitted: %s", missing_reqs_msg)
                skip_reasons.append(missing_reqs_msg)

            # Check if single_or_paired value is recognized.
            if hasattr(sample, "read_type"):
                # Drop "-end", "_end", or "end" from end of the column value.
                rtype = re.sub('[_\\-]?end$', '',
                               str(sample.read_type))
                sample.read_type = rtype.lower()
                if sample.read_type not in VALID_READ_TYPES:
                    _LOGGER.debug(
                        "Invalid read type: '{}'".format(sample.read_type))
                    skip_reasons.append("read_type must be in {}".
                                        format(VALID_READ_TYPES))

            # Append arguments for this pipeline
            # Sample-level arguments are handled by the pipeline interface.
            try:
                argstring = self.pl_iface.get_arg_string(
                    pipeline_name=self.pl_key, sample=sample,
                    submission_folder_path=self.prj.metadata.submission_subdir)
            except AttributeError:
                # TODO: inform about which missing attribute(s).
                fail_message = "Required attribute(s) missing " \
                               "for pipeline arguments string"
                _LOGGER.warn("> Not submitted: %s", fail_message)
                skip_reasons.append(fail_message)
                
            if not skip_reasons:
                self._pool.append((sample, argstring))
                self._curr_size += float(sample.input_file_size)

        if self.automatic and self.is_full:
            self.submit()

        return skip_reasons


    def submit(self, force=False):
        """
        Submit command(s) as a job.
        
        This call will submit the commands corresponding to the current pool 
        of samples if and only if the argument to 'force' evaluates to a 
        true value, or the pool of samples is full.
        
        :param force: 
        :return: 
        """

        if not self._pool:
            _LOGGER.info("No submission (no pooled samples): %s", self.pl_name)
            submitted = False

        elif force or self.is_full:
            _LOGGER.info("Determining submission settings for %d sample(s) "
                         "(%.2f Gb)", len(self._pool), self._curr_size)
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
            assert all(map(lambda cmd_part: isinstance(cmd_part, str),
                           [self.cmd_base, prj_argtext, looper_argtext])), \
                "Each command component mut be a string."

            # Ensure that each sample is individually represented on disk,
            # specific to subtype as applicable (should just be a single
            # subtype for each submission conductor, but some may just be
            # the base Sample while others are the single valid subtype.)
            for s, _ in self._pool:
                if type(s) is Sample:
                    exp_fname = "{}.yaml".format(s.name)
                    exp_fpath = os.path.join(
                            self.prj.metadata.submission_subdir, exp_fname)
                    if not os.path.isfile(exp_fpath):
                        _LOGGER.warn("Missing %s file will be created: '%s'",
                                     Sample.__name__, exp_fpath)
                else:
                    subtype_name = s.__class__.__name__
                    _LOGGER.debug("Writing %s representation to disk: '%s'",
                                  subtype_name, s.name)
                    s.to_yaml(subs_folder_path=self.prj.metadata.submission_subdir)

            script = self._write_script(settings, prj_argtext=prj_argtext,
                                        looper_argtext=looper_argtext)

            # Determine whether to actually do the submission.
            if self.dry_run:
                _LOGGER.info("> DRY RUN: I would have submitted this: '%s'",
                             script)
            else:
                submission_command = "{} {}".format(
                    self.prj.compute.submission_command, script)
                subprocess.call(submission_command, shell=True)
                # Delay next job's submission.
                time.sleep(self.delay)
            _LOGGER.debug("SUBMITTED")

            # Update the job and command submission tallies.
            submitted = True
            self._num_job_submissions += 1
            self._num_cmds_submitted += len(self._pool)

            self._reset_pool()

        else:
            _LOGGER.info("No submission (pool is not full and submission "
                         "was not forced): %s", self.pl_name)
            submitted = False

        return submitted


    def _jobname(self):
        """ Create the name for a job submission. """
        if 1 == self.max_cmds:
            assert 1 == len(self._pool), \
                "If there's a single-command limit on job submission, jobname " \
                "must be determined with exactly one sample in the pool."
            sample, _ = self._pool[0]
            name = sample.name
        else:
            # Note the order in which the increment of submission count and
            # the call to this function can influence naming.
            name = "lump{}".format(self.num_job_submissions)
        return "{}_{}".format(self.pl_key, name)



    def _reset_pool(self):
        """ Reset the state of the pool of samples """
        self._pool = []
        self._curr_size = 0


    def _write_script(self, template_values, prj_argtext, looper_argtext):
        extra_parts = list(filter(
                lambda cmd_part: bool(cmd_part),
                [prj_argtext, looper_argtext, self.extra_args_text]))
        extra_parts_text = " ".join(extra_parts)
        commands = []
        for _, argstring in self._pool:
            if argstring:
                base = "{} {}".format(self.cmd_base, argstring.rstrip())
            else:
                base = self.cmd_base
            if extra_parts_text:
                cmd = "{} {}".format(base, extra_parts_text)
            else:
                cmd = base
            commands.append(cmd)

        jobname = self._jobname()
        submission_base = os.path.join(
                self.prj.metadata.submission_subdir, jobname)
        logfile = submission_base + ".log"
        template_values["JOBNAME"] = jobname
        template_values["CODE"] = "\n".join(commands)
        template_values["LOGFILE"] = logfile

        script_data = copy.copy(self._template)
        for k, v in template_values.items():
            placeholder = "{" + str(k).upper() + "}"
            script_data.replace(placeholder, str(v))

        submission_script = submission_base + ".sub"
        script_dirpath = os.path.dirname(submission_script)
        if not os.path.isdir(script_dirpath):
            os.makedirs(script_dirpath)

        sample_names_text = ", ".join(s.name for s, _ in self._pool)
        _LOGGER.info("> Submission script for %d sample(s): '%s' (%s)",
                     len(self._pool), sample_names_text, submission_script)
        with open(submission_script, 'w') as sub_file:
            sub_file.write(script_data)

        return submission_script