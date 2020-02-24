import sys
from ubiquerg import VersionInHelpParser
import logmuse
from ._version import __version__
from .const2 import *
from logging import getLogger
from .project2 import Project2

_LOGGER = getLogger(PKG_NAME)


def build_argparser():
    banner = "%(prog)s - Interact with PEPs"
    additional_description = "\nhttp://peppy.databio.org/"

    parser = VersionInHelpParser(
            prog=PKG_NAME,
            description=banner,
            epilog=additional_description,
            version=__version__)

    subparsers = parser.add_subparsers(dest="command")

    sps = {}
    for cmd, desc in SUBPARSER_MSGS.items():
        sps[cmd] = subparsers.add_parser(cmd, description=desc, help=desc)
        sps[cmd].add_argument('-p', '--pep', required=True,
                              help="Path to a PEP configuration "
                                   "file in yaml format.")

    sps[VALIDATE_CMD].add_argument("-s", "--schema", required=True,
            help="Path to a PEP schema file in yaml format.")

    sps[VALIDATE_CMD].add_argument(
            "-e", "--exclude-case", default=False, action="store_true",
            help="Whether to exclude the validation case from an error. "
                 "Only the human readable message explaining the error will "
                 "be raised. Useful when validating large PEPs.")

    sps[INSPECT_CMD].add_argument(
        "-n", "--sample-name", required=False, nargs="+",
        help="Name of the samples to inspect.")

    group = sps[VALIDATE_CMD].add_mutually_exclusive_group()

    group.add_argument(
        "-n", "--sample-name", required=False,
        help="Name or index of the sample to validate. "
             "Only this sample will be validated.")

    group.add_argument(
        "-c", "--just-config", required=False, action="store_true",
        default=False, help="Whether samples should be excluded from the "
                            "validation.")
    return parser


def main():
    """ Primary workflow """
    parser = logmuse.add_logging_options(build_argparser())
    args, remaining_args = parser.parse_known_args()
    _LOGGER.debug("Creating a Project object from: {}".format(args.pep))
    p = Project2(args.pep)
    if args.command == VALIDATE_CMD:
        if args.sample_name:
            try:
                args.sample_name = int(args.sample_name)
            except ValueError:
                pass
            _LOGGER.debug("Comparing Sample ('{}') in the Project "
                          "('{}') against a schema: {}.".
                          format(args.sample_name, args.pep, args.schema))
            p.validate_sample(args.sample_name, args.schema, args.exclude_case)
        elif args.just_config:
            _LOGGER.debug("Comparing config ('{}') against a schema: {}.".
                          format(args.pep, args.schema))
            p.validate_config(args.schema, args.exclude_case)
        else:
            _LOGGER.debug("Comparing Project ('{}') against a schema: {}.".
                          format(args.pep, args.schema))
            p.validate_project(args.schema, args.exclude_case)
        _LOGGER.info("Validation successful")
    if args.command == INSPECT_CMD:
        # TODO: add more detailed Project info
        if args.sample_name:
            samples = p.get_samples(args.sample_name)
            for s in samples:
                print(s)
                print("\n")
            sys.exit(0)
        print(p)
