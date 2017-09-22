#!/usr/bin/env python
"""
Looper: a pipeline submission engine. https://github.com/epigen/looper
"""

import argparse
from functools import partial
import glob
import logging
import os
import re
import subprocess
import sys
import time
import pandas as _pd
from . import setup_looper_logger, LOGGING_LEVEL, __version__
from .loodels import Project
from .utils import alpha_cased, VersionInHelpParser

try:
    from .models import \
        fetch_samples, PipelineInterface, ProjectContext, ProtocolMapper, \
        Sample, COMPUTE_SETTINGS_VARNAME, SAMPLE_EXECUTION_TOGGLE, \
        VALID_READ_TYPES
except:
    sys.path.append(os.path.join(os.path.dirname(__file__), "looper"))
    from models import \
        fetch_samples, PipelineInterface, ProjectContext, ProtocolMapper, \
        Sample, COMPUTE_SETTINGS_VARNAME, SAMPLE_EXECUTION_TOGGLE, \
        VALID_READ_TYPES

from colorama import init
init()
from colorama import Fore, Style

# Descending by severity for correspondence with logic inversion.
# That is, greater verbosity setting corresponds to lower logging level.
_LEVEL_BY_VERBOSITY = [logging.ERROR, logging.CRITICAL, logging.WARN,
                       logging.INFO, logging.DEBUG]

_LOGGER = logging.getLogger()
_COUNTER = None



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

    # Accommodate detailed help.
    preparser = argparse.ArgumentParser(add_help=False)
    preparser.add_argument("--details", action="store_true", default=False)
    args, remaining_args = preparser.parse_known_args()
    if args.details:
        suppress_details = False
    else:
        suppress_details = argparse.SUPPRESS
        additional_description += \
                "\n  For debug options, type: '%(prog)s -h --details'"

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
            help=suppress_details or "Optional output file for looper logs")
    parser.add_argument(
            "--verbosity", dest="verbosity",
            type=int, choices=range(len(_LEVEL_BY_VERBOSITY)),
            help=suppress_details or "Choose level of verbosity")
    parser.add_argument(
            "--logging-level", dest="logging_level",
            help=argparse.SUPPRESS)
    parser.add_argument(
            "--dbg", dest="dbg",
            action="store_true",
            help=suppress_details or "Turn on debug mode")

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
            "--limit", dest="limit",
            type=int,
            help="Limit to n samples.")

    # Other commands
    summarize_subparser = add_subparser("summarize")
    destroy_subparser = add_subparser("destroy")
    check_subparser = add_subparser("check")
    clean_subparser = add_subparser("clean")

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



