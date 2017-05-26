#!/usr/bin/env python

"""
Looper

a pipeline submission engine.
https://github.com/epigen/looper
"""

import argparse
import glob
import logging
import os
import re
import subprocess
import sys
import time
import pandas as _pd
from . import setup_looper_logger, LOGGING_LEVEL, __version__, LOOPERENV_VARNAME
from loodels import Project
from utils import VersionInHelpParser

try:
    from .models import \
        InterfaceManager, PipelineInterface, \
        ProtocolMapper
except:
    sys.path.append(os.path.join(os.path.dirname(__file__), "looper"))
    from models import \
        InterfaceManager, PipelineInterface, \
        ProtocolMapper

from colorama import init
init()
from colorama import Fore, Style

SAMPLE_EXECUTION_TOGGLE = "toggle"

_LEVEL_BY_VERBOSITY = [logging.ERROR, logging.CRITICAL, logging.WARN,
                       logging.INFO, logging.DEBUG]

_LOGGER = logging.getLogger()
_COUNTER = None



def parse_arguments():
    """
    Argument Parsing.

    :return argparse.Namespace, list[str]: namespace parsed according to
        arguments defined here, them undefined arguments
    """

    description = "%(prog)s - Loop through samples and submit pipelines for them."
    epilog = "For subcommand-specific options, type: '%(prog)s <subcommand> -h'"
    epilog += "\nhttps://github.com/epigen/looper"

    parser = VersionInHelpParser(
        description=description, epilog=epilog,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-V", "--version", action="version",
                  version="%(prog)s {v}".format(v=__version__))

    # Logging control
    parser.add_argument("--logfile",
                        help=argparse.SUPPRESS)
    parser.add_argument("--verbosity",
                        type=int,
                        choices=range(len(_LEVEL_BY_VERBOSITY)),
                        help=argparse.SUPPRESS)
    parser.add_argument("--logging-level",
                        help=argparse.SUPPRESS)
    parser.add_argument("--dbg",
                        action="store_true",
                        help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="command")

    # Run command
    run_subparser = subparsers.add_parser(
            "run",
            help="Main Looper function: Submit jobs for samples.")
    run_subparser.add_argument(
            "-t",
            "--time-delay",
            type=int,
            default=0,
            help="Time delay in seconds between job submissions.")
    run_subparser.add_argument(
            "--ignore-flags",
            action="store_true",
            help="Ignore run status flags? Default: False. "
                 "By default, pipelines will not be submitted if a pypiper "
                 "flag file exists marking the run (e.g. as "
                 "'running' or 'failed'). Set this option to ignore flags "
                 "and submit the runs anyway.")
    run_subparser.add_argument(
            "--compute",
            help="YAML file with looper environment compute settings.")
    run_subparser.add_argument(
            "--env",
            default=os.getenv("{}".format(LOOPERENV_VARNAME), ""),
            help="Employ looper environment compute settings.")
    run_subparser.add_argument(
            "--limit",
            type=int,
            help="Limit to n samples.")

    # Summarize command
    summarize_subparser = subparsers.add_parser(
            "summarize",
            help="Summarize statistics of project samples.")

    # Destroy command
    destroy_subparser = subparsers.add_parser(
            "destroy",
            help="Remove all files of the project.")

    # Check command
    check_subparser = subparsers.add_parser(
            "check",
            help="Checks flag status of current runs.")

    clean_subparser = subparsers.add_parser(
            "clean",
            help="Runs clean scripts to remove intermediate "
                 "files of already processed jobs.")

    # Common arguments
    for subparser in [run_subparser, summarize_subparser,
                destroy_subparser, check_subparser, clean_subparser]:
        subparser.add_argument(
                "config_file",
                help="Project YAML config file.")
        subparser.add_argument(
                "--file-checks",
                action="store_false",
                help="Perform input file checks. Default=True.")
        subparser.add_argument(
                "-d",
                "--dry-run",
                action="store_true",
                help="Don't actually submit.")
        subparser.add_argument(
                "--sp",
                dest="subproject",
                help="Supply subproject")

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



