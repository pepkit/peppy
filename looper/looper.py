#!/usr/bin/env python
"""
Looper: a pipeline submission engine. https://github.com/epigen/looper
"""

import abc
import argparse
from collections import defaultdict
import glob
import logging
import os
import subprocess
import sys
import pandas as _pd
from . import \
    setup_looper_logger, FLAGS, GENERIC_PROTOCOL_KEY, \
    LOGGING_LEVEL, __version__
from .exceptions import JobSubmissionException
from .loodels import Project
from .models import \
    ProjectContext, COMPUTE_SETTINGS_VARNAME, SAMPLE_EXECUTION_TOGGLE
from .submission_manager import SubmissionConductor
from .utils import \
    alpha_cased, fetch_flag_files, sample_folder, VersionInHelpParser


from colorama import init
init()
from colorama import Fore, Style

# Descending by severity for correspondence with logic inversion.
# That is, greater verbosity setting corresponds to lower logging level.
_LEVEL_BY_VERBOSITY = [logging.ERROR, logging.CRITICAL, logging.WARN,
                       logging.INFO, logging.DEBUG]
_FAIL_DISPLAY_PROPORTION_THRESHOLD = 0.5
_MAX_FAIL_SAMPLE_DISPLAY = 20
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
    # Note that defaults for otherwise numeric lump parameters are set to
    # null by default so that the logic that parses their values may
    # distinguish between explicit 0 and lack of specification.
    run_subparser.add_argument(
            "--lump", type=float, default=None,
            help="Maximum total input file size for a lump/batch of commands "
                 "in a single job")
    run_subparser.add_argument(
            "--lumpn", type=int, default=None,
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

        protocols = {s.protocol for s in self.prj.samples
                     if hasattr(s, "protocol")}
        failures = defaultdict(list)  # Collect problems by sample.
        processed_samples = set()  # Enforce one-time processing.

        _LOGGER.info("Finding pipelines for protocol(s): {}".
                     format(", ".join(self.prj.protocols)))

        # Job submissions are managed on a per-pipeline basis so that
        # individual commands (samples) may be lumped into a single job.
        submission_conductors = {}
        pipe_keys_by_protocol = defaultdict(list)
        mapped_protos = set()
        for proto in protocols | {GENERIC_PROTOCOL_KEY}:
            proto_key = alpha_cased(proto)
            submission_bundles = self.prj.build_submission_bundles(proto_key)
            if not submission_bundles:
                if proto_key != GENERIC_PROTOCOL_KEY:
                    _LOGGER.warn("No mapping for protocol: '%s'", proto)
                continue
            mapped_protos.add(proto)
            for pl_iface, sample_subtype, pl_key, script_with_flags in \
                    submission_bundles:
                conductor = SubmissionConductor(
                        pl_key, pl_iface, script_with_flags, self.prj,
                        args.dry_run, args.time_delay, sample_subtype,
                        remaining_args, args.ignore_flags,
                        self.prj.compute.partition,
                        max_cmds=args.lumpn, max_size=args.lump)
                submission_conductors[pl_key] = conductor
                pipe_keys_by_protocol[proto_key].append(pl_key)

        # Determine number of samples eligible for processing.
        num_samples = len(self.prj.samples)
        if args.limit is None:
            upper_sample_bound = num_samples
        elif args.limit < 0:
            raise ValueError(
                "Invalid number of samples to run: {}".format(args.limit))
        else:
            upper_sample_bound = min(args.limit, num_samples)
        _LOGGER.debug("Limiting to %d of %d samples",
                      upper_sample_bound, num_samples)

        num_commands_possible = 0
        failed_submission_scripts = []

        for sample in self.prj.samples[:upper_sample_bound]:
            # First, step through the samples and determine whether any
            # should be skipped entirely, based on sample attributes alone
            # and independent of anything about any of its pipelines.

            # Start by displaying the sample index and a fresh collection
            # of sample-skipping reasons.
            _LOGGER.info(self.counter.show(
                    sample.sample_name, sample.protocol))
            skip_reasons = []

            # Don't submit samples with duplicate names.
            if sample.sample_name in processed_samples:
                skip_reasons.append("Duplicate sample name")

            # Check if sample should be run.
            if sample.is_dormant():
                skip_reasons.append(
                        "Inactive status (via '{}' column/attribute)".
                        format(SAMPLE_EXECUTION_TOGGLE))

            # Get the base protocol-to-pipeline mappings.
            try:
                protocol = sample.protocol
            except AttributeError:
                skip_reasons.append("Sample has no protocol")
            else:
                if protocol not in mapped_protos and \
                        GENERIC_PROTOCOL_KEY not in mapped_protos:
                    skip_reasons.append("No pipeline for protocol")

            if skip_reasons:
                _LOGGER.warn(
                    "> Not submitted: {}".format(", ".join(skip_reasons)))
                failures[sample.name] = skip_reasons
                continue

            # Processing preconditions have been met.
            # Add this sample to the processed collection.
            processed_samples.add(sample.sample_name)

            # At this point, we have a generic Sample; write that to disk
            # for reuse in case of many jobs (pipelines) using base Sample.
            # Do a single overwrite here, then any subsequent Sample can be sure
            # that the file is fresh, with respect to this run of looper.
            sample.to_yaml(subs_folder_path=self.prj.metadata.submission_subdir)

            pipe_keys = pipe_keys_by_protocol.get(alpha_cased(sample.protocol)) \
                        or pipe_keys_by_protocol.get(GENERIC_PROTOCOL_KEY)
            _LOGGER.debug("Considering %d pipeline(s)", len(pipe_keys))

            pl_fails = []
            for pl_key in pipe_keys:
                num_commands_possible += 1
                # TODO: of interest to track failures by pipeline?
                conductor = submission_conductors[pl_key]
                # TODO: check return value from add() to determine whether
                # TODO (cont.) to grow the failures list.
                try:
                    curr_pl_fails = conductor.add_sample(sample)
                except JobSubmissionException as e:
                    failed_submission_scripts.append(e.script)
                else:
                    pl_fails.extend(curr_pl_fails)
            if pl_fails:
                failures[sample.name].extend(pl_fails)

        job_sub_total = 0
        cmd_sub_total = 0
        for conductor in submission_conductors.values():
            conductor.submit(force=True)
            job_sub_total += conductor.num_job_submissions
            cmd_sub_total += conductor.num_cmd_submissions

        # Report what went down.
        _LOGGER.info("Looper finished")
        _LOGGER.info("Samples qualified for job generation: %d of %d",
                     len(processed_samples), len(self.prj.samples))
        _LOGGER.info("Commands submitted: %d of %d",
                     cmd_sub_total, num_commands_possible)
        _LOGGER.info("Jobs submitted: %d", job_sub_total)
        if args.dry_run:
            _LOGGER.info("Dry run. No jobs were actually submitted.")

        _LOGGER.info("%d faulty samples.", len(failures))

        # Restructure sample/failure data for display.
        samples_by_reason = defaultdict(set)
        # Collect names of failed sample(s) by failure reason.
        for sample, failures in failures.items():
            for f in failures:
                samples_by_reason[f].add(sample)
        # Collect samples by pipeline with submission failure.
        failed_samples_by_pipeline = defaultdict(set)
        for pl_key, conductor in submission_conductors.items():
            # Don't add failure key if there are no samples that failed for
            # that reason.
            if conductor.failed_samples:
                fails = set(conductor.failed_samples)
                samples_by_reason["Job submission failure"] |= fails
                failed_samples_by_pipeline[pl_key] |= fails

        failed_sub_samples = samples_by_reason["Job submission failure"]
        _LOGGER.info("{} samples with at least one failed job submission: {}".
                     format(len(failed_sub_samples),
                            ", ".join(failed_sub_samples)))

        # If failure keys are only added when there's at least one sample that
        # failed for that reason, we can display information conditionally,
        # depending on whether there's actually failure(s).
        if samples_by_reason:
            _LOGGER.info("{} unique reasons for submission failure: {}".format(
                len(samples_by_reason), ", ".join(samples_by_reason.keys())))
            full_fail_msgs = [create_failure_message(reason, samples)
                              for reason, samples in samples_by_reason.items()]
            _LOGGER.info("Samples by failure:\n{}".
                         format("\n".join(full_fail_msgs)))

        if failed_submission_scripts:
            _LOGGER.info(
                    Fore.LIGHTRED_EX +
                    "\n{} scripts with failed submission: ".
                    format(len(failed_submission_scripts)) + Style.RESET_ALL +
                    ", ".join(failed_submission_scripts))



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
        if hasattr(self.prj, "subproject") and self.prj.subproject:
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



def create_failure_message(reason, samples):
    """ Explain lack of submission for a single reason, 1 or more samples. """
    color = Fore.LIGHTRED_EX
    reason_text = color + reason + Style.RESET_ALL
    samples_text = ", ".join(samples)
    return "{}: {}".format(reason_text, samples_text)



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
