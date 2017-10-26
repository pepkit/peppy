#!/usr/bin/env python
"""
Looper: a pipeline submission engine. https://github.com/epigen/looper
"""

import abc
import argparse
from collections import defaultdict
import copy
import glob
import logging
import os
import re
import subprocess
import sys
import time
import pandas as _pd
from . import setup_looper_logger, FLAGS, LOGGING_LEVEL, __version__
from .loodels import Project
from .models import \
    grab_project_data, ProjectContext, Sample, \
    COMPUTE_SETTINGS_VARNAME, SAMPLE_EXECUTION_TOGGLE, \
    SAMPLE_NAME_COLNAME, VALID_READ_TYPES
from .utils import \
    alpha_cased, fetch_flag_files, sample_folder, VersionInHelpParser


from colorama import init
init()
from colorama import Fore, Style

# Descending by severity for correspondence with logic inversion.
# That is, greater verbosity setting corresponds to lower logging level.
_LEVEL_BY_VERBOSITY = [logging.ERROR, logging.CRITICAL, logging.WARN,
                       logging.INFO, logging.DEBUG]

_LOGGER = logging.getLogger()



def parse_arguments():
    """
    Argument Parsing.

    :return argparse.Namespace, list[str]: namespace parsed according to
        arguments defined here, and additional options arguments undefined
        here and to be handled downstream
    """

    # Main looper program help text messages
    banner = "%(prog)s - Loop through samples and submit pipelines."
    additional_description = "For subcommand-specific options, type: " \
            "'%(prog)s <subcommand> -h'"
    additional_description += "\nhttps://github.com/epigen/looper"

    parser = VersionInHelpParser(
            description=banner,
            epilog=additional_description,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
            "-V", "--version",
            action="version",
            version="%(prog)s {v}".format(v=__version__))

    # Logging control
    parser.add_argument(
            "--logfile", dest="logfile",
            help="Optional output file for looper logs")
    parser.add_argument(
            "--verbosity", dest="verbosity",
            type=int, choices=range(len(_LEVEL_BY_VERBOSITY)),
            help="Choose level of verbosity")
    parser.add_argument(
            "--logging-level", dest="logging_level",
            help=argparse.SUPPRESS)
    parser.add_argument(
            "--dbg", dest="dbg", action="store_true",
            help="Turn on debug mode")

    # Individual subcommands
    msg_by_cmd = {
            "run": "Main Looper function: Submit jobs for samples.",
            "summarize": "Summarize statistics of project samples.",
            "destroy": "Remove all files of the project.", 
            "check": "Checks flag status of current runs.", 
            "clean": "Runs clean scripts to remove intermediate "
                     "files of already processed jobs."}
    subparsers = parser.add_subparsers(dest="command")
    def add_subparser(cmd):
        message = msg_by_cmd[cmd]
        return subparsers.add_parser(cmd, description=message, help=message)

    # Run command
    run_subparser = add_subparser("run")
    run_subparser.add_argument(
            "-t", "--time-delay", dest="time_delay",
            type=int, default=0,
            help="Time delay in seconds between job submissions.")
    run_subparser.add_argument(
            "--ignore-flags", dest="ignore_flags",
            action="store_true",
            help="Ignore run status flags? Default: False. "
                 "By default, pipelines will not be submitted if a pypiper "
                 "flag file exists marking the run (e.g. as "
                 "'running' or 'failed'). Set this option to ignore flags "
                 "and submit the runs anyway.")
    run_subparser.add_argument(
            "--compute", dest="compute",
            help="YAML file with looper environment compute settings.")
    run_subparser.add_argument(
            "--env", dest="env",
            default=os.getenv("{}".format(COMPUTE_SETTINGS_VARNAME), ""),
            help="Employ looper environment compute settings.")
    run_subparser.add_argument(
            "--limit", dest="limit", default=None,
            type=int,
            help="Limit to n samples.")
    run_subparser.add_argument(
            "--lump-size", type=int, default=1,
            help="Number of individual scripts grouped into single submission")

    # Other commands
    summarize_subparser = add_subparser("summarize")
    destroy_subparser = add_subparser("destroy")
    check_subparser = add_subparser("check")
    clean_subparser = add_subparser("clean")

    check_subparser.add_argument(
            "-A", "--all-folders", action="store_true",
            help="Check status for all project's output folders, not just "
                 "those for samples specified in the config file used")
    check_subparser.add_argument(
            "-F", "--flags", nargs='*', default=FLAGS,
            help="Check on only these flags/status values.")

    # Common arguments
    for subparser in [run_subparser, summarize_subparser,
                destroy_subparser, check_subparser, clean_subparser]:
        subparser.add_argument(
                "config_file",
                help="Project configuration file (YAML).")
        subparser.add_argument(
                "--file-checks", dest="file_checks",
                action="store_false",
                help="Perform input file checks. Default=True.")
        subparser.add_argument(
                "-d", "--dry-run", dest="dry_run",
                action="store_true",
                help="Don't actually submit the project/subproject.")
        protocols = subparser.add_mutually_exclusive_group()
        protocols.add_argument(
                "--exclude-protocols", nargs='*', dest="exclude_protocols",
                help="Operate only on samples that either lack a protocol or "
                     "for which protocol is not in this collection.")
        protocols.add_argument(
                "--include-protocols", nargs='*', dest="include_protocols",
                help="Operate only on samples associated with these protocols; "
                     "if not provided, all samples are used.")
        subparser.add_argument(
                "--sp", dest="subproject",
                help="Name of subproject to use, as designated in the "
                     "project's configuration file")

    # To enable the loop to pass args directly on to the pipelines...
    args, remaining_args = parser.parse_known_args()

    # Set the logging level.
    if args.dbg:
        # Debug mode takes precedence and will listen for all messages.
        level = args.logging_level or logging.DEBUG
    elif args.verbosity is not None:
        # Verbosity-framed specification trumps logging_level.
        level = _LEVEL_BY_VERBOSITY[args.verbosity]
    else:
        # Normally, we're not in debug mode, and there's not verbosity.
        level = LOGGING_LEVEL

    # Establish the project-root logger and attach one for this module.
    setup_looper_logger(level=level,
                        additional_locations=(args.logfile, ),
                        devmode=args.dbg)
    global _LOGGER
    _LOGGER = logging.getLogger(__name__)

    if len(remaining_args) > 0:
        _LOGGER.debug("Remaining arguments passed to pipelines: {}".
                      format(" ".join([str(x) for x in remaining_args])))

    return args, remaining_args