def run(prj, args, remaining_args, interface_manager):
    """
    Main Looper function: Submit jobs for samples in project.

    :param models.Project prj: configured Project instance
    :param argparse.Namespace args: arguments parsed by this module's parser
    :param Iterable[str] remaining_args: arguments given to this module's 
        parser that were not defined as options it should parse, 
        to be passed on to parser(s) elsewhere
    :param InterfaceManager interface_manager: aggregator and manager of
        pipeline interfaces and protocol mappings
    """

    # Easier change later, especially likely for library --> protocol.
    _read_type = "read_type"
    _protocol = "library"

    _start_counter(len(prj.samples))

    valid_read_types = ["single", "paired"]

    # Keep track of how many jobs have been submitted.
    submit_count = 0
    job_count = 0
    processed_samples = set()

    # Create a problem list so we can keep track and show them at the end.
    failures = []

    for sample in prj.samples:
        _LOGGER.debug(sample)
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.library))

        pipeline_outfolder = os.path.join(
                prj.metadata.results_subdir, sample.sample_name)
        _LOGGER.debug("Pipeline output folder: '%s'", pipeline_outfolder)
        skip_reasons = []

        # Don't submit samples with duplicate names.
        if sample.sample_name in processed_samples:
            skip_reasons.append("Duplicate sample name.")

        # Check if sample should be run.
        if hasattr(sample, SAMPLE_EXECUTION_TOGGLE):
            if sample[SAMPLE_EXECUTION_TOGGLE] != "1":
                skip_reasons.append("Column '{}' deselected.".format(SAMPLE_EXECUTION_TOGGLE))

        # Check if single_or_paired value is recognized.
        if hasattr(sample, _read_type):
            # Drop "-end", "_end", or just "end" from end of the column value.
            sample.read_type = re.sub(
                    '[_\\-]?end$', '', str(sample.read_type)).lower()
            if sample.read_type not in valid_read_types:
                skip_reasons.append("{} must be in {}.".\
                    format(_read_type, valid_read_types))

        # Get the base protocol-to-pipeline mappings
        if hasattr(sample, _protocol):
            protocol = sample.library.upper()
            pipelines = interface_manager.build_pipelines(protocol)
            if len(pipelines) == 0:
                skip_reasons.append(
                        "No pipeline found for protocol {}.".format(protocol))
        else:
            skip_reasons.append("Missing '{}' attribute.".format(_protocol))


        if skip_reasons:
            _LOGGER.warn("> Not submitted: {}".format(skip_reasons))
            failures.append([skip_reasons, sample.sample_name])
            continue

        # Processing preconditions have been met.
        processed_samples.add(sample.sample_name)
        sample.to_yaml()

        # Go through all pipelines to submit for this protocol.
        for pipeline_interface, pipeline_job in pipelines:

            # Discard any arguments to get just the (complete) script name,
            # which is the key in the pipeline interface.
            pl_id = os.path.basename(str(pipeline_job).split(" ")[0])

            _LOGGER.debug("Setting pipeline attributes for job '{}' (ID: '{}')".
                          format(pipeline_job, pl_id))

            try:
                # add pipeline-specific attributes (read type and length, inputs, etc)
                sample.set_pipeline_attributes(pipeline_interface, pl_id)
                _LOGGER.info("> Building submission for Pipeline: '{}' "
                             "(input: {:.2f} Gb)".format(pipeline_job,
                                                         sample.input_file_size))
            except AttributeError:
                # TODO: inform about which missing attribute(s).
                fail_message = "Required attribute(s) missing to set for sample pipeline."
                _LOGGER.warn("> Not submitted: %s", fail_message)
                skip_reasons.append(fail_message)
                continue

            # Check for any required inputs before submitting
            try:
                # TODO: we don't need return value since implicitly permissive=False?
                sample.confirm_required_inputs()
            except IOError:
                # TODO: inform about which missing file(s).
                fail_message = "Required input file(s) not found."
                _LOGGER.warn("> Not submitted: %s", fail_message)
                skip_reasons.append(fail_message)
                continue

            # Identify the cluster resources we will require for this submission
            submit_settings = pipeline_interface.choose_resource_package(pl_id, sample.input_file_size)

            # Reset the partition if it was specified on the command-line
            if hasattr(prj.compute, "partition"):
                submit_settings["partition"] = prj.compute["partition"]

            # Pipeline name is the key used for flag checking
            pl_name = pipeline_interface.get_pipeline_name(pl_id)

            # Build basic command line string
            cmd = pipeline_job

            # Append arguments for this pipeline
            # Sample-level arguments are handled by the pipeline interface.
            try: 
                argstring = pipeline_interface.get_arg_string(pl_id, sample)
                argstring += " "
            except AttributeError:
                # TODO: inform about which missing attribute(s).
                fail_message = "Required attribute(s) missing for pipeline arguments string."
                _LOGGER.warn("> Not submitted: %s", fail_message)
                skip_reasons.append(fail_message)
                continue
                
            # Project-level arguments (sample-agnostic) are handled separately.
            argstring += prj.get_arg_string(pl_id)
            cmd += argstring

            if pipeline_interface.uses_looper_args(pl_id):
                # These are looper_args, -C, -O, -M, and -P. If the pipeline 
                # implements these arguments, then it lists looper_args=True, 
                # and we add the arguments to the command string.

                if hasattr(prj, "pipeline_config"):
                    # Index with 'pl_id' instead of 'pipeline' 
                    # because we don't care about parameters here.
                    if hasattr(prj.pipeline_config, pl_id):
                        # First priority: pipeline config specified in project config
                        pl_config_file = getattr(prj.pipeline_config, pl_id)
                        if pl_config_file:  # make sure it's not null (which it could be provided as null)
                            if not os.path.isfile(pl_config_file):
                                _LOGGER.error("Pipeline config file specified but not found: %s", str(pl_config_file))
                                raise IOError(pl_config_file)
                            _LOGGER.info("Found config file: %s", str(getattr(prj.pipeline_config, pl_id)))
                            # Append arg for config file if found
                            cmd += " -C " + pl_config_file

                cmd += " -O " + prj.metadata.results_subdir
                if submit_settings["cores"] > 1:
                    cmd += " -P " + submit_settings["cores"]
                if submit_settings["mem"] > 1:
                    cmd += " -M " + submit_settings["mem"]

            # Add the command string and job name to the submit_settings object
            submit_settings["JOBNAME"] = sample.sample_name + "_" + pl_id
            submit_settings["CODE"] = cmd

            # Submit job!
            job_count += 1
            submitted = cluster_submit(
                    sample, prj.compute.submission_template,
                    prj.compute.submission_command, submit_settings,
                    prj.metadata.submission_subdir, pipeline_outfolder, 
                    pl_name, args.time_delay, submit=True, 
                    dry_run=args.dry_run,  ignore_flags=args.ignore_flags, 
                    remaining_args=remaining_args)
            if submitted:
                submit_count += 1

        if skip_reasons:
            failures.append([skip_reasons, sample.sample_name])

    msg = "\nLooper finished. {} of {} job(s) submitted.".\
            format(submit_count, job_count)
    if args.dry_run:
        msg += " Dry run. No jobs were actually submitted."

    _LOGGER.info(msg)

    if failures:
        _LOGGER.info("Failure count: %d; Reasons for failure:",
                 len(failures))
        for skip_causes, sample in failures:
            _LOGGER.info("> {}: {}".format(sample, skip_causes))



