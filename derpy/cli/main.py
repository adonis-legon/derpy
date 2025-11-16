"""
Main CLI entry point for derpy container tool.
"""

import click
import getpass
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from derpy import __version__, __author__
from derpy.core.config import ConfigManager, ConfigError, RegistryConfig
from derpy.core.auth import AuthManager
from derpy.core.exceptions import AuthenticationError, InvalidCredentialsError
from derpy.cli.banner import get_banner
from derpy.build import BuildEngine, BuildContext, BuildError
from derpy.storage import ImageManager, StorageError
from derpy.registry import RegistryClient, RegistryError
from derpy.core.exceptions import RegistryAuthenticationError


def format_size(size_bytes: int) -> str:
    """Format size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "45.2MB", "1.3GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


class BannerGroup(click.Group):
    """Custom Click Group that displays banner in help."""
    
    def format_help(self, ctx, formatter):
        """Format help with ASCII banner."""
        click.echo(get_banner())
        super().format_help(ctx, formatter)


@click.group(cls=BannerGroup)
@click.version_option(
    version=__version__,
    prog_name="derpy",
    message=f"Version: %(version)s\nAuthor: {__author__}"
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose output (INFO level logging)'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug output (DEBUG level logging)'
)
@click.pass_context
def cli(ctx, verbose: bool, debug: bool):
    """
    Build, manage, and distribute OCI-compliant container images
    without relying on existing container runtimes.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Setup logging based on flags
    from derpy.core.logging import setup_logging
    setup_logging(verbose=verbose, debug=debug)
    
    # Initialize config manager
    ctx.obj['config_manager'] = ConfigManager()


@cli.command()
def version():
    """Display version information with author and date."""
    click.echo(f"Version: {__version__}")
    click.echo(f"Author: {__author__}")


@cli.group()
@click.pass_context
def config(ctx):
    """Manage derpy configuration settings."""
    pass


