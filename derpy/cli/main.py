"""
Main CLI entry point for derpy container tool.
"""

import click
from datetime import datetime
from derpy import __version__, __author__


@click.group()
@click.version_option(version=__version__, prog_name="derpy")
def main():
    """
    Derpy - A zero-dependency container tool
    
    Build, manage, and distribute OCI-compliant container images
    without relying on existing container runtimes.
    """
    pass


@main.command()
def version():
    """Display version information."""
    release_date = "2024-01-01"  # This will be updated with actual release date
    click.echo(f"derpy version {__version__}")
    click.echo(f"Author: {__author__}")
    click.echo(f"Release Date: {release_date}")


if __name__ == "__main__":
    main()