class Executor(object):
    """ Base class that ensures the program's Sample counter starts. """

    __metaclass__ = abc.ABCMeta

    def __init__(self, prj):
        """
        The Project defines the instance; establish an iteration counter.
        
        :param Project prj: Project with which to work/operate on
        """
        super(Executor, self).__init__()
        self.prj = prj
        self.counter = LooperCounter(len(prj.samples))

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        """ Do the work of the subcommand/program. """
        pass



class Cleaner(Executor):
    """ Remove all intermediate files (defined by pypiper clean scripts). """
    
    def __call__(self, args, preview_flag=True):
        """
        Execute the file cleaning process.
        
        :param argparse.Namespace args: command-line options and arguments
        :param bool preview_flag: whether to halt before actually removing files 
        """
        _LOGGER.info("Files to clean:")

        for sample in self.prj.samples:
            _LOGGER.info(self.counter.show(sample.sample_name, sample.protocol))
            sample_output_folder = sample_folder(self.prj, sample)
            cleanup_files = glob.glob(os.path.join(sample_output_folder,
                                                   "*_cleanup.sh"))
            if preview_flag:
                # Preview: Don't actually clean, just show what will be cleaned.
                _LOGGER.info("Files to clean: %s", ", ".join(cleanup_files))
            else:
                for f in cleanup_files:
                    _LOGGER.info(f)
                    subprocess.call(["sh", f])

        if not preview_flag:
            _LOGGER.info("Clean complete.")
            return 0

        if args.dry_run:
            _LOGGER.info("Dry run. No files cleaned.")
            return 0

        if not query_yes_no("Are you sure you want to permanently delete all "
                            "intermediate pipeline results for this project?"):
            _LOGGER.info("Clean action aborted by user.")
            return 1

        self.counter.reset()

        return self(args, preview_flag=False)



class Destroyer(Executor):
    """ Destroyer of files and folders associated with Project's Samples """
    
    def __call__(self, args, preview_flag=True):
        """
        Completely remove all output produced by any pipelines.
    
        :param argparse.Namespace args: command-line options and arguments
        :param bool preview_flag: whether to halt before actually removing files
        """
    
        _LOGGER.info("Results to destroy:")
    
        for sample in self.prj.samples:
            _LOGGER.info(
                self.counter.show(sample.sample_name, sample.protocol))
            sample_output_folder = sample_folder(self.prj, sample)
            if preview_flag:
                # Preview: Don't actually delete, just show files.
                _LOGGER.info(str(sample_output_folder))
            else:
                destroy_sample_results(sample_output_folder, args)
    
        if not preview_flag:
            _LOGGER.info("Destroy complete.")
            return 0
    
        if args.dry_run:
            _LOGGER.info("Dry run. No files destroyed.")
            return 0
    
        if not query_yes_no("Are you sure you want to permanently delete "
                            "all pipeline results for this project?"):
            _LOGGER.info("Destroy action aborted by user.")
            return 1

        self.counter.reset()

        # Finally, run the true destroy:
        return self(args, preview_flag=False)



