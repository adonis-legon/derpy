"""
Main CLI entry point for derpy container tool.
"""

import click
from datetime import datetime
from pathlib import Path
from typing import Optional

from derpy import __version__, __author__
from derpy.core.config import ConfigManager, ConfigError, RegistryConfig
from derpy.cli.banner import get_banner
from derpy.build import BuildEngine, BuildContext, BuildError
from derpy.storage import ImageManager, StorageError
from derpy.registry import RegistryClient, RegistryError


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
@click.pass_context
def cli(ctx):
    """
    Build, manage, and distribute OCI-compliant container images
    without relying on existing container runtimes.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
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
            if setting_key == 'max_layers':
                try:
                    typed_value = int(value)
                except ValueError:
                    click.echo(f"Error: max_layers must be an integer", err=True)
                    ctx.exit(1)
            elif setting_key == 'parallel_builds':
                typed_value = value.lower() in ('true', 'yes', '1', 'on')
            elif setting_key in ('default_platform', 'compression'):
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
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
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
        
        # If dockerfile is relative, resolve it relative to context
        if not dockerfile.is_absolute():
            dockerfile_path = (context_path / dockerfile).resolve()
        else:
            dockerfile_path = dockerfile.resolve()
        
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
        
        # Build image
        click.echo("Parsing Dockerfile...")
        build_engine = BuildEngine()
        
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
            click.echo(f"{'TAG':<40} {'SIZE':<10} {'CREATED':<25} {'PLATFORM'}")
            click.echo("-" * 90)
            
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
@click.option(
    '--registry',
    help='Registry name from config or full registry URL (default: uses default registry from config)'
)
@click.option(
    '--username',
    help='Registry username (overrides config)'
)
@click.option(
    '--password',
    help='Registry password (overrides config)'
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
    
    IMAGE is the local image tag to push (e.g., myapp:latest).
    
    The image will be pushed to the specified registry. If no registry is
    specified, the default registry from the configuration will be used.
    
    Examples:
    
      derpy push myapp:latest --registry docker.io --username myuser
      
      derpy push myapp:v1.0 --registry localhost:5000 --insecure
      
      derpy push myapp:latest --registry myregistry
    """
    try:
        # Get configuration
        config_manager = ctx.obj['config_manager']
        config = config_manager.get_config()
        
        # Determine registry configuration
        registry_config = None
        
        if registry:
            # Check if it's a named registry in config
            if registry in config.registry_configs:
                registry_config = config.registry_configs[registry]
                click.echo(f"Using registry configuration: {registry}")
            else:
                # Treat as a registry URL
                registry_config = RegistryConfig(
                    url=registry if registry.startswith('http') else f"https://{registry}",
                    username=username,
                    password=password,
                    insecure=insecure
                )
        else:
            # Use default registry if configured
            if 'default' in config.registry_configs:
                registry_config = config.registry_configs['default']
                click.echo("Using default registry from configuration")
            else:
                click.echo(
                    "Error: No registry specified and no default registry configured.",
                    err=True
                )
                click.echo()
                click.echo("Please specify a registry with --registry or configure a default registry:")
                click.echo("  derpy config set registry_configs.default.url https://registry.example.com")
                ctx.exit(1)
        
        # Override credentials if provided
        if username:
            registry_config.username = username
        if password:
            registry_config.password = password
        if insecure:
            registry_config.insecure = True
        
        # Check if image exists locally
        image_manager = ImageManager()
        if not image_manager.image_exists(image):
            click.echo(f"Error: Image '{image}' not found in local repository.", err=True)
            click.echo()
            click.echo("List available images with: derpy ls")
            ctx.exit(1)
        
        click.echo(f"Pushing image '{image}' to {registry_config.url}...")
        click.echo()
        
        # Create registry client
        with RegistryClient(registry_config) as client:
            # Check connectivity
            click.echo("Checking registry connectivity...")
            if not client.check_connectivity():
                click.echo(
                    f"Error: Cannot connect to registry at {registry_config.url}",
                    err=True
                )
                click.echo("Please verify the registry URL and network connectivity.")
                ctx.exit(1)
            
            # Verify authentication if credentials provided
            if registry_config.username:
                click.echo("Verifying authentication...")
                if not client.verify_authentication():
                    click.echo("Error: Authentication failed.", err=True)
                    click.echo("Please check your username and password.")
                    ctx.exit(1)
            
            # Prepare image data
            click.echo("Preparing image data...")
            manifest_bytes, config_bytes, layers_data = image_manager.prepare_image_for_push(image)
            
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
            
            # Push image
            click.echo(f"Uploading image ({len(layers_data)} layer(s), {total_size} bytes total)...")
            result = client.push_image(
                image,
                manifest_bytes,
                config_bytes,
                layers_data,
                progress_callback
            )
            
            click.echo()
            click.echo(f"✓ Successfully pushed image: {image}")
            click.echo(f"  Repository: {result['repository']}")
            click.echo(f"  Tag: {result['tag']}")
            click.echo(f"  Manifest Digest: {result['manifest_digest']}")
            
    except StorageError as e:
        click.echo(f"Storage error: {e}", err=True)
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