import sys
from logging import CRITICAL, DEBUG, ERROR, INFO, WARN, Logger
from typing import Dict, List, Optional

import typer
from logmuse import init_logger

from ..const import PKG_NAME, SAMPLE_NAME_ATTR
from ..project import Project
from .const import CONVERT_CMD, INSPECT_CMD, LOGGING_LEVEL, SUBPARSER_MSGS, VALIDATE_CMD
from .conversion import (
    convert_project,
    get_available_pep_filters,
    pep_conversion_plugins,
)
from .exceptions import EidoFilterError, EidoValidationError
from .inspection import inspect_project
from .validation import validate_config, validate_project, validate_sample

LEVEL_BY_VERBOSITY = [ERROR, CRITICAL, WARN, INFO, DEBUG]

app = typer.Typer()


def _configure_logging(
    verbosity: Optional[int],
    logging_level: Optional[str],
    dbg: bool,
) -> str:
    """Mimic old verbosity / logging-level behavior."""
    if dbg:
        level = logging_level or DEBUG
    elif verbosity is not None:
        # Verbosity-framed specification trumps logging_level.
        level = LEVEL_BY_VERBOSITY[verbosity]
    else:
        level = LOGGING_LEVEL
    return level


def _parse_filter_args_str(input: Optional[List[str]]) -> Dict[str, str]:
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
    errors_by_type: Dict[str, List[Dict[str, str]]], _LOGGER: Logger
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


@app.callback()
def common(
    ctx: typer.Context,
    verbosity: Optional[int] = typer.Option(
        None,
        "--verbosity",
        min=0,
        max=len(LEVEL_BY_VERBOSITY) - 1,
        help=f"Choose level of verbosity (default: {None})",
    ),
    logging_level: Optional[str] = typer.Option(
        None,
        "--logging-level",
        help="logging level",
    ),
    dbg: bool = typer.Option(
        False,
        "--dbg",
        help=f"Turn on debug mode (default: {False})",
    ),
):
    ctx.obj = {
        "verbosity": verbosity,
        "logging_level": logging_level,
        "dbg": dbg,
    }

    logger_level = _configure_logging(verbosity, logging_level, dbg)
    logger_kwargs = {"level": logger_level, "devmode": dbg}

    global _LOGGER
    _LOGGER = init_logger(name=PKG_NAME, **logger_kwargs)


@app.command(name=CONVERT_CMD, help=SUBPARSER_MSGS[CONVERT_CMD])
def convert(
    ctx: typer.Context,
    pep: Optional[str] = typer.Argument(
        None,
        metavar="PEP",
        help="Path to a PEP configuration file in yaml format.",
    ),
    st_index: Optional[str] = typer.Option(
        None, "--st-index", help="Sample table index to use"
    ),
    sst_index: Optional[str] = typer.Option(
        None, "--sst-index", help="Subsample table index to use"
    ),
    amendments: Optional[List[str]] = typer.Option(
        None,
        "--amendments",
        help="Names of the amendments to activate.",
    ),
    format_: str = typer.Option(
        "yaml",
        "-f",
        "--format",
        help="Output format (name of filter; use -l to see available).",
    ),
    sample_name: Optional[List[str]] = typer.Option(
        None,
        "-n",
        "--sample-name",
        help="Name of the samples to inspect.",
    ),
    args: Optional[List[str]] = typer.Option(
        None,
        "-a",
        "--args",
        help=(
            "Provide arguments to the filter function " "(e.g. arg1=val1 arg2=val2)."
        ),
    ),
    list_filters: bool = typer.Option(
        False,
        "-l",
        "--list",
        help="List available filters.",
    ),
    describe: bool = typer.Option(
        False,
        "-d",
        "--describe",
        help="Show description for a given filter.",
    ),
    paths_: Optional[List[str]] = typer.Option(
        None,
        "-p",
        "--paths",
        help="Paths to dump conversion result as key=value pairs.",
    ),
):
    filters = get_available_pep_filters()
    if list_filters:
        _LOGGER.info("Available filters:")
        if len(filters) < 1:
            _LOGGER.info("No available filters")
        for filter_name in filters:
            _LOGGER.info(f" - {filter_name}")
        sys.exit(0)
    if describe:
        if format_ not in filters:
            raise EidoFilterError(
                f"'{format_}' filter not found. Available filters: {', '.join(filters)}"
            )
        filter_functions_by_name = pep_conversion_plugins()
        print(filter_functions_by_name[format_].__doc__)
        sys.exit(0)
    if pep is None:
        typer.echo(ctx.get_help(), err=True)
        _LOGGER.info("The following arguments are required: PEP")
        sys.exit(1)

    if paths_:
        paths = {y[0]: y[1] for y in [x.split("=") for x in paths_]}
    else:
        paths = None

    p = Project(
        pep,
        sample_table_index=st_index,
        subsample_table_index=sst_index,
        amendments=amendments,
    )

    plugin_kwargs = _parse_filter_args_str(args)

    # append paths
    plugin_kwargs["paths"] = paths

    convert_project(p, format_, plugin_kwargs)
    _LOGGER.info("Conversion successful")
    sys.exit(0)


