import typer

from .helpers import call_client_func
from .pephubclient import PEPHubClient

_client = PEPHubClient()

app = typer.Typer()


@app.command()
def login():
    """
    Login to PEPhub
    """
    call_client_func(_client.login)


@app.command()
def logout():
    """
    Logout
    """
    _client.logout()


@app.command()
def pull(
    project_registry_path: str,
    force: bool = typer.Option(False, help="Overwrite project if it exists."),
    zip: bool = typer.Option(False, help="Save project as zip file."),
    output: str = typer.Option(None, help="Output directory."),
):
    """
    Download and save project locally.
    """
    call_client_func(
        _client.pull,
        project_registry_path=project_registry_path,
        force=force,
        output=output,
        zip=zip,
    )


@app.command()
def push(
    cfg: str = typer.Argument(
        ...,
        help="Project config file (YAML) or sample table (CSV/TSV)"
        "with one row per sample to constitute project",
    ),
    namespace: str = typer.Option(..., help="Project namespace"),
    name: str = typer.Option(..., help="Project name"),
    tag: str = typer.Option(None, help="Project tag"),
    force: bool = typer.Option(
        False, help="Force push to the database. Use it to update, or upload project."
    ),
    is_private: bool = typer.Option(False, help="Upload project as private."),
):
    """
    Upload/update project in PEPhub
    """

    call_client_func(
        _client.push,
        cfg=cfg,
        namespace=namespace,
        name=name,
        tag=tag,
        is_private=is_private,
        force=force,
    )
