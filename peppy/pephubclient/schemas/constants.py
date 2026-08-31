PEPHUB_SCHEMA_BASE_PATH = "api/v1/schemas/"

PEPHUB_SCHEMA_NEW_SCHEMA_PATH = f"{PEPHUB_SCHEMA_BASE_PATH}{{namespace}}/json"
PEPHUB_SCHEMA_NEW_VERSION_PATH = (
    f"{PEPHUB_SCHEMA_BASE_PATH}{{namespace}}/{{schema_name}}/versions/json"
)
PEPHUB_SCHEMA_RECORD_PATH = f"{PEPHUB_SCHEMA_BASE_PATH}{{namespace}}/{{schema_name}}"
PEPHUB_SCHEMA_VERSIONS_PATH = (
    f"{PEPHUB_SCHEMA_BASE_PATH}{{namespace}}/{{schema_name}}/versions"
)
PEPHUB_SCHEMA_VERSION_PATH = (
    f"{PEPHUB_SCHEMA_BASE_PATH}{{namespace}}/{{schema_name}}/versions/{{version}}"
)

LATEST_VERSION = "latest"