@app.command(name=VALIDATE_CMD, help=SUBPARSER_MSGS[VALIDATE_CMD])
def validate(
    pep: str = typer.Argument(
        None,
        metavar="PEP",
        help="Path to a PEP configuration file in yaml format.",
    ),
    schema: str = typer.Option(
        None,
        "-s",
        "--schema",
        metavar="S",
        help="Path to a PEP schema file in yaml format.",
    ),
    st_index: Optional[str] = typer.Option(
        None,
        "--st-index",
        help=(
            f"Sample table index to use; samples are identified by "
            f"'{SAMPLE_NAME_ATTR}' by default."
        ),
    ),
    sst_index: Optional[str] = typer.Option(
        None,
        "--sst-index",
        help=(
            f"Subsample table index to use; samples are identified by "
            f"'{SAMPLE_NAME_ATTR}' by default."
        ),
    ),
    amendments: Optional[List[str]] = typer.Option(
        None,
        "--amendments",
        help="Names of the amendments to activate.",
    ),
    sample_name: Optional[str] = typer.Option(
        None,
        "-n",
        "--sample-name",
        metavar="S",
        help=(
            "Name or index of the sample to validate. "
            "Only this sample will be validated."
        ),
    ),
    just_config: bool = typer.Option(
        False,
        "-c",
        "--just-config",
        help="Whether samples should be excluded from the validation.",
    ),
):
    if sample_name and just_config:
        raise typer.BadParameter(
            "Use only one of --sample-name or --just-config for 'validate'."
        )
    p = Project(
        pep,
        sample_table_index=st_index,
        subsample_table_index=sst_index,
        amendments=amendments,
    )
    if sample_name:
        try:
            sample_name = int(sample_name)
        except ValueError:
            pass
        _LOGGER.debug(
            f"Comparing Sample ('{pep}') in Project ('{pep}') "
            f"against a schema: {schema}"
        )
        validator = validate_sample
        arguments = [p, sample_name, schema]
    elif just_config:
        _LOGGER.debug(f"Comparing Project ('{pep}') against a schema: {schema}")

        validator = validate_config
        arguments = [p, schema]
    else:
        _LOGGER.debug(f"Comparing Project ('{pep}') against a schema: {schema}")

        validator = validate_project
        arguments = [p, schema]
    try:
        validator(*arguments)
    except EidoValidationError as e:
        print_error_summary(e.errors_by_type, _LOGGER)
        sys.exit(1)
    _LOGGER.info("Validation successful")
    sys.exit(0)


@app.command(name=INSPECT_CMD, help=SUBPARSER_MSGS[INSPECT_CMD])
def inspect(
    pep: str = typer.Argument(
        None,
        metavar="PEP",
        help="Path to a PEP configuration file in yaml format.",
    ),
    st_index: Optional[str] = typer.Option(
        None,
        "--st-index",
        help=(
            f"Sample table index to use; samples are identified by "
            f"'{SAMPLE_NAME_ATTR}' by default."
        ),
    ),
    sst_index: Optional[str] = typer.Option(
        None,
        "--sst-index",
        help=(
            f"Subsample table index to use; samples are identified by "
            f"'{SAMPLE_NAME_ATTR}' by default."
        ),
    ),
    amendments: Optional[List[str]] = typer.Option(
        None,
        "--amendments",
        help="Names of the amendments to activate.",
    ),
    sample_name: Optional[List[str]] = typer.Option(
        None,
        "-n",
        "--sample-name",
        metavar="SN",
        help="Name of the samples to inspect.",
    ),
    attr_limit: int = typer.Option(
        10,
        "-l",
        "--attr-limit",
        help="Number of sample attributes to display.",
    ),
):
    p = Project(
        pep,
        sample_table_index=st_index,
        subsample_table_index=sst_index,
        amendments=amendments,
    )
    inspect_project(p, sample_name, attr_limit)