def summarize(prj):
    """
    Grabs the report_results stats files from each sample,
    and collates them into a single matrix (as a csv file)
    """

    import csv
    columns = []
    stats = []

    _start_counter(len(prj.samples))

    for sample in prj.samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.library))
        pipeline_outfolder = os.path.join(prj.metadata.results_subdir, sample.sample_name)

        # Grab the basic info from the annotation sheet for this sample.
        # This will correspond to a row in the output.
        sample_stats = sample.get_sheet_dict()
        columns.extend(sample_stats.keys())
        # Version 0.3 standardized all stats into a single file
        stats_file = os.path.join(pipeline_outfolder, "stats.tsv")
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

    # all samples are parsed. Produce file.

    tsv_outfile_path = os.path.join(prj.metadata.output_dir, prj.name)
    if prj.subproject:
        tsv_outfile_path += '_' + prj.subproject
    tsv_outfile_path += '_stats_summary.tsv'

    tsv_outfile = open(tsv_outfile_path, 'w')

    tsv_writer = csv.DictWriter(tsv_outfile, fieldnames=uniqify(columns), delimiter='\t', extrasaction='ignore')
    tsv_writer.writeheader()

    for row in stats:
        tsv_writer.writerow(row)

    tsv_outfile.close()

    _LOGGER.info("Summary (n=" + str(len(stats)) + "): " + tsv_outfile_path)