def create_looper_args_text(prj, pl_key, submission_settings):
    """
    
    :param Project prj: Project data, used for metadata and pipeline
        configuration information
    :param str pl_key: Strict/exact pipeline key, the hook into the project's
        pipeline configuration data
    :param dict submission_settings: Mapping from settings
        key to value, used to determine resource request
    :return str: text representing the portion of a command generated by
        looper options and arguments
    """

    # Start with copied settings and empty arguments text
    submission_settings = copy.deepcopy(submission_settings)
    looper_argtext = ""

    if hasattr(prj, "pipeline_config"):
        # Index with 'pl_key' instead of 'pipeline'
        # because we don't care about parameters here.
        if hasattr(prj.pipeline_config, pl_key):
            # First priority: pipeline config in project config
            pl_config_file = getattr(prj.pipeline_config,
                                     pl_key)
            # Make sure it's a file (it could be provided as null.)
            if pl_config_file:
                if not os.path.isfile(pl_config_file):
                    _LOGGER.error(
                        "Pipeline config file specified "
                        "but not found: %s", pl_config_file)
                    raise IOError(pl_config_file)
                _LOGGER.info("Found config file: %s",
                             pl_config_file)
                # Append arg for config file if found
                looper_argtext += " -C " + pl_config_file

    looper_argtext += " -O " + prj.metadata.results_subdir
    if int(submission_settings.setdefault("cores", 1)) > 1:
        looper_argtext += " -P " + submission_settings["cores"]
    try:
        if float(submission_settings["mem"]) > 1:
            looper_argtext += " -M " + submission_settings["mem"]
    except KeyError:
        _LOGGER.warn("Submission settings lack memory specification")

    return looper_argtext
    


def create_pipeline_submissions(
        pl_key, pl_job, pl_iface, sample_subtype, sample_data_bundles,
        prj, update_partition, extra_args, lump_size=1, ignore_flags=False):
    """
    Submit samples for a particular pipeline.

    :param pl_key: strict pipeline key, used for accessing interface data
    :param str pl_job: script + flags (command-like) for the job(s) to submit
    :param PipelineInterface pl_iface: pipeline interface with which each 
        submission generated here is associated; determines resource request
    :param type sample_subtype: the type of each Sample to create for 
        submission, perhaps determining how it's represented on disk and 
        thus how it's presented to each pipeline for processing
    :param Iterable[Mapping] sample_data_bundles: collection of mappings,
        each containing data for a single sample
    :param Project prj: Project with which the samples are associated
    :param callable update_partition: function with which to update
        partition setting
    :param extra_args: additional arguments to add to command string
    :param bool ignore_flags: whether to disregard flag files that exist for
        a sample for this pipeline and generate a submission script anyway
    :param int lump_size: number of commands to lump into one script, i.e.
        job submission; default 1
    :return str, Iterable[str], Iterable[[str, str]]:
    """

    pl_name = pl_iface.get_pipeline_name(pl_key)

    scripts = []
    failures = []
    num_submissions = 0

    # Collect pairs of Sample and submission command so that we can place 
    # multiple commands within a single cluster submission script, and thus 
    # group processing of multiple samples for this pipeline into a single 
    # cluster job.
    curr_lump = []
    lump_index = 0

    for sdata in sample_data_bundles:

        sfolder = sample_folder(prj, sample=sdata)
        flag_files = glob.glob(os.path.join(sfolder, pl_name + "*.flag"))
        if not ignore_flags and len(flag_files) > 0:
            _LOGGER.info("> Not including sample '%s' in submission script "
                         "for pipeline '%s', flag(s) found: %s",
                         sdata[SAMPLE_NAME_COLNAME])
            # Message more directly analogous to the one for a sample
            # that's submitted, for debugging clarity.
            _LOGGER.debug("NOT SUBMITTED")
            continue

        sample = sample_subtype(sdata)
        _LOGGER.debug("Created %s instance: '%s'",
                      sample_subtype.__name__, sample.sample_name)
        sample.prj = grab_project_data(prj)

        # The current sample is active.
        # For each pipeline submission consideration, start fresh.
        skip_reasons = []

        _LOGGER.debug("Setting pipeline attributes for job '{}' "
                      "(PL_ID: '{}')".format(pl_job, pl_key))
        try:
            # Add pipeline-specific attributes.
            sample.set_pipeline_attributes(pl_iface, pipeline_name=pl_key)
        except AttributeError:
            # TODO: inform about WHICH missing attribute(s).
            fail_message = "Pipeline required attribute(s) missing"
            _LOGGER.warn("> Not submitted: %s", fail_message)
            skip_reasons.append(fail_message)

        # Check for any missing requirements before submitting.
        _LOGGER.debug("Determining missing requirements")
        error_type, missing_reqs_msg = \
            sample.determine_missing_requirements()
        if missing_reqs_msg:
            if prj.permissive:
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
            argstring = pl_iface.get_arg_string(
                pipeline_name=pl_key, sample=sample,
                submission_folder_path=prj.metadata.submission_subdir)
        except AttributeError:
            # TODO: inform about which missing attribute(s).
            fail_message = "Required attribute(s) missing " \
                           "for pipeline arguments string"
            _LOGGER.warn("> Not submitted: %s", fail_message)
            skip_reasons.append(fail_message)
        else:
            argstring += " "

        if skip_reasons:
            # Sample is active, but we've at least 1 pipeline skip reason.
            failures.append([skip_reasons, sample.sample_name])
            continue

        _LOGGER.info("> Building submission for Pipeline: '{}' "
                     "(input: {:.2f} Gb)".format(
                pl_job, sample.input_file_size))


        # Add this Sample and its argument string (to append to the base 
        # pipeline command) to the current lump.
        curr_lump.append((sample, argstring))
        if len(curr_lump) < lump_size:
            # We've not yet reached capacity for this lump.
            _LOGGER.debug("Growing lump")
            continue
            
        # Once control flow hits here, we're finished accumulating the 
        # sample and argument strings for the current lump, so it's time 
        # to determine the submission settings and create the script.
        _LOGGER.debug("Determining submission settings")
        total_input_size = sum(
                [float(sample.input_file_size) for file_size, _ in curr_lump])
        
        _LOGGER.debug("Creating submission script for sample '%s' "
                      "to pipeline '%s'", total_input_size, pl_name)

        # Identify cluster resources required for this submission.
        submit_settings = pl_iface.choose_resource_package(
                pl_key, total_input_size)

        # Reset the partition if it was specified on the command-line.
        submit_settings = update_partition(submit_settings)

        if pl_iface.uses_looper_args(pl_key):
            # These are looper_args, -C, -O, -M, and -P. If the pipeline
            # implements these arguments, then it lists looper_args=True,
            # and we add the arguments to the command string.
            looper_argtext = create_looper_args_text(
                    prj, pl_key, submit_settings)
        else:
            looper_argtext = ""

        # Project-level arguments (sample-agnostic) are handled separately.
        prj_argtext = prj.get_arg_string(pl_key)

        # Fore each sample, the entire command consists of the base pipeline 
        # job, arguments determined by the specific sample itself, arguments 
        # related to the project, and then looper options/arguments.
        # DEBUG
        assert pl_job is not None
        assert prj_argtext is not None
        assert looper_argtext is not None
        curr_lump_cmds = [pl_job + astring + prj_argtext + looper_argtext
                          for _, astring in curr_lump]

        # Add command string and job name to the submit_settings object.
        if 1 == lump_size:
            jobname = "{}_{}".format(sample.sample_name, pl_key)
        else:
            jobname = "{}_{}".format(pl_key, lump_index)
        submit_settings["JOBNAME"] = jobname
        submit_settings["CODE"] = "\n".join(curr_lump_cmds)

        status_message = "Creating submission script for pipeline {}".\
                format(pl_name)
        if 1 != lump_size:
            status_message += " ({} commands)".format(len(curr_lump))
        _LOGGER.debug(status_message)

        samples = [s for s, _ in curr_lump]
        submit_script = create_submission_script(
                samples, template_values=submit_settings, 
                template=prj.compute.submission_template, 
                submission_folder=prj.metadata.submission_subdir, 
                jobname=jobname, extra_args=extra_args)
        scripts.append(submit_script)
        num_submissions += len(samples)
        curr_lump = []
        lump_index += 1

    return num_submissions, scripts, failures



