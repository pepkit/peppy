from ..constants import PEPHUB_BASE_URL

PEPHUB_SCHEMA_BASE_URL = f"{PEPHUB_BASE_URL}api/v1/schemas/"

PEPHUB_SCHEMA_NEW_SCHEMA_URL = f"{PEPHUB_SCHEMA_BASE_URL}{{namespace}}/json"
PEPHUB_SCHEMA_NEW_VERSION_URL = (
    f"{PEPHUB_SCHEMA_BASE_URL}{{namespace}}/{{schema_name}}/versions/json"
)
PEPHUB_SCHEMA_RECORD_URL = f"{PEPHUB_SCHEMA_BASE_URL}{{namespace}}/{{schema_name}}"
PEPHUB_SCHEMA_VERSIONS_URL = (
    f"{PEPHUB_SCHEMA_BASE_URL}{{namespace}}/{{schema_name}}/versions"
)
PEPHUB_SCHEMA_VERSION_URL = (
    f"{PEPHUB_SCHEMA_BASE_URL}{{namespace}}/{{schema_name}}/versions/{{version}}"
)

LATEST_VERSION = "latest"