@config.command(name='show')
@click.option(
    '--key',
    help='Show specific configuration key (e.g., images_path, build_settings.compression)'
)
@click.pass_context
def config_show(ctx, key: Optional[str]):
    """Display current configuration settings."""
    try:
        config_manager = ctx.obj['config_manager']
        cfg = config_manager.get_config()
        
        if key:
            # Show specific key
            parts = key.split('.')
            value = cfg
            
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    click.echo(f"Error: Configuration key '{key}' not found", err=True)
                    ctx.exit(1)
            
            click.echo(f"{key}: {value}")
        else:
            # Show all configuration
            click.echo("Current Configuration:")
            click.echo(f"  Images Path: {cfg.images_path}")
            click.echo(f"\nBuild Settings:")
            click.echo(f"  Default Platform: {cfg.build_settings.default_platform}")
            click.echo(f"  Max Layers: {cfg.build_settings.max_layers}")
            click.echo(f"  Compression: {cfg.build_settings.compression}")
            click.echo(f"  Parallel Builds: {cfg.build_settings.parallel_builds}")
            click.echo(f"  Enable Isolation: {cfg.build_settings.enable_isolation}")
            click.echo(f"  Base Image Cache Dir: {cfg.build_settings.base_image_cache_dir}")
            click.echo(f"  Chroot Timeout: {cfg.build_settings.chroot_timeout}s")
            
            if cfg.registry_configs:
                click.echo(f"\nRegistry Configurations:")
                for name, reg_config in cfg.registry_configs.items():
                    click.echo(f"  {name}:")
                    click.echo(f"    URL: {reg_config.url}")
                    click.echo(f"    Username: {reg_config.username or '(not set)'}")
                    click.echo(f"    Insecure: {reg_config.insecure}")
            else:
                click.echo(f"\nRegistry Configurations: (none)")
                
    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@config.command(name='set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx, key: str, value: str):
    """
    Set a configuration value.
    
    Examples:
    
      derpy config set images_path /path/to/images
      
      derpy config set build_settings.compression gzip
      
      derpy config set build_settings.max_layers 100
      
      derpy config set build_settings.parallel_builds true
    """
    try:
        config_manager = ctx.obj['config_manager']
        cfg = config_manager.get_config()
        
        # Parse the key path
        parts = key.split('.')
        
        if parts[0] == 'images_path':
            # Update images path
            config_manager.update_images_path(Path(value))
            click.echo(f"Updated images_path to: {value}")
            
        elif parts[0] == 'build_settings' and len(parts) == 2:
            # Update build settings
            setting_key = parts[1]
            
            # Convert value to appropriate type
            if setting_key in ('max_layers', 'chroot_timeout'):
                try:
                    typed_value = int(value)
                except ValueError:
                    click.echo(f"Error: {setting_key} must be an integer", err=True)
                    ctx.exit(1)
            elif setting_key in ('parallel_builds', 'enable_isolation'):
                typed_value = value.lower() in ('true', 'yes', '1', 'on')
            elif setting_key in ('default_platform', 'compression', 'base_image_cache_dir'):
                typed_value = value
            else:
                click.echo(f"Error: Unknown build setting '{setting_key}'", err=True)
                ctx.exit(1)
            
            config_manager.update_build_settings(**{setting_key: typed_value})
            click.echo(f"Updated build_settings.{setting_key} to: {typed_value}")
            
        else:
            click.echo(f"Error: Configuration key '{key}' is not supported for modification", err=True)
            click.echo("Supported keys: images_path, build_settings.<setting>")
            ctx.exit(1)
            
    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument('context', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option(
    '-f', '--file',
    'dockerfile',
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default='Dockerfile',
    help='Path to Dockerfile (default: Dockerfile in context)'
)
@click.option(
    '-t', '--tag',
    required=True,
    help='Tag for the image (e.g., myapp:latest)'
)
@click.pass_context
def build(ctx, context: Path, dockerfile: Path, tag: str):
    """
    Build a container image from a Dockerfile.
    
    CONTEXT is the build context directory containing files for the build.
    
    Examples:
    
      derpy build . -t myapp:latest
      
      derpy build /path/to/app -f /path/to/Dockerfile -t myapp:v1.0
    """
    try:
        # Resolve paths
        context_path = context.resolve()
        
        # If dockerfile is absolute or exists as-is, use it directly
        # Otherwise, resolve it relative to context
        if dockerfile.is_absolute():
            dockerfile_path = dockerfile.resolve()
        elif dockerfile.exists():
            dockerfile_path = dockerfile.resolve()
        else:
            # Try relative to context
            dockerfile_path = (context_path / dockerfile).resolve()
        
        # Verify dockerfile exists
        if not dockerfile_path.exists():
            click.echo(f"Error: Dockerfile not found: {dockerfile_path}", err=True)
            ctx.exit(1)
        
        click.echo(f"Building image '{tag}'...")
        click.echo(f"  Context: {context_path}")
        click.echo(f"  Dockerfile: {dockerfile_path}")
        click.echo()
        
        # Create build context
        build_context = BuildContext(
            context_path=context_path,
            dockerfile_path=dockerfile_path
        )
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Create storage manager for base image caching
        storage_manager = ImageManager(config.images_path)
        
        # Build image
        click.echo("Parsing Dockerfile...")
        build_engine = BuildEngine(
            storage_manager=storage_manager,
            enable_isolation=config.build_settings.enable_isolation,
            base_image_cache_dir=Path(config.build_settings.base_image_cache_dir).expanduser(),
            chroot_timeout=config.build_settings.chroot_timeout
        )
        
        click.echo("Executing build instructions...")
        image = build_engine.build_image(build_context, tag)
        
        click.echo(f"Built image with {len(image.layers)} layer(s)")
        click.echo()
        
        # Store image in local repository
        click.echo("Storing image in local repository...")
        image_manager = ImageManager()
        image_manager.store_image(image, tag)
        
        click.echo()
        click.echo(f"✓ Successfully built and stored image: {tag}")
        
    except BuildError as e:
        click.echo(f"Build error: {e}", err=True)
        ctx.exit(1)
    except StorageError as e:
        click.echo(f"Storage error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@cli.command(name='ls')
@click.option(
    '--format',
    type=click.Choice(['table', 'json'], case_sensitive=False),
    default='table',
    help='Output format (default: table)'
)
@click.pass_context
def list_images(ctx, format: str):
    """
    List all local container images.
    
    Examples:
    
      derpy ls
      
      derpy ls --format json
    """
    try:
        image_manager = ImageManager()
        images = image_manager.list_local_images()
        
        if not images:
            click.echo("No images found in local repository.")
            click.echo()
            click.echo("Build an image with: derpy build <context> -t <tag>")
            return
        
        if format == 'json':
            # Output as JSON
            import json
            images_data = [
                {
                    'tag': img.tag,
                    'size': img.size,
                    'created': img.created,
                    'architecture': img.architecture,
                    'os': img.os
                }
                for img in images
            ]
            click.echo(json.dumps(images_data, indent=2))
        else:
            # Output as table
            click.echo()
            click.echo(f"{'TAG':<40} {'SIZE':<10} {'CREATED':<19} {'PLATFORM'}")
            click.echo("-" * 84)
            
            for img in images:
                click.echo(str(img))
            
            click.echo()
            click.echo(f"Total: {len(images)} image(s)")
            
    except StorageError as e:
        click.echo(f"Storage error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument('image')
@click.pass_context
def rm(ctx, image: str):
    """
    Remove a container image from local storage.
    
    IMAGE is the image tag to remove (e.g., myapp:latest).
    
    Examples:
    
      derpy rm myapp:latest
      
      derpy rm nginx:alpine
    """
    try:
        click.echo(f"Removing image '{image}'...")
        
        # Create ImageManager instance
        image_manager = ImageManager()
        
        # Calculate size before removal for reporting
        metadata = image_manager._get_image_metadata(image)
        freed_size = metadata.size if metadata else 0
        
        # Call remove_image(tag) and check return value
        removed = image_manager.remove_image(image)
        
        if removed:
            # Display success message with freed space on success
            click.echo(f"✓ Successfully removed image: {image}")
            if freed_size > 0:
                # Format size in human-readable format
                size_str = format_size(freed_size)
                click.echo(f"  Freed: {size_str}")
        else:
            # Display error message with suggestion to run `derpy ls` if not found
            click.echo(f"Error: Image '{image}' not found in local repository.", err=True)
            click.echo()
            click.echo("List available images with: derpy ls")
            ctx.exit(1)
            
    except StorageError as e:
        # Handle StorageError exceptions and display error messages
        click.echo(f"Storage error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option(
    '-f', '--force',
    is_flag=True,
    help='Skip confirmation prompt'
)
@click.pass_context
def purge(ctx, force: bool):
    """
    Remove all container images and cached data.
    
    This command removes all images from local storage and clears
    the base image cache. Use with caution as this operation cannot
    be undone.
    
    Examples:
    
      derpy purge
      
      derpy purge --force
    """
    try:
        # Create ImageManager instance
        image_manager = ImageManager()
        
        # Load configuration to get cache directory
        config_manager = ConfigManager()
        config = config_manager.get_config()
        cache_dir = Path(config.build_settings.base_image_cache_dir).expanduser()
        
        # Calculate storage size and cache size before removal
        storage_size = image_manager.calculate_storage_size()
        cache_size = image_manager.get_cache_size(cache_dir)
        total_size = storage_size + cache_size
        
        # Count images from metadata
        all_metadata = image_manager._load_metadata()
        image_count = len(all_metadata)
        
        # Check if there are no images
        if image_count == 0 and cache_size == 0:
            click.echo("No images found in local repository.")
            click.echo("Nothing to purge.")
            return
        
        # Display warning with size information unless --force is specified
        if not force:
            click.echo("WARNING: This will remove all images and cached data.")
            click.echo()
            click.echo(f"Images: {image_count}")
            click.echo(f"Storage: {format_size(storage_size)}")
            click.echo(f"Cache: {format_size(cache_size)}")
            click.echo(f"Total: {format_size(total_size)}")
            click.echo()
            
            # Prompt user for confirmation
            response = click.prompt("Are you sure you want to continue? [y/N]", type=str, default="N")
            
            # Handle user cancellation (exit with code 0)
            if response.lower() not in ('y', 'yes'):
                click.echo("Operation cancelled.")
                return
        
        # Call remove_all_images() if confirmed
        click.echo("Removing all images...")
        removed_count = image_manager.remove_all_images()
        
        # Clear base image cache directory using shutil.rmtree
        if cache_dir.exists():
            click.echo("Clearing base image cache...")
            shutil.rmtree(cache_dir)
            # Recreate the cache directory
            cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Display summary with images removed and space freed
        click.echo()
        click.echo("✓ Successfully purged all images")
        click.echo(f"  Images removed: {removed_count}")
        click.echo(f"  Space freed: {format_size(total_size)}")
        
    except StorageError as e:
        # Handle StorageError exceptions and display error messages
        click.echo(f"Storage error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument('registry', default='docker.io')
@click.option(
    '-u', '--username',
    help='Username for registry authentication'
)
@click.option(
    '-p', '--password',
    help='Password for registry authentication'
)
@click.option(
    '--password-stdin',
    is_flag=True,
    help='Read password from stdin'
)
@click.pass_context
def login(
    ctx,
    registry: str,
    username: Optional[str],
    password: Optional[str],
    password_stdin: bool
):
    """
    Login to a container registry.
    
    REGISTRY is the registry URL (default: docker.io for Docker Hub).
    
    Credentials are stored securely in ~/.derpy/auth.json with file
    permissions set to 0600 (owner read/write only).
    
    Examples:
    
      derpy login
      
      derpy login registry.example.com
      
      derpy login -u myuser -p mypass registry.example.com
      
      echo "mypass" | derpy login --password-stdin -u myuser registry.example.com
    """
    try:
        # Validate that password-stdin and password are not both specified
        if password_stdin and password:
            click.echo(
                "Error: Cannot use both --password and --password-stdin",
                err=True
            )
            ctx.exit(1)
        
        # Prompt for username if not provided
        if not username:
            username = click.prompt("Username", type=str)
        
        # Validate username is not empty
        if not username or not username.strip():
            click.echo("Error: Username cannot be empty", err=True)
            ctx.exit(1)
        
        username = username.strip()
        
        # Get password from stdin, option, or prompt
        if password_stdin:
            # Read password from stdin
            password = sys.stdin.read().strip()
            if not password:
                click.echo("Error: No password provided on stdin", err=True)
                ctx.exit(1)
        elif password is not None:
            # Password provided via option - validate it's not empty
            if not password or not password.strip():
                click.echo("Error: Password cannot be empty", err=True)
                ctx.exit(1)
            password = password.strip()
        else:
            # Prompt for password (hidden input)
            password = getpass.getpass("Password: ")
            # Validate password is not empty
            if not password or not password.strip():
                click.echo("Error: Password cannot be empty", err=True)
                ctx.exit(1)
            password = password.strip()
        
        # Create AuthManager instance
        auth_manager = AuthManager()
        
        # Normalize registry URL for display
        normalized_registry = auth_manager._normalize_registry(registry)
        
        click.echo(f"Logging in to {normalized_registry}...")
        
        # Attempt login with credential verification
        try:
            auth_manager.login(
                registry=registry,
                username=username,
                password=password,
                verify_auth=True
            )
            
            click.echo(f"✓ Login Succeeded")
            click.echo(f"  Registry: {normalized_registry}")
            click.echo(f"  Username: {username}")
            
        except InvalidCredentialsError as e:
            click.echo(f"Error: Authentication failed for {normalized_registry}", err=True)
            click.echo("Please check your username and password and try again.", err=True)
            ctx.exit(1)
        except AuthenticationError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo("Please check your credentials and try again.", err=True)
            ctx.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\nLogin cancelled.", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument('registry', default='docker.io')
@click.pass_context
def logout(ctx, registry: str):
    """
    Logout from a container registry.
    
    REGISTRY is the registry URL (default: docker.io for Docker Hub).
    
    Removes stored credentials from ~/.derpy/auth.json.
    
    Examples:
    
      derpy logout
      
      derpy logout registry.example.com
    """
    try:
        # Create AuthManager instance
        auth_manager = AuthManager()
        
        # Normalize registry URL for display
        normalized_registry = auth_manager._normalize_registry(registry)
        
        # Attempt logout
        removed = auth_manager.logout(registry)
        
        if removed:
            click.echo(f"✓ Logged out from {normalized_registry}")
            click.echo(f"  Credentials removed")
        else:
            click.echo(f"No credentials found for {normalized_registry}")
            click.echo(f"  Already logged out or never logged in")
            
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument('image')
@click.option(
    '--registry',
    help='Registry name from config or full registry URL (default: inferred from image tag)'
)
@click.option(
    '--username',
    help='Registry username (overrides stored credentials)'
)
@click.option(
    '--password',
    help='Registry password (overrides stored credentials)'
)
@click.option(
    '--insecure',
    is_flag=True,
    help='Allow insecure registry connections (skip TLS verification)'
)
@click.pass_context
def push(ctx, image: str, registry: Optional[str], username: Optional[str], 
         password: Optional[str], insecure: bool):
    """
    Push a container image to a remote registry.
    
    IMAGE is the local image tag to push (e.g., myapp:latest or registry.example.com/myapp:latest).
    
    The registry is determined from the image tag. If the image tag includes a registry
    (e.g., registry.example.com/myapp:latest), that registry will be used. Otherwise,
    Docker Hub (registry-1.docker.io) is used by default.
    
    Credentials are automatically loaded from ~/.derpy/auth.json if available.
    Use 'derpy login' to store credentials.
    
    Examples:
    
      derpy push myapp:latest
      
      derpy push registry.example.com/myapp:v1.0
      
      derpy push localhost:5000/myapp:latest --insecure
      
      derpy push myapp:latest --username myuser --password mypass
    """
    try:
        # Get configuration
        config_manager = ctx.obj['config_manager']
        config = config_manager.get_config()
        
        # Parse registry from image tag
        registry_url = None
        repository = image
        
        # Check if image tag includes a registry (contains '/' and first part has '.' or ':')
        if '/' in image:
            first_part = image.split('/')[0]
            if '.' in first_part or ':' in first_part:
                # Image tag includes registry
                registry_url = first_part
                repository = image[len(first_part) + 1:]  # Remove registry from repository
        
        # If no registry in image tag, check --registry option or use Docker Hub
        if not registry_url:
            if registry:
                registry_url = registry
            else:
                # Default to Docker Hub
                registry_url = 'docker.io'
        
        # Create AuthManager instance
        auth_manager = AuthManager()
        
        # Normalize registry URL
        normalized_registry = auth_manager._normalize_registry(registry_url)
        
        # Get credentials from AuthManager (unless overridden by options)
        credentials = None
        if not username or not password:
            credentials = auth_manager.get_credentials(registry_url)
        
        # Determine final username and password
        final_username = username if username else (credentials.username if credentials else None)
        final_password = password if password else (credentials.decode_password() if credentials else None)
        
        # Check if credentials are available
        if not final_username or not final_password:
            click.echo(
                f"Error: No credentials found for registry: {normalized_registry}",
                err=True
            )
            click.echo()
            click.echo(f"Please login to the registry first:")
            click.echo(f"  derpy login {registry_url}")
            click.echo()
            click.echo("Or provide credentials with --username and --password options.")
            ctx.exit(1)
        
        # Create registry configuration
        registry_config = RegistryConfig(
            url=f"https://{normalized_registry}" if not normalized_registry.startswith('http') else normalized_registry,
            username=final_username,
            password=final_password,
            insecure=insecure
        )
        
        # Determine local image tag (repository without registry prefix)
        local_tag = repository
        
        # Check if image exists locally using the local tag
        image_manager = ImageManager()
        if not image_manager.image_exists(local_tag):
            click.echo(f"Error: Image '{local_tag}' not found in local repository.", err=True)
            click.echo()
            click.echo("List available images with: derpy ls")
            ctx.exit(1)
        
        click.echo(f"Pushing image '{local_tag}' to {normalized_registry}/{repository}...")
        click.echo()
        
        # Create registry client
        with RegistryClient(registry_config) as client:
            # Check connectivity
            click.echo("Checking registry connectivity...")
            if not client.check_connectivity():
                click.echo(
                    f"Error: Cannot connect to registry at {normalized_registry}",
                    err=True
                )
                click.echo("Please verify the registry URL and network connectivity.")
                ctx.exit(1)
            
            # Verify authentication
            click.echo("Verifying authentication...")
            if not client.verify_authentication():
                click.echo(f"Error: Authentication failed for {normalized_registry}", err=True)
                click.echo()
                click.echo("Your credentials may be invalid or expired.")
                click.echo(f"Please login again:")
                click.echo(f"  derpy login {registry_url}")
                ctx.exit(1)
            
            # Prepare image data using local tag
            click.echo("Preparing image data...")
            manifest_bytes, config_bytes, layers_data = image_manager.prepare_image_for_push(local_tag)
            
            # Calculate total size
            total_size = len(manifest_bytes) + len(config_bytes) + sum(
                len(data) for _, data in layers_data
            )
            
            # Progress tracking
            last_progress = [0]
            
            def progress_callback(uploaded, total):
                # Update progress every 10%
                progress = int((uploaded / total) * 100)
                if progress >= last_progress[0] + 10 or uploaded == total:
                    last_progress[0] = progress
                    click.echo(f"  Uploading: {progress}% ({uploaded}/{total} bytes)")
            
            # Push image using the repository path (with registry)
            click.echo(f"Uploading image ({len(layers_data)} layer(s), {total_size} bytes total)...")
            result = client.push_image(
                repository,
                manifest_bytes,
                config_bytes,
                layers_data,
                progress_callback
            )
            
            click.echo()
            click.echo(f"✓ Successfully pushed image: {local_tag}")
            click.echo(f"  Registry: {normalized_registry}")
            click.echo(f"  Repository: {result['repository']}")
            click.echo(f"  Tag: {result['tag']}")
            click.echo(f"  Manifest Digest: {result['manifest_digest']}")
            
    except StorageError as e:
        click.echo(f"Storage error: {e}", err=True)
        ctx.exit(1)
    except RegistryAuthenticationError as e:
        # Get registry_url from locals if available
        reg_url = registry_url if 'registry_url' in locals() else 'REGISTRY'
        norm_reg = normalized_registry if 'normalized_registry' in locals() else reg_url
        
        click.echo(f"Authentication error for {norm_reg}: {e}", err=True)
        click.echo()
        click.echo("Your credentials may be invalid, expired, or insufficient for this operation.")
        click.echo()
        click.echo("Please check your credentials and try logging in again:")
        click.echo(f"  derpy login {reg_url}")
        ctx.exit(1)
    except RegistryError as e:
        click.echo(f"Registry error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        ctx.exit(1)


def main():
    """Entry point for the CLI application."""
    cli(obj={})


if __name__ == "__main__":
    main()