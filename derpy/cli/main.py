"""
Main CLI entry point for derpy container tool.
"""

from derpy import __version__, __author__


def main():
    """
    Derpy - A zero-dependency container tool
    
    Build, manage, and distribute OCI-compliant container images
    without relying on existing container runtimes.
    """
    print(f"derpy version {__version__}")
    print(f"Author: {__author__}")



if __name__ == "__main__":
    main()