class Runner(Executor):
    """ The true submitter of pipelines """

    def __call__(self, args, remaining_args):
        """
        Do the Sample submission.
        
        :param argparse.Namespace args: parsed command-line options and 
            arguments, recognized by looper 
        :param list remaining_args: command-line options and arguments not 
            recognized by looper, germane to samples/pipelines
        """

        protocols = {s.protocol for s in self.prj.samples if hasattr(s, "protocol")}

        _LOGGER.info("Protocols: %s", ", ".join(protocols))

        # Keep track of how many jobs have been submitted.
        num_jobs = 0  # Some job templates will be skipped.
        submit_count = 0  # Some jobs won't be submitted.
        processed_samples = set()

        # Create a problem list so we can keep track and show them at the end.
        failures = []

        _LOGGER.info("Building submission bundle(s) for protocol(s): {}".
                     format(", ".join(self.prj.protocols)))
        submission_bundle_by_protocol = {
            alpha_cased(p): self.prj.build_submission_bundles(alpha_cased(p))
            for p in protocols
        }

        # Determine number of samples eligible for processing.
        num_samples = len(self.prj.samples)
        if args.limit is None:
            upper_sample_bound = num_samples
        elif args.limit < 0:
            raise ValueError(
                "Invalid number of samples to run: {}".format(args.limit))
        else:
            upper_sample_bound = min(args.limit, num_samples)
        _LOGGER.debug("Limiting to %d of %d samples", upper_sample_bound, num_samples)

        try:
            partition = self.prj.compute.partition
        except AttributeError:
            _LOGGER.debug("No partition to set")
            update_partition = lambda ss: ss
        else:
            def update_partition(ss):
                ss["partition"] = partition
                return ss

        # Each strict pipeline key maps to the same script + flags, the same 
        # Sample subtype, and the same PipelineInterface.
        script_subtype_iface_trio_by_pipeline_key = {}
        # Collect Sample data by strict pipeline key for submission.
        sample_data_by_pipeline_key = defaultdict(list)

        for sample in self.prj.samples[:upper_sample_bound]:
            # First, step through the samples and determine whether any
            # should be skipped entirely, based on sample attributes alone
            # and independent of anything about any of its pipelines.

            _LOGGER.info(self.counter.show(
                    sample.sample_name, sample.protocol))

            skip_reasons = []

            # Don't submit samples with duplicate names.
            if sample.sample_name in processed_samples:
                skip_reasons.append("Duplicate sample name")

            # Check if sample should be run.
            if sample.is_dormant():
                skip_reasons.append("Inactive status (via {})".
                                    format(SAMPLE_EXECUTION_TOGGLE))

            # Get the base protocol-to-pipeline mappings
            try:
                protocol = alpha_cased(sample.protocol)
            except AttributeError:
                skip_reasons.append("Sample has no protocol")
            else:
                protocol = protocol.upper()
                _LOGGER.debug("Fetching submission bundle, "
                              "using '%s' as protocol key", protocol)
                submission_bundles = \
                        submission_bundle_by_protocol.get(protocol)
                if not submission_bundles:
                    skip_reasons.append("No submission bundle for protocol")

            if skip_reasons:
                _LOGGER.warn(
                    "> Not submitted: {}".format(", ".join(skip_reasons)))
                failures.append([skip_reasons, sample.sample_name])
                continue

            # Processing preconditions have been met.
            # Add this sample to the processed collection.
            processed_samples.add(sample.sample_name)

            # At this point, we have a generic Sample; write that to disk
            # for reuse in case of many jobs (pipelines) using base Sample.
            # Do a single overwrite here, then any subsequent Sample can be sure
            # that the file is fresh, with respect to this run of looper.
            sample.to_yaml(subs_folder_path=self.prj.metadata.submission_subdir)

            # Store the base Sample data for reuse in creating subtype(s).
            sample_data = sample.as_series()

            # Each submission bundle corresponds to a particular pipeline
            # by which this sample should be processed. Pair the sample
            # data with the group/bundle of objects that will be used to
            # submit it.
            for pl_iface, sample_subtype, pl_key, flagged_script in \
                    submission_bundles:
                submit_data_trio = (flagged_script, sample_subtype, pl_iface)
                script_subtype_iface_trio_by_pipeline_key.setdefault(
                        pl_key, submit_data_trio)
                # Key by pipeline so that we can lump submissions for a
                # single pipeline together if desired.
                sample_data_by_pipeline_key[pl_key].append(sample_data)

        # Iterate over collection in which each pipeline key is mapped to
        # a collection of pairs of sample data and job submission bundle.
        assert set(sample_data_by_pipeline_key.keys()) == \
               set(script_subtype_iface_trio_by_pipeline_key.keys()), \
                "Collections of strict pipeline keys must be equal for " \
                "mapping to sample data and for mapping to submission data."

        # Now that we've remapped in terms of pipelines, we can submit
        # samples for processing in a per-pipeline fashion, facilitating
        # grouping of multiple samples into individual jobs, with one or
        # more jobs per pipeline.
        for pl_key in sample_data_by_pipeline_key.keys():

            # Extract the base pipeline command, sample subtype to use for
            # this pipeline, and the associated pipeline interface.
            pl_job, sample_subtype, pl_iface = \
                    script_subtype_iface_trio_by_pipeline_key[pl_key]

            # Pull of the collection of sample data bundles associated with
            # the current pipeline key; here sample_data is actually a
            # collection of mappings.
            sample_data = sample_data_by_pipeline_key[pl_key]
            num_jobs += len(sample_data)

            _LOGGER.info("Creating submissions for pipeline: '%s'", pl_key)

            pl_name, scripts, fail_reason_sample_pairs = \
                create_pipeline_submissions(
                    pl_key, pl_job, pl_iface, sample_subtype, sample_data,
                    self.prj, update_partition, extra_args=remaining_args,
                    lump_size=args.lump_size, ignore_flags=args.ignore_flags)
            failures.extend(fail_reason_sample_pairs)

            for submit_script in scripts:
                if args.dry_run:
                    _LOGGER.info(
                        "> DRY RUN: I would have submitted this: '%s'",
                        submit_script)
                else:
                    submission_command = "{} {}".format(
                        self.prj.compute.submission_command, submit_script)
                    subprocess.call(submission_command, shell=True)
                    # Delay next job's submission.
                    time.sleep(args.time_delay)
                _LOGGER.debug("SUBMITTED")
                submit_count += 1

        # Report what went down.
        _LOGGER.info("Looper finished")
        _LOGGER.info("Samples generating jobs: %d of %d",
                     len(processed_samples), len(self.prj.samples))
        _LOGGER.info("Jobs submitted: %d of %d", submit_count, num_jobs)
        if args.dry_run:
            _LOGGER.info("Dry run. No jobs were actually submitted.")
        if failures:
            _LOGGER.info("%d sample(s) with submission failure.",
                         len(failures))
            sample_by_reason = aggregate_exec_skip_reasons(failures)
            _LOGGER.info("{} unique reasons for submission failure: {}".format(
                len(sample_by_reason), ", ".join(sample_by_reason.keys())))
            _LOGGER.info("Samples by failure:\n{}".format(
                "\n".join(["{}: {}".format(failure, ", ".join(samples))
                           for failure, samples in sample_by_reason.items()])))



