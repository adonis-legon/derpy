"""Base image management for build isolation.

This module provides the BaseImageManager class for downloading base images
from OCI registries and extracting them for use in isolated builds.
"""

from pathlib import Path
from typing import Optional, Tuple
import tarfile
import gzip
import shutil
import os
from datetime import datetime

from derpy.build.models import ImageReference
from derpy.oci.models import Image, Manifest, ImageConfig, Layer, Descriptor
from derpy.oci.models import MEDIA_TYPE_IMAGE_CONFIG, MEDIA_TYPE_IMAGE_LAYER
from derpy.registry.client import RegistryClient
from derpy.storage.manager import ImageManager
from derpy.core.config import RegistryConfig
from derpy.core.exceptions import BaseImageError, RegistryAuthenticationError
from derpy.core.logging import get_logger
from derpy.core.auth import AuthManager


class BaseImageManager:
    """Manages base image retrieval and extraction for isolated builds.
    
    Handles downloading base images from registries, caching them locally,
    and extracting their layers into a usable filesystem.
    """
    
    def __init__(
        self,
        storage_manager: ImageManager,
        cache_dir: Optional[Path] = None,
        auth_manager: Optional[AuthManager] = None
    ):
        """Initialize BaseImageManager.
        
        Args:
            storage_manager: ImageManager for local storage operations
            cache_dir: Directory for caching base images (default: ~/.derpy/cache/base-images)
            auth_manager: AuthManager for registry credentials (default: creates new instance)
        """
        self.storage = storage_manager
        self.cache_dir = cache_dir or Path.home() / ".derpy" / "cache" / "base-images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("base_image")
        self.auth_manager = auth_manager or self._create_auth_manager()
    
    def _create_auth_manager(self) -> AuthManager:
        """Create AuthManager instance with appropriate auth file path.
        
        Handles sudo builds by using the SUDO_USER's home directory if available.
        
        Returns:
            AuthManager instance
        """
        import os
        
        # Check if running as root
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            # Running as root - check for SUDO_USER
            sudo_user = os.environ.get('SUDO_USER')
            if sudo_user:
                # Use SUDO_USER's home directory
                import pwd
                try:
                    user_info = pwd.getpwnam(sudo_user)
                    user_home = Path(user_info.pw_dir)
                    auth_file = user_home / ".derpy" / "auth.json"
                    self.logger.info(f"Using auth file from SUDO_USER ({sudo_user}): {auth_file}")
                    return AuthManager(auth_file=auth_file)
                except KeyError:
                    self.logger.warning(f"SUDO_USER '{sudo_user}' not found, using root's auth file")
        
        # Use default auth file (current user's home directory)
        return AuthManager()
    
    def resolve_image_reference(self, image_ref: str) -> Tuple[str, str, str]:
        """Parse image reference into registry, repository, and tag.
        
        This method parses an image reference string and returns its components,
        applying default values for registry (docker.io) and tag (latest) when
        not specified.
        
        Examples:
            "ubuntu:22.04" → ("docker.io", "library/ubuntu", "22.04")
            "ghcr.io/org/app:v1" → ("ghcr.io", "org/app", "v1")
            "nginx" → ("docker.io", "library/nginx", "latest")
            "localhost:5000/myapp:dev" → ("localhost:5000", "myapp", "dev")
        
        Args:
            image_ref: Image reference string to parse
            
        Returns:
            Tuple of (registry_url, repository, tag)
            
        Raises:
            BaseImageError: If the image reference format is invalid
        """
        try:
            # Parse using ImageReference model
            parsed = ImageReference.parse(image_ref)
            
            # Return components as tuple
            return (parsed.registry, parsed.repository, parsed.tag)
            
        except ValueError as e:
            raise BaseImageError(
                image_ref=image_ref,
                message=f"Invalid image reference format: {e}",
                cause=e
            )
    
    def pull_base_image(self, image_ref: str) -> Image:
        """Download base image from registry if not cached locally.
        
        This method checks if the image exists in local storage first. If not,
        it downloads the image from the registry, stores it locally, and returns
        the Image object.
        
        Steps:
        1. Parse image reference
        2. Check if image exists in local storage
        3. If not, resolve registry and authenticate
        4. Download manifest
        5. Download config blob
        6. Download all layer blobs
        7. Store in local OCI layout
        8. Return Image object
        
        Args:
            image_ref: Image reference (e.g., "ubuntu:22.04")
            
        Returns:
            Image object with manifest, config, and layers
            
        Raises:
            BaseImageError: If download or storage fails
        """
        try:
            # Parse image reference
            registry_url, repository, tag = self.resolve_image_reference(image_ref)
            
            # Create a tag for local storage (include registry if not docker.io)
            if registry_url == "docker.io":
                # For Docker Hub, use simplified tag
                if repository.startswith("library/"):
                    local_tag = f"{repository.replace('library/', '', 1)}:{tag}"
                else:
                    local_tag = f"{repository}:{tag}"
            else:
                local_tag = f"{registry_url}/{repository}:{tag}"
            
            # Check if image exists in local storage (cache hit)
            self.logger.info(f"Checking cache for base image: {local_tag}")
            cached_image = self.storage.get_image(local_tag)
            if cached_image is not None:
                self.logger.info(f"Using cached base image: {local_tag}")
                return cached_image
            
            # Cache miss - download from registry
            self.logger.info(f"Pulling base image from registry: {image_ref}")
            
            # Determine registry URL for connection
            if registry_url == "docker.io":
                # Docker Hub uses registry-1.docker.io for API
                api_url = "https://registry-1.docker.io"
            elif "://" not in registry_url:
                # Add https:// if no scheme specified
                api_url = f"https://{registry_url}"
            else:
                api_url = registry_url
            
            # Check for stored credentials
            credentials = self.auth_manager.get_credentials(registry_url)
            
            # Create registry config with credentials if available
            if credentials:
                self.logger.info(f"Using authenticated pull for {registry_url}")
                registry_config = RegistryConfig(
                    url=api_url,
                    username=credentials.username,
                    password=credentials.decode_password(),
                    insecure=False
                )
            else:
                self.logger.info(f"Using anonymous pull for {registry_url}")
                registry_config = RegistryConfig(
                    url=api_url,
                    username=None,
                    password=None,
                    insecure=False
                )
            
            # Determine if token auth should be enabled (for Docker Hub)
            enable_token_auth = registry_url == "docker.io"
            
            # Create registry client and pull image
            try:
                with RegistryClient(registry_config, enable_token_auth=enable_token_auth) as client:
                    # Pull image components
                    manifest_bytes, config_bytes, layers_data = client.pull_image(
                        repository,
                        tag
                    )
            except RegistryAuthenticationError as auth_error:
                # Handle authentication errors specifically
                raise BaseImageError(
                    image_ref=image_ref,
                    message=(
                        f"Authentication failed for base image: {image_ref}\n"
                        f"Registry: {registry_url}\n"
                        f"\n"
                        f"To authenticate with this registry, run:\n"
                        f"  derpy login {registry_url}\n"
                        f"\n"
                        f"Error details: {auth_error.message}"
                    ),
                    cause=auth_error
                )
            except Exception as pull_error:
                # Provide clear error message for image not found
                error_msg = str(pull_error)
                if "404" in error_msg or "not found" in error_msg.lower():
                    raise BaseImageError(
                        image_ref=image_ref,
                        message=(
                            f"Base image not found in registry: {image_ref}\n"
                            f"Registry: {api_url}\n"
                            f"Repository: {repository}\n"
                            f"Tag: {tag}\n"
                            "Please verify the image name and tag are correct."
                        ),
                        cause=pull_error
                    )
                elif "401" in error_msg or "403" in error_msg or "unauthorized" in error_msg.lower():
                    # Authentication error not caught by RegistryAuthenticationError
                    raise BaseImageError(
                        image_ref=image_ref,
                        message=(
                            f"Authentication failed for base image: {image_ref}\n"
                            f"Registry: {registry_url}\n"
                            f"\n"
                            f"To authenticate with this registry, run:\n"
                            f"  derpy login {registry_url}\n"
                            f"\n"
                            f"Error details: {error_msg}"
                        ),
                        cause=pull_error
                    )
                elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    raise BaseImageError(
                        image_ref=image_ref,
                        message=(
                            f"Network error while pulling base image: {image_ref}\n"
                            f"Registry: {api_url}\n"
                            "Please check your network connection and try again."
                        ),
                        cause=pull_error
                    )
                else:
                    raise BaseImageError(
                        image_ref=image_ref,
                        message=(
                            f"Failed to pull base image from registry: {image_ref}\n"
                            f"Registry: {api_url}\n"
                            f"Error: {error_msg}"
                        ),
                        cause=pull_error
                    )
            
            # Parse manifest and config
            import json
            try:
                manifest_dict = json.loads(manifest_bytes.decode('utf-8'))
                manifest = Manifest.from_dict(manifest_dict)
                
                config_dict = json.loads(config_bytes.decode('utf-8'))
                config = ImageConfig.from_dict(config_dict)
            except (json.JSONDecodeError, KeyError, ValueError) as parse_error:
                raise BaseImageError(
                    image_ref=image_ref,
                    message=(
                        f"Failed to parse base image manifest or config: {image_ref}\n"
                        "The image may be corrupted or in an unsupported format."
                    ),
                    cause=parse_error
                )
            
            # Create Layer objects and save layer data to temp files
            layers = []
            for i, (layer_digest, layer_bytes) in enumerate(layers_data):
                try:
                    # Save layer to temp file
                    layer_path = self.cache_dir / f"{layer_digest.replace('sha256:', '')}.tar.gz"
                    layer_path.write_bytes(layer_bytes)
                    
                    # Get diff_id from config
                    diff_id = None
                    if i < len(config.rootfs.diff_ids):
                        diff_id = config.rootfs.diff_ids[i]
                    
                    # Get layer descriptor from manifest
                    layer_desc = manifest.layers[i]
                    
                    layer = Layer(
                        digest=layer_digest,
                        size=layer_desc.size,
                        media_type=layer_desc.media_type,
                        content_path=layer_path,
                        diff_id=diff_id
                    )
                    layers.append(layer)
                except (OSError, IOError) as layer_error:
                    raise BaseImageError(
                        image_ref=image_ref,
                        message=(
                            f"Failed to save layer {i+1}/{len(layers_data)} for base image: {image_ref}\n"
                            f"Layer digest: {layer_digest[:19]}...\n"
                            f"Cache directory: {self.cache_dir}\n"
                            "Check disk space and permissions."
                        ),
                        cause=layer_error
                    )
            
            # Create Image object
            image = Image(
                manifest=manifest,
                config=config,
                layers=layers
            )
            
            # Store in local OCI layout for caching
            try:
                self.logger.info(f"Caching base image: {local_tag}")
                self.storage.store_image(image, local_tag)
            except Exception as storage_error:
                # Log warning but don't fail - image is already downloaded
                self.logger.warning(
                    f"Failed to cache base image {local_tag}: {storage_error}. "
                    "Image will be re-downloaded on next build."
                )
            
            self.logger.info(f"Successfully pulled base image: {local_tag}")
            return image
            
        except BaseImageError:
            raise
        except Exception as e:
            raise BaseImageError(
                image_ref=image_ref,
                message=f"Unexpected error while pulling base image: {e}",
                cause=e
            )
    
    def extract_base_image(self, image: Image, target_dir: Path) -> Path:
        """Extract base image layers into a merged rootfs.
        
        This method extracts all layers from a base image in order and merges
        them into a single root filesystem directory, handling OCI whiteout
        files appropriately.
        
        Steps:
        1. Create target directory
        2. For each layer in order:
           a. Extract tar.gz to temp location
           b. Apply to target_dir (overlay behavior)
           c. Handle whiteout files (.wh.* markers)
        3. Return path to merged rootfs
        
        Args:
            image: Image object to extract
            target_dir: Directory to extract layers into
            
        Returns:
            Path to extracted rootfs directory
            
        Raises:
            BaseImageError: If extraction fails
        """
        temp_layer_dir = None
        try:
            # Create target directory
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as dir_error:
                raise BaseImageError(
                    image_ref="<unknown>",
                    message=(
                        f"Failed to create target directory for base image extraction: {target_dir}\n"
                        "Check disk space and permissions."
                    ),
                    cause=dir_error
                )
            
            self.logger.info(f"Extracting {len(image.layers)} layers to {target_dir}")
            
            # Extract each layer in order
            for i, layer in enumerate(image.layers):
                self.logger.debug(f"Extracting layer {i+1}/{len(image.layers)}: {layer.digest[:16]}...")
                
                # Validate layer content exists
                if not layer.content_path or not layer.content_path.exists():
                    raise BaseImageError(
                        image_ref="<unknown>",
                        message=(
                            f"Layer {i+1}/{len(image.layers)} content file not found\n"
                            f"Layer digest: {layer.digest}\n"
                            f"Expected path: {layer.content_path}\n"
                            "The base image may be corrupted. Try clearing the cache and re-pulling."
                        )
                    )
                
                # Create temp directory for this layer
                temp_layer_dir = self.cache_dir / f"extract_{layer.digest.replace('sha256:', '')}"
                try:
                    temp_layer_dir.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError) as temp_error:
                    raise BaseImageError(
                        image_ref="<unknown>",
                        message=(
                            f"Failed to create temporary directory for layer {i+1}/{len(image.layers)}\n"
                            f"Temp directory: {temp_layer_dir}\n"
                            "Check disk space and permissions."
                        ),
                        cause=temp_error
                    )
                
                try:
                    # Extract tar.gz layer
                    try:
                        with tarfile.open(layer.content_path, 'r:gz') as tar:
                            # Extract all members
                            # For Python 3.12+, we need to handle the filter parameter
                            # Container layers may contain absolute symlinks which are rejected by 'data' filter
                            # We use 'tar' filter which is less restrictive but still safe for our use case
                            import sys
                            if sys.version_info >= (3, 12):
                                # Python 3.12+ - use 'tar' filter to allow absolute symlinks
                                tar.extractall(path=temp_layer_dir, filter='tar')
                            else:
                                # Python < 3.12 - no filter parameter needed
                                tar.extractall(path=temp_layer_dir)
                    except tarfile.TarError as tar_error:
                        raise BaseImageError(
                            image_ref="<unknown>",
                            message=(
                                f"Failed to extract layer {i+1}/{len(image.layers)} tar.gz archive\n"
                                f"Layer digest: {layer.digest}\n"
                                f"Layer file: {layer.content_path}\n"
                                "The layer file may be corrupted. Try clearing the cache and re-pulling."
                            ),
                            cause=tar_error
                        )
                    except (OSError, IOError) as extract_error:
                        raise BaseImageError(
                            image_ref="<unknown>",
                            message=(
                                f"I/O error while extracting layer {i+1}/{len(image.layers)}\n"
                                f"Layer digest: {layer.digest}\n"
                                f"Target directory: {temp_layer_dir}\n"
                                "Check disk space and permissions."
                            ),
                            cause=extract_error
                        )
                    
                    # Process whiteout files first
                    try:
                        self._process_whiteouts(target_dir, temp_layer_dir)
                    except Exception as whiteout_error:
                        raise BaseImageError(
                            image_ref="<unknown>",
                            message=(
                                f"Failed to process whiteout files in layer {i+1}/{len(image.layers)}\n"
                                f"Layer digest: {layer.digest}\n"
                                f"Error: {whiteout_error}"
                            ),
                            cause=whiteout_error
                        )
                    
                    # Copy layer contents to target (overlay behavior)
                    try:
                        self._merge_layer(temp_layer_dir, target_dir)
                    except Exception as merge_error:
                        raise BaseImageError(
                            image_ref="<unknown>",
                            message=(
                                f"Failed to merge layer {i+1}/{len(image.layers)} into rootfs\n"
                                f"Layer digest: {layer.digest}\n"
                                f"Target directory: {target_dir}\n"
                                "Check disk space and permissions."
                            ),
                            cause=merge_error
                        )
                    
                finally:
                    # Clean up temp layer directory
                    if temp_layer_dir and temp_layer_dir.exists():
                        try:
                            shutil.rmtree(temp_layer_dir, ignore_errors=False)
                        except Exception as cleanup_error:
                            # Log warning but don't fail
                            self.logger.warning(
                                f"Failed to clean up temp layer directory {temp_layer_dir}: {cleanup_error}"
                            )
                            # Try with ignore_errors=True as fallback
                            shutil.rmtree(temp_layer_dir, ignore_errors=True)
            
            self.logger.info(f"Successfully extracted base image to {target_dir}")
            return target_dir
            
        except BaseImageError:
            raise
        except Exception as e:
            raise BaseImageError(
                image_ref="<unknown>",
                message=f"Unexpected error during base image extraction: {e}",
                cause=e
            )
    
    def _process_whiteouts(self, rootfs: Path, layer_dir: Path) -> None:
        """Process OCI whiteout files in a layer.
        
        Handles two types of whiteout markers:
        1. .wh.filename - Delete the file "filename" from rootfs
        2. .wh..wh..opq - Opaque directory marker, delete all contents
        
        Args:
            rootfs: Root filesystem where files should be deleted
            layer_dir: Layer directory containing whiteout markers
        """
        # Walk through layer directory looking for whiteout files
        for dirpath, dirnames, filenames in os.walk(layer_dir):
            dirpath = Path(dirpath)
            rel_dir = dirpath.relative_to(layer_dir)
            
            for filename in filenames:
                # Check for whiteout files
                if filename.startswith('.wh.'):
                    whiteout_path = dirpath / filename
                    
                    # Opaque whiteout - delete entire directory contents
                    if filename == '.wh..wh..opq':
                        target_dir = rootfs / rel_dir
                        if target_dir.exists() and target_dir.is_dir():
                            self.logger.debug(f"Opaque whiteout: clearing {target_dir}")
                            # Remove all contents but keep the directory
                            for item in target_dir.iterdir():
                                if item.is_dir():
                                    shutil.rmtree(item, ignore_errors=True)
                                else:
                                    item.unlink(missing_ok=True)
                        # Remove the whiteout marker itself
                        whiteout_path.unlink(missing_ok=True)
                    
                    # Regular whiteout - delete specific file
                    else:
                        # Extract the actual filename (remove .wh. prefix)
                        actual_filename = filename[4:]  # Remove '.wh.' prefix
                        target_file = rootfs / rel_dir / actual_filename
                        
                        if target_file.exists():
                            self.logger.debug(f"Whiteout: deleting {target_file}")
                            if target_file.is_dir():
                                shutil.rmtree(target_file, ignore_errors=True)
                            else:
                                target_file.unlink(missing_ok=True)
                        
                        # Remove the whiteout marker itself
                        whiteout_path.unlink(missing_ok=True)
    
    def _merge_layer(self, layer_dir: Path, target_dir: Path) -> None:
        """Merge a layer directory into the target rootfs.
        
        Copies all files from layer_dir to target_dir, overwriting existing files
        (overlay behavior). Properly handles symlinks and skips special directories.
        
        Args:
            layer_dir: Source layer directory
            target_dir: Target rootfs directory
        """
        # Special directories to skip (virtual filesystems that shouldn't be copied)
        skip_dirs = {'proc', 'sys', 'dev'}
        
        # Walk through layer directory and copy all files
        for dirpath, dirnames, filenames in os.walk(layer_dir):
            dirpath = Path(dirpath)
            rel_dir = dirpath.relative_to(layer_dir)
            
            # Skip special virtual filesystem directories at root level
            if rel_dir == Path('.'):
                # Remove skip_dirs from dirnames to prevent walking into them
                dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            
            target_subdir = target_dir / rel_dir
            
            # Create directory in target if it doesn't exist (unless it's a symlink)
            if not target_subdir.exists():
                target_subdir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files
            for filename in filenames:
                src_file = dirpath / filename
                dst_file = target_subdir / filename
                
                # Skip if source file doesn't exist (can happen with broken symlinks)
                try:
                    src_file.lstat()  # Use lstat to check without following symlinks
                except (FileNotFoundError, OSError):
                    self.logger.debug(f"Skipping non-existent file: {src_file}")
                    continue
                
                # Handle symlinks specially
                if src_file.is_symlink():
                    try:
                        link_target = src_file.readlink()
                        # Remove existing file/symlink if present
                        if dst_file.exists() or dst_file.is_symlink():
                            if dst_file.is_dir() and not dst_file.is_symlink():
                                shutil.rmtree(dst_file)
                            else:
                                dst_file.unlink()
                        # Create symlink
                        dst_file.symlink_to(link_target)
                    except (OSError, FileNotFoundError) as e:
                        self.logger.debug(f"Failed to copy symlink {src_file}: {e}")
                        continue
                else:
                    # Regular file - copy with metadata
                    try:
                        # Remove existing if it's a symlink or directory
                        if dst_file.exists() or dst_file.is_symlink():
                            if dst_file.is_dir() and not dst_file.is_symlink():
                                shutil.rmtree(dst_file)
                            elif dst_file.is_symlink():
                                dst_file.unlink()
                        shutil.copy2(src_file, dst_file)
                    except (OSError, FileNotFoundError) as e:
                        self.logger.debug(f"Failed to copy file {src_file}: {e}")
                        continue
            
            # Handle directory symlinks
            for dirname in dirnames:
                src_dir = dirpath / dirname
                dst_dir = target_subdir / dirname
                
                # Skip if source doesn't exist
                try:
                    src_dir.lstat()
                except (FileNotFoundError, OSError):
                    self.logger.debug(f"Skipping non-existent directory: {src_dir}")
                    continue
                
                # If source is a symlink, recreate it in target
                if src_dir.is_symlink():
                    try:
                        link_target = src_dir.readlink()
                        # Remove existing if present
                        if dst_dir.exists() or dst_dir.is_symlink():
                            if dst_dir.is_dir() and not dst_dir.is_symlink():
                                shutil.rmtree(dst_dir)
                            else:
                                dst_dir.unlink()
                        # Create symlink
                        dst_dir.symlink_to(link_target)
                    except (OSError, FileNotFoundError) as e:
                        self.logger.debug(f"Failed to copy directory symlink {src_dir}: {e}")
                        continue
