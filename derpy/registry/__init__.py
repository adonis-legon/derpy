"""Registry client for OCI distribution protocol.

This module provides the RegistryClient for pushing and pulling container
images to/from OCI-compliant registries.
"""

from derpy.registry.client import RegistryClient, RegistryError

__all__ = ['RegistryClient', 'RegistryError']