# TODO: remove once validation is assured in build_submission_bundles
def validate_submission_bundles(bundles):
    """
    Ensure that each pipeline key uniquely maps to a submission bundle.

    That is, each 'strict' pipeline key should have the same pipeline path + 
    flags, the same sable subtype, and the same pipeline interface.

    :param Iterable[(PipelineInterface, type, str, str)] bundles: collection
        of tuples of pipeline interface, sample subtype, strict pipeline key,
        and pipeline script path + flags
    :return bool: True if the validation succeeds
    :raise ValueError: if the validation fails
    """
    submission_data_by_key = {}
    for pl_iface, sample_subtype, strict_pipe_key, \
            pipe_path_with_flags in bundles:
        new_sub_data = (pipe_path_with_flags, sample_subtype, pl_iface)
        old_sub_data = submission_data_by_key.setdefault(
                strict_pipe_key, new_sub_data)
        if new_sub_data != old_sub_data:
            raise ValueError(
                    "Submission data mismatch; pipeline key '{}' maps "
                    "to at least two different submission bundles: {}\n{}".
                    format(strict_pipe_key, new_sub_data, old_sub_data))
    return True





class Summarizer(Executor):
    """ Project/Sample output summarizer """
    
    def __call__(self):
        """ Do the summarization. """
        import csv

        columns = []
        stats = []
        figs = []

        for sample in self.prj.samples:
            _LOGGER.info(self.counter.show(sample.sample_name, sample.protocol))
            sample_output_folder = sample_folder(self.prj, sample)

            # Grab the basic info from the annotation sheet for this sample.
            # This will correspond to a row in the output.
            sample_stats = sample.get_sheet_dict()
            columns.extend(sample_stats.keys())
            # Version 0.3 standardized all stats into a single file
            stats_file = os.path.join(sample_output_folder, "stats.tsv")
            if os.path.isfile(stats_file):
                _LOGGER.info("Found stats file: '%s'", stats_file)
            else:
                _LOGGER.warn("No stats file '%s'", stats_file)
                continue

            t = _pd.read_table(
                stats_file, header=None, names=['key', 'value', 'pl'])

            t.drop_duplicates(subset=['key', 'pl'], keep='last', inplace=True)
            # t.duplicated(subset= ['key'], keep = False)

            t.loc[:, 'plkey'] = t['pl'] + ":" + t['key']
            dupes = t.duplicated(subset=['key'], keep=False)
            t.loc[dupes, 'key'] = t.loc[dupes, 'plkey']

            sample_stats.update(t.set_index('key')['value'].to_dict())
            stats.append(sample_stats)
            columns.extend(t.key.tolist())

        self.counter.reset()

        for sample in self.prj.samples:
            _LOGGER.info(self.counter.show(sample.sample_name, sample.protocol))
            sample_output_folder = sample_folder(self.prj, sample)
            # Now process any reported figures
            figs_file = os.path.join(sample_output_folder, "figures.tsv")
            if os.path.isfile(figs_file):
                _LOGGER.info("Found figures file: '%s'", figs_file)
            else:
                _LOGGER.warn("No figures file '%s'", figs_file)
                continue

            t = _pd.read_table(
                figs_file, header=None, names=['key', 'value', 'pl'])

            t.drop_duplicates(subset=['key', 'pl'], keep='last', inplace=True)

            t.loc[:, 'plkey'] = t['pl'] + ":" + t['key']
            dupes = t.duplicated(subset=['key'], keep=False)
            t.loc[dupes, 'key'] = t.loc[dupes, 'plkey']

            figs.append(t)

        # all samples are parsed. Produce file.

        tsv_outfile_path = os.path.join(self.prj.metadata.output_dir, self.prj.name)
        if self.prj.subproject:
            tsv_outfile_path += '_' + self.prj.subproject
        tsv_outfile_path += '_stats_summary.tsv'

        tsv_outfile = open(tsv_outfile_path, 'w')

        tsv_writer = csv.DictWriter(tsv_outfile, fieldnames=uniqify(columns),
                                    delimiter='\t', extrasaction='ignore')
        tsv_writer.writeheader()

        for row in stats:
            tsv_writer.writerow(row)

        tsv_outfile.close()

        figs_tsv_path = "{root}_figs_summary.tsv".format(
            root=os.path.join(self.prj.metadata.output_dir, self.prj.name))

        figs_html_path = "{root}_figs_summary.html".format(
            root=os.path.join(self.prj.metadata.output_dir, self.prj.name))

        figs_html_file = open(figs_html_path, 'w')

        img_code = "<h1>{key}</h1><a href='{path}'><img src='{path}'></a>\n"
        for fig in figs:
            figs_html_file.write(img_code.format(
                key=str(fig['key']), path=fig['value']))

        figs_html_file.close()
        _LOGGER.info(
            "Summary (n=" + str(len(stats)) + "): " + tsv_outfile_path)