def destroy(prj, args, preview_flag=True):
    """
    Completely removes all output files and folders produced by any pipelines.
    """

    _LOGGER.info("Results to destroy:")

    _start_counter(len(prj.samples))

    for sample in prj.samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.library))
        pipeline_outfolder = os.path.join(prj.metadata.results_subdir, sample.sample_name)
        if preview_flag:
            # Preview: Don't actually delete, just show files.
            _LOGGER.info(str(pipeline_outfolder))
        else:
            destroy_sample_results(pipeline_outfolder, args)

    if not preview_flag:
        _LOGGER.info("Destroy complete.")
        return 0

    if args.dry_run:
        _LOGGER.info("Dry run. No files destroyed.")
        return 0

    if not query_yes_no("Are you sure you want to permanently delete all pipeline results for this project?"):
        _LOGGER.info("Destroy action aborted by user.")
        return 1

    # Finally, run the true destroy:

    return destroy(prj, args, preview_flag=False)


def clean(prj, args, preview_flag=True):
    """
    Clean will remove all intermediate files, defined by pypiper clean scripts, in the project.
    """

    _LOGGER.info("Files to clean:")

    _start_counter(len(prj.samples))

    for sample in prj.samples:
        _LOGGER.info(_COUNTER.show(sample.sample_name, sample.library))
        pipeline_outfolder = os.path.join(prj.metadata.results_subdir,
                                          sample.sample_name)
        cleanup_files = glob.glob(os.path.join(pipeline_outfolder,
                                               "*_cleanup.sh"))
        if preview_flag:
            # Preview: Don't actually clean, just show what we're going to clean.
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



class LooperCounter(object):
    """
    Count samples as you loop through them, and create text for the
    subcommand logging status messages.
    """

    def __init__(self, total):
        """
        Initialize the counter by telling it how many jobs may be processed.

        :param int total: number of jobs to process
        """
        self.count = 0
        self.total = total

    def show(self, name, library):
        """
        Display sample counts status for a particular library type.
         
        The counts are running vs. total for the library within the Project, 
        and as a side-effect of the call, the running count is incremented.
        
        :param str name: name of the sample
        :param str library: name of the library
        :return str: message suitable for logging a status update
        """
        self.count += 1
        return Fore.CYAN + "## [{n} of {N}] {sample} ({library})".format(
                n=self.count, N=self.total, sample=name, library=library) + Style.RESET_ALL 

    def __str__(self):
        return "LooperCounter of size {}".format(self.total)


def _submission_status_text(curr, total, sample_name, sample_library):
    return Fore.BLUE + \
           "## [{n} of {N}] {sample} ({library})".format(
                n=curr, N=total, sample=sample_name, library=sample_library) + \
           Style.RESET_ALL