def run(prj, args, remaining_args, get_samples=None):
    """
    Main Looper function: Submit jobs for samples in project.

    :param models.Project prj: configured Project instance
    :param argparse.Namespace args: arguments parsed by this module's parser
    :param Iterable[str] remaining_args: arguments given to this module's 
        parser that were not defined as options it should parse, 
        to be passed on to parser(s) elsewhere
    :param callable get_samples: strategy for looping over samples, optional; 
        if provided, this should accept a Project as an argument and return 
        a collection of Samples; if not provided, the ordinary project 
        version of this concept (over all of its Samples) is used
    """

    samples = _iter_proj(prj, get_samples)
    protocols = {s.protocol for s in samples if hasattr(s, "protocol")}

    _LOGGER.info("Protocols: %s", ", ".join(protocols))

    # Keep track of how many jobs have been submitted.
    job_count = 0            # Some job templates will be skipped.
    submit_count = 0         # Some jobs won't be submitted.
    processed_samples = set()

    # Create a problem list so we can keep track and show them at the end.
    failures = []

    _LOGGER.info("Building submission bundle(s) for protocol(s): {}".
                 format(", ".join(prj.protocols)))
    submission_bundle_by_protocol = {
            alpha_cased(p): prj.build_submission_bundles(alpha_cased(p))
            for p in protocols
    }

    for sample in samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.protocol))

        sample_output_folder = prj.sample_folder(sample)
        _LOGGER.debug("Sample output folder: '%s'", sample_output_folder)
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
            submission_bundles = submission_bundle_by_protocol.get(protocol)
            if not submission_bundles:
                skip_reasons.append("No submission bundle for protocol")

        if skip_reasons:
            _LOGGER.warn("> Not submitted: {}".format(", ".join(skip_reasons)))
            failures.append([skip_reasons, sample.sample_name])
            continue

        # TODO: determine what to do with subtype(s) here.
        # Processing preconditions have been met.
        processed_samples.add(sample.sample_name)

        # At this point, we have a generic Sample; write that to disk
        # for reuse in case of many jobs (pipelines) using base Sample.
        # Do a single overwrite here, then any subsequent Sample can be sure
        # that the file is fresh, with respect to this run of looper.
        sample.to_yaml(subs_folder_path=prj.metadata.submission_subdir)

        # Store the base Sample data for reuse in creating subtype(s).
        sample_data = sample.as_series()

        # Go through all pipelines to submit for this protocol.
        # Note: control flow doesn't reach this point if variable "pipelines"
        # cannot be assigned (library/protocol missing).
        # pipeline_key (previously pl_id) is no longer necessarily
        # script name, it's more flexible.
        for pipeline_interface, sample_subtype, pipeline_key, pipeline_job in \
                submission_bundles:
            job_count += 1

            _LOGGER.debug("Creating %s instance: '%s'",
                          sample_subtype.__name__, sample.sample_name)
            sample = sample_subtype(sample_data)

            # The full Project reference is provided here, but this sample
            # is only in existence for the duration of the outer loop. Plus,
            # when the Sample is written to disk as a YAML file, only certain
            # sections that are more likely to be of use in downstream analysis
            # are written. Nonetheless, it seems possible that this sort of
            # bare-bones inclusion of Project data within the Sample could
            # instead be accomplished here, disallowing a Project to be passed
            # to the Sample, as it appears that use of the Project reference
            # within Sample has been factored out.
            sample.prj = prj

            # The current sample is active.
            # For each pipeline submission consideration, start fresh.
            skip_reasons = []

            _LOGGER.debug("Setting pipeline attributes for job '{}' "
                          "(PL_ID: '{}')".format(pipeline_job, pipeline_key))
            try:
                # Add pipeline-specific attributes.
                sample.set_pipeline_attributes(
                        pipeline_interface, pipeline_name=pipeline_key)
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

            # Identify cluster resources required for this submission.
            submit_settings = pipeline_interface.choose_resource_package(
                    pipeline_key, sample.input_file_size)

            # Reset the partition if it was specified on the command-line.
            try:
                submit_settings["partition"] = prj.compute.partition
            except AttributeError:
                _LOGGER.debug("No partition to reset")

            # Pipeline name is the key used for flag checking.
            pl_name = pipeline_interface.get_pipeline_name(pipeline_key)

            # Build basic command line string
            cmd = pipeline_job

            # Append arguments for this pipeline
            # Sample-level arguments are handled by the pipeline interface.
            try:
                argstring = pipeline_interface.get_arg_string(
                        pipeline_name=pipeline_key, sample=sample,
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
                         "(input: {:.2f} Gb)".format(pipeline_job,
                                                     sample.input_file_size))

            # Project-level arguments (sample-agnostic) are handled separately.
            argstring += prj.get_arg_string(pipeline_key)
            cmd += argstring

            if pipeline_interface.uses_looper_args(pipeline_key):
                # These are looper_args, -C, -O, -M, and -P. If the pipeline
                # implements these arguments, then it lists looper_args=True,
                # and we add the arguments to the command string.

                if hasattr(prj, "pipeline_config"):
                    # Index with 'pipeline_key' instead of 'pipeline'
                    # because we don't care about parameters here.
                    if hasattr(prj.pipeline_config, pipeline_key):
                        # First priority: pipeline config in project config
                        pl_config_file = getattr(prj.pipeline_config,
                                                 pipeline_key)
                        # Make sure it's a file (it could be provided as null.)
                        if pl_config_file:
                            if not os.path.isfile(pl_config_file):
                                _LOGGER.error("Pipeline config file specified "
                                              "but not found: %s",
                                              str(pl_config_file))
                                raise IOError(pl_config_file)
                            _LOGGER.info("Found config file: %s",
                                         str(getattr(prj.pipeline_config,
                                                     pipeline_key)))
                            # Append arg for config file if found
                            cmd += " -C " + pl_config_file

                cmd += " -O " + prj.metadata.results_subdir
                if int(submit_settings.setdefault("cores", 1)) > 1:
                    cmd += " -P " + submit_settings["cores"]
                try:
                    if float(submit_settings["mem"]) > 1:
                        cmd += " -M " + submit_settings["mem"]
                except KeyError:
                    _LOGGER.warn("Submission settings "
                                 "lack memory specification")

            # Add command string and job name to the submit_settings object.
            submit_settings["JOBNAME"] = \
                    sample.sample_name + "_" + pipeline_key
            submit_settings["CODE"] = cmd

            # Create submission script (write script to disk)!
            _LOGGER.debug("Creating submission script for pipeline %s: '%s'",
                          pl_name, sample.sample_name)
            submit_script = create_submission_script(
                    sample, prj.compute.submission_template, submit_settings,
                    submission_folder=prj.metadata.submission_subdir,
                    pipeline_name=pl_name, remaining_args=remaining_args)

            # Determine how to update submission counts and (perhaps) submit.
            flag_files = glob.glob(os.path.join(
                    sample_output_folder, pl_name + "*.flag"))
            if not args.ignore_flags and len(flag_files) > 0:
                _LOGGER.info("> Not submitting, flag(s) found: {}".
                             format(flag_files))
                _LOGGER.debug("NOT SUBMITTED")
            else:
                if args.dry_run:
                    _LOGGER.info("> DRY RUN: I would have submitted this: '%s'",
                                 submit_script)
                else:
                    submission_command = "{} {}".format(
                            prj.compute.submission_command, submit_script)
                    subprocess.call(submission_command, shell=True)
                    time.sleep(args.time_delay)  # Delay next job's submission.
                _LOGGER.debug("SUBMITTED")
                submit_count += 1

    # Report what went down.
    _LOGGER.info("Looper finished")
    _LOGGER.info("Samples generating jobs: %d of %d",
                 len(processed_samples), len(samples))
    _LOGGER.info("Jobs submitted: %d of %d", submit_count, job_count)
    if args.dry_run:
        _LOGGER.info("Dry run. No jobs were actually submitted.")
    if failures:
        _LOGGER.info("%d sample(s) with submission failure.", len(failures))
        sample_by_reason = aggregate_exec_skip_reasons(failures)
        _LOGGER.info("{} unique reasons for submission failure: {}".format(
                len(sample_by_reason), ", ".join(sample_by_reason.keys())))
        _LOGGER.info("Samples by failure:\n{}".format(
            "\n".join(["{}: {}".format(failure, ", ".join(samples))
                       for failure, samples in sample_by_reason.items()])))