def aggregate_exec_skip_reasons(skip_reasons_sample_pairs):
    """
    Collect the reasons for skipping submission/execution of each sample

    :param Iterable[(Iterable[str], str)] skip_reasons_sample_pairs: pairs of
        collection of reasons for which a sample was skipped for submission,
        and the name of the sample itself
    :return Mapping[str, Iterable[str]]: mapping from explanation to
        collection of names of samples to which it pertains
    """
    samples_by_skip_reason = defaultdict(list)
    for skip_reasons, sample in skip_reasons_sample_pairs:
        for reason in set(skip_reasons):
            samples_by_skip_reason[reason].append(sample)
    return samples_by_skip_reason



class LooperCounter(object):
    """
    Count samples as you loop through them, and create text for the
    subcommand logging status messages.

    :param total: number of jobs to process
    :type total: int

    """
    def __init__(self, total):
        self.count = 0
        self.total = total

    def show(self, name, protocol):
        """
        Display sample counts status for a particular protocol type.
         
        The counts are running vs. total for the protocol within the Project, 
        and as a side-effect of the call, the running count is incremented.
        
        :param str name: name of the sample
        :param str protocol: name of the protocol
        :return str: message suitable for logging a status update
        """
        self.count += 1
        return _submission_status_text(
                curr=self.count, total=self.total, sample_name=name,
                sample_protocol=protocol, color=Fore.CYAN)

    def reset(self):
        self.count = 0

    def __str__(self):
        return "LooperCounter of size {}".format(self.total)


