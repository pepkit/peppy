import typer

from ._version import __version__
from .const import PKG_NAME
from .eido.cli import app as eido_app
from .pephubclient.cli import app as phc_app


def version_callback(value: bool):
    if value:
        typer.echo(f"{PKG_NAME} version: {__version__}")
        raise typer.Exit()


app = typer.Typer(help=f"{PKG_NAME} - Portable Encapsulated Projects toolkit")


@app.callback()
def common(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, help="package version"
    ),
):
    pass


app.add_typer(phc_app, name="phc", help="Client for the PEPhub server")
app.add_typer(eido_app, name="eido", help="PEP validation, conversion, and inspection")


def main():
    app(prog_name=PKG_NAME)