def cluster_submit(
    sample, submit_template, submission_command, variables_dict,
    submission_folder, pipeline_outfolder, pipeline_name, time_delay,
    submit=False, dry_run=False, ignore_flags=False, remaining_args=None):
    """
    Submit job to cluster manager.
    
    :param looper.models.Sample sample: the sample object for submission
    :param str submit_template: path to submission script template
    :param str submission_command: actual command with which to execute the 
        submission of the cluster job for the given sample
    :param variables_dict: key-value pairs to use to populate fields in 
        the submission template
    :param str submission_folder: path to the folder in which to place 
        submission files
    :param str pipeline_outfolder: path to folder into which the pipeline 
        will write file(s), and where to search for flag file to check 
        if a sample's already been submitted
    :param str pipeline_name: name of the pipeline that the job will run
    :param int time_delay: number of seconds by which to delay submission 
        of next job
    :param bool submit: whether to even attempt to actually submit the job; 
        this is useful for skipping certain samples within a project
    :param bool dry_run: whether the call is a test and thus the cluster job 
        created should not actually be submitted; in this case, the return 
        is a true proxy for whether the job would've been submitted
    :param bool ignore_flags: whether to ignore the presence of flag file(s) 
        in making the determination of whether to submit the job
    :param Iterable[str] remaining_args: arguments for this submission, 
        unconsumed by previous option/argument parsing
    :return bool: whether the submission was done, 
        or would've been if not a dry run
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

    with open(submit_template, 'r') as handle:
        filedata = handle.read()

    # Update variable dict with any additional arguments.
    variables_dict["CODE"] += " " + str(" ".join(remaining_args or []))
    # Fill in submit_template with variables.
    for key, value in variables_dict.items():
        # Here we add brackets around the key names and use uppercase because
        # this is how they are encoded as variables in the submit templates.
        filedata = filedata.replace("{" + str(key).upper() + "}", str(value))
    with open(submit_script, 'w') as handle:
        handle.write(filedata)

    # Prepare and write sample yaml object
    sample.to_yaml()

    # Check if job is already submitted (unless ignore_flags is set to True)
    if not ignore_flags:
        flag_files = glob.glob(os.path.join(
                pipeline_outfolder, pipeline_name + "*.flag"))
        if len(flag_files) > 0:
            flags = [os.path.basename(f) for f in flag_files]
            _LOGGER.info("> Not submitting, flag(s) found: {}".format(flags))
            submit = False
        else:
            pass

    if not submit:
        return False
    if dry_run:
        _LOGGER.info("> DRY RUN: I would have submitted this")
    else:
        subprocess.call(submission_command + " " + submit_script, shell=True)
        time.sleep(time_delay)    # Delay next job's submission.
    return True



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
    Checks flag status
    """
    # prefix
    pf = "ls " + prj.metadata.results_subdir + "/"
    cmd = os.path.join(pf + "*/*.flag | xargs -n1 basename | sort | uniq -c")
    _LOGGER.info(cmd)
    subprocess.call(cmd, shell=True)

    flags = ["completed", "running", "failed", "waiting"]

    counts = {}
    for f in flags:
        counts[f] = int(subprocess.check_output(pf + "*/*" + f + ".flag 2> /dev/null | wc -l", shell=True))

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

    
    _LOGGER.info("Command: " + args.command + " (Looper version: " + __version__ + ")")
    # Initialize project
    _LOGGER.debug("compute_env_file: " + getattr(args, 'env', None))
    prj = Project(
        args.config_file, args.subproject,
        file_checks=args.file_checks,
        compute_env_file=getattr(args, 'env', None))

    _LOGGER.info("Results subdir: " + prj.metadata.results_subdir)

    if args.command == "run":
        if args.compute:
            prj.set_compute(args.compute)

        # TODO split here, spawning separate run process for each pipelines directory in project metadata pipelines directory.
        try:
            pipedirs = prj.metadata.pipelines_dir
            _LOGGER.info("Pipelines path(s): {}".format(pipedirs))
        except AttributeError:
            _LOGGER.error("Looper requires a metadata.pipelines_dir")
            raise

        if len(pipedirs) == 0:
            _LOGGER.error("Looper requires a metadata.pipelines_dir")   
            raise AttributeError         

        interface_manager = InterfaceManager(prj.metadata.pipelines_dir)
        try:
            run(prj, args, remaining_args, interface_manager=interface_manager)
        except IOError:
            _LOGGER.error("{} pipelines_dir: '{}'".format(
                    prj.__class__.__name__, prj.metadata.pipelines_dir))
            raise

    if args.command == "destroy":
        return destroy(prj, args)

    if args.command == "summarize":
        summarize(prj)

    if args.command == "check":
        check(prj)

    if args.command == "clean":
        clean(prj, args)



if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _LOGGER.error("Program canceled by user!")
        sys.exit(1)
