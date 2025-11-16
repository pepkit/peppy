from logging import CRITICAL, DEBUG, ERROR, INFO, WARN

from ..const import PKG_NAME, SAMPLE_NAME_ATTR
from .const import CONVERT_CMD, INSPECT_CMD, SUBPARSER_MSGS, VALIDATE_CMD

LEVEL_BY_VERBOSITY = [ERROR, CRITICAL, WARN, INFO, DEBUG]


def build_subparser(parser):
    sp = parser.add_subparsers(dest="subcommand")
    subparsers = {}

    for k, v in SUBPARSER_MSGS.items():
        subparsers[k] = sp.add_parser(k, description=v, help=v)
        subparsers[k].add_argument(
            "--st-index",
            required=False,
            type=str,
            # default=SAMPLE_NAME_ATTR,
            help=f"Sample table index to use, samples are identified by '{SAMPLE_NAME_ATTR}' by default.",
        )
        subparsers[k].add_argument(
            "--sst-index",
            required=False,
            type=str,
            # default=SAMPLE_NAME_ATTR,
            help=f"Subsample table index to use, samples are identified by '{SAMPLE_NAME_ATTR}' by default.",
        )
        subparsers[k].add_argument(
            "--amendments",
            required=False,
            type=str,
            nargs="+",
            help=f"Names of the amendments to activate.",
        )

        if k != CONVERT_CMD:
            subparsers[k].add_argument(
                "pep",
                metavar="PEP",
                help="Path to a PEP configuration file in yaml format.",
                default=None,
            )
        else:
            subparsers[k].add_argument(
                "pep",
                metavar="PEP",
                nargs="?",
                help="Path to a PEP configuration file in yaml format.",
                default=None,
            )

    subparsers[VALIDATE_CMD].add_argument(
        "-s",
        "--schema",
        required=True,
        help="Path to a PEP schema file in yaml format.",
        metavar="S",
    )

    subparsers[INSPECT_CMD].add_argument(
        "-n",
        "--sample-name",
        required=False,
        nargs="+",
        help="Name of the samples to inspect.",
        metavar="SN",
    )

    subparsers[INSPECT_CMD].add_argument(
        "-l",
        "--attr-limit",
        required=False,
        type=int,
        default=10,
        help="Number of sample attributes to display.",
    )

    group = subparsers[VALIDATE_CMD].add_mutually_exclusive_group()

    group.add_argument(
        "-n",
        "--sample-name",
        required=False,
        help="Name or index of the sample to validate. "
        "Only this sample will be validated.",
        metavar="S",
    )

    group.add_argument(
        "-c",
        "--just-config",
        required=False,
        action="store_true",
        default=False,
        help="Whether samples should be excluded from the validation.",
    )

    subparsers[CONVERT_CMD].add_argument(
        "-f",
        "--format",
        required=False,
        default="yaml",
        help="Output format (name of filter; use -l to see available).",
    )

    subparsers[CONVERT_CMD].add_argument(
        "-n",
        "--sample-name",
        required=False,
        nargs="+",
        help="Name of the samples to inspect.",
    )

    subparsers[CONVERT_CMD].add_argument(
        "-a",
        "--args",
        nargs="+",
        action="append",
        required=False,
        default=None,
        help="Provide arguments to the filter function (e.g. arg1=val1 arg2=val2).",
    )

    subparsers[CONVERT_CMD].add_argument(
        "-l",
        "--list",
        required=False,
        default=False,
        action="store_true",
        help="List available filters.",
    )

    subparsers[CONVERT_CMD].add_argument(
        "-d",
        "--describe",
        required=False,
        default=False,
        action="store_true",
        help="Show description for a given filter.",
    )

    subparsers[CONVERT_CMD].add_argument(
        "-p",
        "--paths",
        nargs="+",
        help="Paths to dump conversion result as key=value pairs.",
    )

    return parser