def aggregate_exec_skip_reasons(skip_reasons_sample_pairs):
    """
    Collect the reasons for skipping submission/execution of each sample

    :param Iterable[(Iterable[str], str)] skip_reasons_sample_pairs: pairs of
        collection of reasons for which a sample was skipped for submission,
        and the name of the sample itself
    :return Mapping[str, Iterable[str]]: mapping from explanation to
        collection of names of samples to which it pertains
    """
    from collections import defaultdict
    samples_by_skip_reason = defaultdict(list)
    for skip_reasons, sample in skip_reasons_sample_pairs:
        for reason in set(skip_reasons):
            samples_by_skip_reason[reason].append(sample)
    return samples_by_skip_reason



def _iter_proj(prj, get_samples=None):
    """
    Initialize iteration for a looper program, over Samples from a Project.

    :param Project prj: Project with which to work, of which the Samples
        operated on will be a subset
    :param callable get_samples: strategy for looping over samples, optional;
        if provided, this should accept a Project as an argument and return
        a collection of Samples; if not provided, the ordinary project
        version of this concept (over all of its Samples) is used
    :return Iterable[Sample]: collection of Samples to iterate over,
        performing arbitrary operations on each one
    """
    samples = prj.samples if get_samples is None else get_samples(prj)
    _start_counter(len(samples))
    return samples



