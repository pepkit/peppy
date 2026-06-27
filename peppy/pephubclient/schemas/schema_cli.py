import os

import typer

from ..helpers import (
    call_client_func,
    open_schema,
    save_schema,
    schema_path_converter,
)
from ..pephubclient import PEPHubClient

schemas_app = typer.Typer(
    pretty_exceptions_short=False,
    pretty_exceptions_show_locals=False,
    help="PEPhub CLI for schemas",
)

_client_schema = PEPHubClient().schema


@schemas_app.command(
    help="Download schema from PEPhub",
)
def get(
    schema_registry_path: str,
    output: str = typer.Option(None, help="Output directory."),
    format: str = typer.Option("json", help="Format in which file should be saved"),
):
    namespace, schema_name, version = schema_path_converter(schema_registry_path)

    schema_value = call_client_func(
        _client_schema.get,
        namespace=namespace,
        schema_name=schema_name,
        version=version,
    )
    if output is None:
        output = os.getcwd()

    new_name = os.path.join(output, f"{namespace}_{schema_name}_{version}.{format}")
    save_schema(new_name, schema_obj=schema_value, format=format)


@schemas_app.command(help="Create new schema in PEPhub")
def create(
    schema: str = typer.Option(
        ...,
        help="Path to schema file stored in json, or yaml format",
        readable=True,
    ),
    namespace: str = typer.Option(..., help="Schema namespace"),
    schema_name: str = typer.Option(..., help="Schema name"),
    version: str = typer.Option("1.0.0", help="Schema version"),
    description: str = typer.Option("", help="Schema description"),
    maintainers: str = typer.Option("", help="Schema maintainers"),
    contributors: str = typer.Option("", help="Schema contributors"),
    tags: list[str] = typer.Option(list(), help="Tags of the version"),
    release_notes: str = typer.Option("", help="Version release notes"),
    private: bool = typer.Option(False, help="Make schema private"),
    lifecycle_stage: str = typer.Option("", help="Lifecycle stage"),
):
    schema_value = open_schema(schema)

    call_client_func(
        _client_schema.create_schema,
        schema_name=schema_name,
        version=version,
        description=description,
        maintainers=maintainers,
        contributors=contributors,
        tags=tags,
        release_notes=release_notes,
        schema_value=schema_value,
        namespace=namespace,
        lifecycle_stage=lifecycle_stage,
        private=private,
    )


@schemas_app.command(help="Add new version of schema to PEPhub")
def add_version(
    schema: str = typer.Option(
        ...,
        help="Path to schema file stored in json, or yaml format",
        readable=True,
    ),
    namespace: str = typer.Option(..., help="Schema namespace"),
    schema_name: str = typer.Option(..., help="Schema name"),
    version: str = typer.Option("1.0.0", help="Schema version"),
    contributors: str = typer.Option("", help="Schema contributors"),
    tags: list[str] = typer.Option(list(), help="Tags of the version"),
    release_notes: str = typer.Option("", help="Version release notes"),
):
    schema_value = open_schema(schema)
    call_client_func(
        _client_schema.add_version,
        namespace=namespace,
        schema_name=schema_name,
        schema_value=schema_value,
        version=version,
        contributors=contributors,
        release_notes=release_notes,
        tags=tags,
    )


@schemas_app.command(
    help="Delete schema version",
)
def delete_version(
    namespace: str = typer.Option(..., help="Schema namespace"),
    schema_name: str = typer.Option(..., help="Schema name"),
    version: str = typer.Option(..., help="Schema version"),
):
    call_client_func(
        _client_schema.delete_version,
        namespace=namespace,
        schema_name=schema_name,
        version=version,
    )


@schemas_app.command(
    help="Remove schema record from PEPhub",
)
def remove(
    namespace: str = typer.Option(..., help="Schema namespace"),
    schema_name: str = typer.Option(..., help="Schema name"),
):
    call_client_func(
        _client_schema.delete_schema,
        namespace=namespace,
        schema_name=schema_name,
    )