def _submission_status_text(curr, total, sample_name, sample_protocol, color):
    return color + \
           "## [{n} of {N}] {sample} ({protocol})".format(
                n=curr, N=total, sample=sample_name, protocol=sample_protocol) + \
           Style.RESET_ALL



def create_submission_script(
        samples, template_values, template, submission_folder, jobname,
        extra_args=None):
    """
    Write cluster submission script to disk and submit job for given Sample.

    :param Iterable[models.Sample] samples: Sample instances for submission
    :param Mapping[str, str] template_values: key-value pairs with which to 
        populate fields in the submission template
    :param str template: path to submission script template
    :param str submission_folder: path to the folder in which to place 
        submission files
    :param str jobname: name for the job that will be create/submitted when 
        this script is executed
    :param Iterable[str] extra_args: arguments for this submission, 
        unconsumed by previous option/argument parsing
    :return str: filepath to submission script
    """

    # Ensure existence of on-disk representation of each sample.
    for s in samples:
        if type(s) is Sample:
            # Runner writes base Sample to disk for each non-skipped sample,
            # so check for that if we're using a basic Sample.
            expected_filepath = os.path.join(
                    submission_folder, "{}.yaml".format(s.name))
            if not os.path.exists(expected_filepath):
                _LOGGER.warn("Missing base Sample file will be created: '%s'",
                             expected_filepath)
                s.to_yaml(subs_folder_path=submission_folder)
            else:
                _LOGGER.debug("Base Sample file exists")
        else:
            # Serialize Sample, generate data for disk, and write.
            name_s_subtype = s.__class__.__name__
            _LOGGER.debug("Writing %s representation to disk: '%s'",
                          name_s_subtype, s.name)
            s.to_yaml(subs_folder_path=submission_folder)
    
    # Create the script and logfile paths.
    submission_base = os.path.join(submission_folder, jobname)
    submit_script = submission_base + ".sub"
    template_values["LOGFILE"] = submission_base + ".log"

    # Prepare and write submission script.
    _LOGGER.info("> script: " + submit_script + " ")
    submit_script_dirpath = os.path.dirname(submit_script)
    if not os.path.exists(submit_script_dirpath):
        os.makedirs(submit_script_dirpath)

    # Add additional arguments, populate template fields, and write to disk.
    with open(template, 'r') as handle:
        filedata = handle.read()

    template_values["CODE"] += " " + str(" ".join(extra_args or []))

    for key, value in template_values.items():
        # Here we add brackets around the key names and use uppercase because
        # this is how they are encoded as variables in the submit templates.
        filedata = filedata.replace("{" + str(key).upper() + "}", str(value))

    with open(submit_script, 'w') as handle:
        handle.write(filedata)

    return submit_script