def summarize(prj, get_samples=None):
    """
    Grab the report_results stats files from each sample and collate them.
    The result is a single matrix (written as a csv file).

    :param Project prj: the Project to summarize
    :param callable get_samples: strategy for looping over samples, optional;
        if provided, this should accept a Project as an argument and return
        a collection of Samples; if not provided, the ordinary project
        version of this concept (over all of its Samples) is used
    """

    import csv
    columns = []
    stats = []
    figs = []

    samples = _iter_proj(prj, get_samples)

    for sample in samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.protocol))
        sample_output_folder = prj.sample_folder(sample)

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

    for sample in samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.protocol))
        sample_output_folder = prj.sample_folder(sample)
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

    tsv_outfile_path = os.path.join(prj.metadata.output_dir, prj.name)
    if prj.subproject:
        tsv_outfile_path += '_' + prj.subproject
    tsv_outfile_path += '_stats_summary.tsv'

    tsv_outfile = open(tsv_outfile_path, 'w')

    tsv_writer = csv.DictWriter(tsv_outfile, fieldnames=uniqify(columns),
                                delimiter='\t', extrasaction='ignore')
    tsv_writer.writeheader()

    for row in stats:
        tsv_writer.writerow(row)

    tsv_outfile.close()

    figs_tsv_path = "{root}_figs_summary.tsv".format(
        root=os.path.join(prj.metadata.output_dir, prj.name))


    figs_html_path = "{root}_figs_summary.html".format(
        root=os.path.join(prj.metadata.output_dir, prj.name))

    figs_html_file = open(figs_html_path, 'w')

    img_code ="<h1>{key}</h1><a href='{path}'><img src='{path}'></a>\n"
    for fig in figs:
        figs_html_file.write(img_code.format(
            key=str(fig['key']), path=fig['value']))

    figs_html_file.close()
    _LOGGER.info("Summary (n=" + str(len(stats)) + "): " + tsv_outfile_path)



def clean(prj, args, preview_flag=True, get_samples=None):
    """
    Remove all project's intermediate files (defined by pypiper clean scripts).

    :param Project prj: current working Project
    :param argparse.Namespace args: command-line options and arguments
    :param bool preview_flag: whether to halt before actually removing files
    :param callable get_samples: strategy for looping over samples, optional;
        if provided, this should accept a Project as an argument and return
        a collection of Samples; if not provided, the ordinary project
        version of this concept (over all of its Samples) is used
    """

    _LOGGER.info("Files to clean:")

    samples = _iter_proj(prj, get_samples)

    for sample in samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.protocol))
        sample_output_folder = prj.sample_folder(sample)
        cleanup_files = glob.glob(os.path.join(sample_output_folder,
                                               "*_cleanup.sh"))
        if preview_flag:
            # Preview: Don't actually clean, just show what will be cleaned.
            _LOGGER.info(str(cleanup_files))
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

    return clean(prj, args, preview_flag=False)



def destroy(prj, args, preview_flag=True, get_samples=None):
    """
    Completely removes all output files and folders produced by any pipelines.

    :param Project prj: current working Project
    :param argparse.Namespace args: command-line options and arguments
    :param bool preview_flag: whether to halt before actually removing files
    :param callable get_samples: strategy for looping over samples, optional;
        if provided, this should accept a Project as an argument and return
        a collection of Samples; if not provided, the ordinary project
        version of this concept (over all of its Samples) is used
    """

    _LOGGER.info("Results to destroy:")

    samples = _iter_proj(prj, get_samples)

    for sample in samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.protocol))
        sample_output_folder = prj.sample_folder(sample)
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

    # Finally, run the true destroy:

    return destroy(prj, args, preview_flag=False, get_samples=get_samples)



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

    def __str__(self):
        return "LooperCounter of size {}".format(self.total)


def _submission_status_text(curr, total, sample_name, sample_protocol, color):
    return color + \
           "## [{n} of {N}] {sample} ({protocol})".format(
                n=curr, N=total, sample=sample_name, protocol=sample_protocol) + \
           Style.RESET_ALL



