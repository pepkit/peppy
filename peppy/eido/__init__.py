"""eido: PEP schema validation, inspection and conversion.

Formerly the standalone ``eido`` package, now vendored into ``peppy`` and
available as ``peppy.eido``. This module re-exports the public API so that
``from peppy.eido import read_schema``` keep working.
"""

from .const import *
from .conversion import (
    convert_project,
    get_available_pep_filters,
    pep_conversion_plugins,
    run_filter,
    save_result,
)
from .exceptions import (
    EidoException,
    EidoFilterError,
    EidoSchemaInvalidError,
    EidoValidationError,
    PathAttrNotFoundError,
)
from .inspection import get_input_files_size, inspect_project
from .schema import preprocess_schema, read_schema
from .validation import (
    validate_config,
    validate_input_files,
    validate_original_samples,
    validate_project,
    validate_sample,
)

__all__ = [
    # inspection
    "inspect_project",
    "get_input_files_size",
    # schema
    "read_schema",
    "preprocess_schema",
    # validation
    "validate_project",
    "validate_sample",
    "validate_config",
    "validate_input_files",
    "validate_original_samples",
    # conversion
    "convert_project",
    "run_filter",
    "get_available_pep_filters",
    "pep_conversion_plugins",
    "save_result",
    # exceptions
    "EidoException",
    "PathAttrNotFoundError",
    "EidoSchemaInvalidError",
    "EidoFilterError",
    "EidoValidationError",
]