def query_yes_no(question, default="no"):
    """
    Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {
        "yes": True, "y": True, "ye": True,
        "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write(
                "Please respond with 'yes' or 'no' "
                "(or 'y' or 'n').\n")



def destroy_sample_results(result_outfolder, args):
    """
    This function will delete all results for this sample
    """
    import shutil
    if os.path.exists(result_outfolder):
        if args.dry_run:
            _LOGGER.info("DRY RUN. I would have removed: " + result_outfolder)
        else:
            _LOGGER.info("Removing: " + result_outfolder)
            shutil.rmtree(result_outfolder)
    else:
        _LOGGER.info(result_outfolder + " does not exist.")



def uniqify(seq):
    """
    Fast way to uniqify while preserving input order.
    """
    # http://stackoverflow.com/questions/480214/
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]



class Checker(Executor):

    def __call__(self, flags=None, all_folders=False, max_file_count=30):
        """
        Check Project status, based on flag files.

        :param Iterable[str] | str flags: Names of flags to check, optional;
            if unspecified, all known flags will be checked.
        :param bool all_folders: Whether to check flags in all folders, not
            just those for samples in the config file from which the Project
            was created.
        :param int max_file_count: Maximum number of filepaths to display for a
            given flag.
        """

        # Handle single or multiple flags, and alphabetize.
        flags = sorted([flags] if isinstance(flags, str)
                       else list(flags or FLAGS))
        flag_text = ", ".join(flags)

        # Collect the files by flag and sort by flag name.
        if all_folders:
            _LOGGER.info("Checking project folders for flags: %s", flag_text)
            files_by_flag = fetch_flag_files(
                results_folder=self.prj.metadata.results_subdir, flags=flags)
        else:
            _LOGGER.info("Checking project samples for flags: %s", flag_text)
            files_by_flag = fetch_flag_files(prj=self.prj, flags=flags)

        # For each flag, output occurrence count.
        for flag in flags:
            _LOGGER.info("%s: %d", flag.upper(), len(files_by_flag[flag]))

        # For each flag, output filepath(s) if not overly verbose.
        for flag in flags:
            try:
                files = files_by_flag[flag]
            except:
                # No files for flag.
                continue
            # Regardless of whether 0-count flags are previously reported,
            # don't report an empty file list for a flag that's absent.
            # If the flag-to-files mapping is defaultdict, absent flag (key)
            # will fetch an empty collection, so check for length of 0.
            if 0 < len(files) <= max_file_count:
                _LOGGER.info("%s (%d):\n%s", flag.upper(),
                             len(files), "\n".join(files))



def main():
    # Parse command-line arguments and establish logger.
    args, remaining_args = parse_arguments()

    _LOGGER.info("Command: {} (Looper version: {})".
                 format(args.command, __version__))
    # Initialize project
    _LOGGER.debug("compute_env_file: " + str(getattr(args, 'env', None)))
    _LOGGER.info("Building Project")
    if args.subproject is not None:
        _LOGGER.info("Using subproject: %s", args.subproject)
    prj = Project(
        args.config_file, subproject=args.subproject,
        file_checks=args.file_checks,
        compute_env_file=getattr(args, 'env', None))

    _LOGGER.info("Results subdir: " + prj.metadata.results_subdir)

    with ProjectContext(prj,
            include_protocols=args.include_protocols,
            exclude_protocols=args.exclude_protocols) as prj:

        if args.command == "run":
            if args.compute:
                prj.set_compute(args.compute)

            # TODO split here, spawning separate run process for each
            # pipelines directory in project metadata pipelines directory.

            if not hasattr(prj.metadata, "pipelines_dir") or \
                            len(prj.metadata.pipelines_dir) == 0:
                raise AttributeError(
                        "Looper requires at least one pipeline(s) location.")

            if not prj.interfaces_by_protocol:
                _LOGGER.error(
                        "The Project knows no protocols. Does it point "
                        "to at least one pipelines location that exists?")
                return

            run = Runner(prj)
            try:
                run(args, remaining_args)
            except IOError:
                _LOGGER.error("{} pipelines_dir: '{}'".format(
                        prj.__class__.__name__, prj.metadata.pipelines_dir))
                raise

        if args.command == "destroy":
            return Destroyer(prj)(args)

        if args.command == "summarize":
            Summarizer(prj)()

        if args.command == "check":
            # TODO: hook in fixed samples once protocol differentiation is
            # TODO (continued) figured out (related to #175).
            Checker(prj)(flags=args.flags)

        if args.command == "clean":
            return Cleaner(prj)(args)



if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _LOGGER.error("Program canceled by user!")
        sys.exit(1)