def create_submission_script(
        sample, submit_template, variables_dict,
        submission_folder, pipeline_name, remaining_args=None):
    """
    Write cluster submission script to disk and submit job for given Sample.

    :param models.Sample sample: the Sample object for submission
    :param str submit_template: path to submission script template
    :param variables_dict: key-value pairs to use to populate fields in 
        the submission template
    :param str submission_folder: path to the folder in which to place 
        submission files
    :param str pipeline_name: name of the pipeline that the job will run
    :param Iterable[str] remaining_args: arguments for this submission, 
        unconsumed by previous option/argument parsing
    :return str: filepath to submission script
    """

    # Create the script and logfile paths.
    submission_base = os.path.join(
        submission_folder, "{}_{}".format(sample.sample_name, pipeline_name))
    submit_script = submission_base + ".sub"
    variables_dict["LOGFILE"] = submission_base + ".log"

    # Prepare and write submission script.
    _LOGGER.info("> script: " + submit_script + " ")
    submit_script_dirpath = os.path.dirname(submit_script)
    if not os.path.exists(submit_script_dirpath):
        os.makedirs(submit_script_dirpath)

    # Add additional arguments, populate template fields, and write to disk.
    with open(submit_template, 'r') as handle:
        filedata = handle.read()
    variables_dict["CODE"] += " " + str(" ".join(remaining_args or []))
    for key, value in variables_dict.items():
        # Here we add brackets around the key names and use uppercase because
        # this is how they are encoded as variables in the submit templates.
        filedata = filedata.replace("{" + str(key).upper() + "}", str(value))
    with open(submit_script, 'w') as handle:
        handle.write(filedata)

    # Ensure existence of on-disk representation of this sample.
    if type(sample) is Sample:
        # run() writes base Sample to disk for each non-skipped sample.
        expected_filepath = os.path.join(
                submission_folder, "{}.yaml".format(sample.name))
        _LOGGER.debug("Base Sample, to reuse file: '%s'",
                      expected_filepath)
        if not os.path.exists(expected_filepath):
            _LOGGER.warn("Missing expected Sample file; creating")
            sample.to_yaml(subs_folder_path=submission_folder)
        else:
            _LOGGER.debug("Base Sample file exists")
    else:
        # Serialize Sample, generate data for disk, and write.
        name_sample_subtype = sample.__class__.__name__
        _LOGGER.debug("Writing %s representation to disk: '%s'",
                      name_sample_subtype, sample.name)
        sample.to_yaml(subs_folder_path=submission_folder)

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



def check(prj):
    """
    Check Project status, based on flag files.
    
    :param Project prj: Project for which to inquire about status
    """

    # TODO: resume here to hook into specific protocols, and if we want
    # TODO (continued): to just use Python rather than shelling out.
    from collections import defaultdict
    flags_by_protocol = defaultdict(list)

    # prefix
    pf = "ls " + prj.metadata.results_subdir + "/"
    cmd = os.path.join(pf + "*/*.flag | xargs -n1 basename | sort | uniq -c")
    _LOGGER.info(cmd)
    subprocess.call(cmd, shell=True)

    flags = ["completed", "running", "failed", "waiting"]

    counts = {}
    for f in flags:
        counts[f] = int(subprocess.check_output(
                pf + "*/*" + f + ".flag 2> /dev/null | wc -l", shell=True))

    for f, count in counts.items():
        if 0 < count < 30:
            _LOGGER.info(f + " (" + str(count) + ")")
            subprocess.call(pf + "*/*" + f + ".flag 2> /dev/null", shell=True)



def _start_counter(total):
    """
    Start counting processed jobs/samples;
    called by each subcommand program that counts.

    :param int total: upper bound on processing count
    """
    global _COUNTER
    _COUNTER = LooperCounter(total)



def main():
    # Parse command-line arguments and establish logger.
    args, remaining_args = parse_arguments()

    _LOGGER.info("Command: {} (Looper version: {})".
                 format(args.command, __version__))
    # Initialize project
    _LOGGER.debug("compute_env_file: " + str(getattr(args, 'env', None)))
    prj = Project(
        args.config_file, args.subproject,
        file_checks=args.file_checks,
        compute_env_file=getattr(args, 'env', None))

    _LOGGER.info("Results subdir: " + prj.metadata.results_subdir)

    get_samples = partial(fetch_samples,
        inclusion=args.include_protocols, exclusion=args.exclude_protocols)

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
            try:
                run(prj, args, remaining_args, get_samples=get_samples)
            except IOError:
                _LOGGER.error("{} pipelines_dir: '{}'".format(
                        prj.__class__.__name__, prj.metadata.pipelines_dir))
                raise

        if args.command == "destroy":
            return destroy(prj, args, get_samples=get_samples)

        if args.command == "summarize":
            summarize(prj, get_samples=get_samples)

        if args.command == "check":
            # TODO: hook in fixed samples once protocol differentiation is
            # TODO (continued) figured out (related to #175).
            check(prj)

        if args.command == "clean":
            clean(prj, args, get_samples=get_samples)



if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _LOGGER.error("Program canceled by user!")
        sys.exit(1)
