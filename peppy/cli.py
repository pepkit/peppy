import argparse
import logging
import sys
from typing import Dict, List

import logmuse
from logmuse import init_logger
from ubiquerg import VersionInHelpParser

from ._version import __version__
from .const import PKG_NAME
from .eido.argparser import LEVEL_BY_VERBOSITY
from .eido.argparser import build_subparser as eido_subparser
from .eido.const import CONVERT_CMD, INSPECT_CMD, LOGGING_LEVEL, VALIDATE_CMD
from .eido.conversion import (
    convert_project,
    get_available_pep_filters,
    pep_conversion_plugins,
)
from .eido.exceptions import EidoFilterError, EidoValidationError
from .eido.inspection import inspect_project
from .eido.validation import validate_config, validate_project, validate_sample
from .project import Project


def _get_subparser(parser, *names):
    """
    Access nested subparsers by name.
    Example: _get_subparser(main_parser, "cmdA", "subA1")
    """
    current = parser
    for name in names:
        # find subparsers action
        subactions = [
            a for a in current._actions if isinstance(a, argparse._SubParsersAction)
        ]
        if not subactions:
            raise ValueError(f"{current} has no subparsers")

        action = subactions[0]
        if name not in action.choices:
            raise ValueError(f"Subparser '{name}' not found")

        current = action.choices[name]

    return current


def _parse_filter_args_str(input):
    """
    Parse user input specification.

    :param Iterable[Iterable[str]] input: user command line input,
        formatted as follows: [[arg=txt, arg1=txt]]
    :return dict: mapping of keys, which are input names and values
    """
    lst = []
    for i in input or []:
        lst.extend(i)
    return (
        {x.split("=")[0]: x.split("=")[1] for x in lst if "=" in x}
        if lst is not None
        else lst
    )


def print_error_summary(
    errors_by_type: Dict[str, List[Dict[str, str]]], _LOGGER: logging.Logger
):
    """Print a summary of errors, organized by error type"""
    n_error_types = len(errors_by_type)
    _LOGGER.error(f"Found {n_error_types} types of error:")
    for err_type, items in errors_by_type.items():
        n = len(items)
        msg = f"  - {err_type}: ({n} samples) "
        if n < 50:
            msg += ", ".join(x["sample_name"] for x in items)
        _LOGGER.error(msg)

    if len(errors_by_type) > 1:
        final_msg = f"Validation unsuccessful. {len(errors_by_type)} error types found."
    else:
        final_msg = f"Validation unsuccessful. {len(errors_by_type)} error type found."

    _LOGGER.error(final_msg)


def build_argparser():
    """
    Builds argument parser.

    :return argparse.ArgumentParser: Argument parser
    """

    banner = "%(prog)s - Portable Encapsulated Projects toolkit"
    # additional_description = "\nhttps://geniml.databio.org"

    parser = VersionInHelpParser(
        prog=PKG_NAME,
        version=f"{__version__}",
        description=banner,
    )

    # Individual subcommands
    msg_by_cmd = {
        "eido": "PEP validation, conversion, and inspection",
        # "pephubclient": "Client for the PEPhub server",
    }

    sp = parser.add_subparsers(dest="command")
    subparsers: Dict[str, VersionInHelpParser] = {}
    for k, v in msg_by_cmd.items():
        subparsers[k] = sp.add_parser(k, description=v, help=v)

    # build up subparsers for modules
    subparsers["eido"] = eido_subparser(subparsers["eido"])

    return parser


def main(test_args=None):
    """Primary workflow"""
    parser = logmuse.add_logging_options(build_argparser())
    args, _ = parser.parse_known_args()

    if test_args:
        args.__dict__.update(test_args)

    global _LOGGER
    _LOGGER = logmuse.logger_via_cli(args, make_root=True)

    if args.command is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.command == "eido":

        if args.subcommand == CONVERT_CMD:
            convert_sp = _get_subparser(parser, "eido", CONVERT_CMD)
            filters = get_available_pep_filters()
            if args.list:
                _LOGGER.info("Available filters:")
                if len(filters) < 1:
                    _LOGGER.info("No available filters")
                for filter_name in filters:
                    _LOGGER.info(f" - {filter_name}")
                sys.exit(0)
            if not "format" in args:
                _LOGGER.error("The following arguments are required: --format")
                convert_sp.print_help(sys.stderr)
                sys.exit(1)
            if args.describe:
                if args.format not in filters:
                    raise EidoFilterError(
                        f"'{args.format}' filter not found. Available filters: {', '.join(filters)}"
                    )
                filter_functions_by_name = pep_conversion_plugins()
                print(filter_functions_by_name[args.format].__doc__)
                sys.exit(0)
            if args.pep is None:
                # parser.print_help(sys.stderr)
                # sp[CONVERT_CMD].print_help(sys.stderr)
                convert_sp.print_help(sys.stderr)
                _LOGGER.info("The following arguments are required: PEP")
                sys.exit(1)
            if args.paths:
                paths = {y[0]: y[1] for y in [x.split("=") for x in args.paths]}
            else:
                paths = None

            p = Project(
                args.pep,
                sample_table_index=args.st_index,
                subsample_table_index=args.sst_index,
                amendments=args.amendments,
            )
            plugin_kwargs = _parse_filter_args_str(args.args)

            # append paths
            plugin_kwargs["paths"] = paths

            convert_project(p, args.format, plugin_kwargs)
            _LOGGER.info("Conversion successful")
            sys.exit(0)

        _LOGGER.debug(f"Creating a Project object from: {args.pep}")
        if args.subcommand == VALIDATE_CMD:
            p = Project(
                args.pep,
                sample_table_index=args.st_index,
                subsample_table_index=args.sst_index,
                amendments=args.amendments,
            )
            if args.sample_name:
                try:
                    args.sample_name = int(args.sample_name)
                except ValueError:
                    # If sample_name is not an integer, leave it as a string.
                    pass
                _LOGGER.debug(
                    f"Comparing Sample ('{args.pep}') in Project ('{args.pep}') "
                    f"against a schema: {args.schema}"
                )
                validator = validate_sample
                arguments = [p, args.sample_name, args.schema]
            elif args.just_config:
                _LOGGER.debug(
                    f"Comparing Project ('{args.pep}') against a schema: {args.schema}"
                )
                validator = validate_config
                arguments = [p, args.schema]
            else:
                _LOGGER.debug(
                    f"Comparing Project ('{args.pep}') against a schema: {args.schema}"
                )
                validator = validate_project
                arguments = [p, args.schema]
            try:
                validator(*arguments)
            except EidoValidationError as e:
                print_error_summary(e.errors_by_type, _LOGGER)
                sys.exit(1)
            _LOGGER.info("Validation successful")
            sys.exit(0)

        if args.subcommand == INSPECT_CMD:
            p = Project(
                args.pep,
                sample_table_index=args.st_index,
                subsample_table_index=args.sst_index,
                amendments=args.amendments,
            )
            inspect_project(p, args.sample_name, args.attr_limit)
            sys.exit(0)
