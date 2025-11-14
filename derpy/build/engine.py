"""Build engine for creating container images from Dockerfiles."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess
import tempfile
import shutil
import tarfile
import gzip
import hashlib
import platform
from datetime import datetime, timezone

from derpy.dockerfile.parser import DockerfileParser, Dockerfile, Instruction, InstructionType
from derpy.dockerfile.handlers import FromHandler, RunHandler, CmdHandler, RunInstruction
from derpy.oci.models import (
    Image,
    ImageConfig,
    Manifest,
    Layer,
    ContainerConfig,
    RootFS,
    HistoryEntry,
    Descriptor,
    MEDIA_TYPE_IMAGE_CONFIG,
    MEDIA_TYPE_IMAGE_LAYER,
)
from derpy.build.layers import LayerBuilder
from derpy.build.pipeline import InstructionPipeline, PipelineResult
from derpy.build.base_image import BaseImageManager
from derpy.build.isolation import IsolationExecutor
from derpy.build.diff import LayerDiffManager
from derpy.storage.manager import ImageManager
from derpy.core.exceptions import (
    BuildError,
    BuildContextError,
    CommandExecutionError,
    LayerCreationError,
    DockerfileSyntaxError,
    PlatformNotSupportedError
)
from derpy.core.logging import get_logger

logger = get_logger('build')


@dataclass
class BuildContext:
    """Build context for image building."""
    
    context_path: Path
    dockerfile_path: Path
    build_args: Dict[str, str] = field(default_factory=dict)
    platform_arch: str = field(default_factory=lambda: platform.machine())
    platform_os: str = field(default_factory=lambda: platform.system().lower())
    rootfs_path: Optional[Path] = None  # Path to extracted base image rootfs
    
    def __post_init__(self):
        """Validate build context paths."""
        if not self.context_path.exists():
            raise BuildContextError(
                "Build context path does not exist",
                context_path=str(self.context_path)
            )
        
        if not self.context_path.is_dir():
            raise BuildContextError(
                "Build context path is not a directory",
                context_path=str(self.context_path)
            )
        
        if not self.dockerfile_path.exists():
            from derpy.core.exceptions import DockerfileNotFoundError
            raise DockerfileNotFoundError(str(self.dockerfile_path))
        
        if not self.dockerfile_path.is_file():
            raise BuildError(f"Dockerfile path is not a file: {self.dockerfile_path}")


class BuildEngine:
    """Engine for building container images from Dockerfiles.
    
    Handles the complete build process including:
    - Parsing Dockerfiles
    - Executing RUN instructions
    - Creating filesystem layers
    - Generating OCI-compliant image artifacts
    - Build isolation with base image support (Linux only)
    """
    
    def __init__(
        self,
        storage_manager: Optional[ImageManager] = None,
        enable_isolation: bool = True,
        base_image_cache_dir: Optional[Path] = None,
        chroot_timeout: int = 600
    ):
        """Initialize the build engine.
        
        Args:
            storage_manager: Optional ImageManager for base image caching
            enable_isolation: Whether to enable build isolation (default: True)
            base_image_cache_dir: Directory for caching base images
            chroot_timeout: Timeout for chroot command execution in seconds
        """
        self.parser = DockerfileParser()
        self.from_handler = FromHandler()
        self.run_handler = RunHandler()
        self.cmd_handler = CmdHandler()
        self.layer_builder = LayerBuilder()
        
        # Store configuration
        self.enable_isolation = enable_isolation
        self.base_image_cache_dir = base_image_cache_dir
        self.chroot_timeout = chroot_timeout
        
        # Initialize isolation components
        self.storage_manager = storage_manager
        self.base_image_manager = None
        self.isolation_executor = None
        self.layer_diff_manager = None
        self.use_isolation = False
        self.base_image = None  # Store base image for layer combination
        
        # Check if isolation is supported
        self._check_isolation_support()
    
    def _handle_from_instruction(self, dockerfile: Dockerfile, context: BuildContext) -> None:
        """Handle FROM instruction by pulling and extracting base image.
        
        Creates a unique temporary directory for this build's rootfs to ensure
        concurrent builds don't interfere with each other.
        
        Args:
            dockerfile: Parsed Dockerfile
            context: Build context
            
        Raises:
            BuildError: If FROM handling fails
        """
        # Find FROM instruction
        from_instruction = None
        for instruction in dockerfile.instructions:
            if instruction.type == InstructionType.FROM:
                from_instruction = instruction
                break
        
        if not from_instruction:
            # No FROM instruction - skip base image handling
            logger.debug("No FROM instruction found, skipping base image handling")
            return
        
        try:
            # Parse FROM instruction to get image reference
            from_inst = self.from_handler.process(from_instruction)
            image_ref = from_inst.image
            
            logger.info(f"Pulling base image: {image_ref}")
            
            # Pull base image (will use cache if available)
            try:
                self.base_image = self.base_image_manager.pull_base_image(image_ref)
            except Exception as pull_error:
                # BaseImageError will have detailed message, re-raise as-is
                # Other errors get wrapped with context
                if not isinstance(pull_error, BuildError):
                    raise BuildError(
                        f"Failed to pull base image '{image_ref}': {pull_error}"
                    )
                raise
            
            logger.info(f"Base image pulled: {image_ref} ({len(self.base_image.layers)} layers)")
            
            # Create unique temporary directory for this build's rootfs
            # Using mkdtemp ensures uniqueness and prevents concurrent build interference
            try:
                rootfs_temp = tempfile.mkdtemp(prefix="derpy_rootfs_", suffix=f"_{id(context)}")
                context.rootfs_path = Path(rootfs_temp)
            except (OSError, PermissionError) as temp_error:
                raise BuildError(
                    f"Failed to create temporary directory for rootfs: {temp_error}\n"
                    "Check disk space and permissions."
                )
            
            logger.info(f"Created isolated rootfs directory: {context.rootfs_path}")
            logger.debug(f"Extracting base image to: {context.rootfs_path}")
            
            # Extract base image layers to build-specific rootfs
            try:
                self.base_image_manager.extract_base_image(self.base_image, context.rootfs_path)
            except Exception as extract_error:
                # Clean up rootfs on extraction failure
                self._cleanup_rootfs(context)
                # BaseImageError will have detailed message, re-raise as-is
                # Other errors get wrapped with context
                if not isinstance(extract_error, BuildError):
                    raise BuildError(
                        f"Failed to extract base image '{image_ref}': {extract_error}"
                    )
                raise
            
            logger.info(f"Base image extracted successfully to isolated rootfs")
            
        except BuildError:
            # Clean up rootfs on failure
            if context.rootfs_path and context.rootfs_path.exists():
                logger.debug("Cleaning up rootfs after FROM instruction failure")
                self._cleanup_rootfs(context)
            raise
        except Exception as e:
            # Clean up rootfs on failure
            if context.rootfs_path and context.rootfs_path.exists():
                logger.debug("Cleaning up rootfs after FROM instruction failure")
                self._cleanup_rootfs(context)
            raise BuildError(
                f"Unexpected error while handling FROM instruction: {e}"
            )
    
    def _combine_layers(self, new_layers: List[Layer]) -> List[Layer]:
        """Combine base image layers with new layers from RUN instructions.
        
        If a base image was used, this method combines:
        - All base image layers (in order)
        - New layers from RUN instructions (appended after base layers)
        
        Args:
            new_layers: Layers created from RUN instructions
            
        Returns:
            Combined list of all layers in correct order
        """
        if not self.base_image or not self.use_isolation:
            # No base image or isolation not used - return only new layers
            return new_layers
        
        # Combine base layers + new layers
        all_layers = list(self.base_image.layers) + new_layers
        
        logger.info(
            f"Combined layers: {len(self.base_image.layers)} base + "
            f"{len(new_layers)} new = {len(all_layers)} total"
        )
        
        return all_layers
    
    def _cleanup_rootfs(self, context: BuildContext) -> None:
        """Clean up temporary rootfs directory.
        
        This method ensures proper cleanup of the build-specific rootfs directory
        on both successful build completion and build failure. It handles:
        - Unmounting chroot mounts (/proc, /sys, /dev)
        - Removing the temporary rootfs directory
        - Graceful error handling to prevent cleanup failures from blocking builds
        
        Args:
            context: Build context with rootfs_path
        """
        if not context.rootfs_path or not context.rootfs_path.exists():
            logger.debug("No rootfs to clean up")
            return
        
        rootfs_path = context.rootfs_path
        
        try:
            # Clean up chroot environment first if isolation is enabled
            if self.use_isolation and self.isolation_executor:
                logger.debug(f"Cleaning up chroot environment: {rootfs_path}")
                self.isolation_executor.cleanup_chroot_environment(rootfs_path)
            
            # Remove temporary rootfs directory
            logger.info(f"Removing temporary rootfs: {rootfs_path}")
            shutil.rmtree(rootfs_path, ignore_errors=False)
            logger.debug(f"Successfully removed rootfs: {rootfs_path}")
            
        except PermissionError as e:
            # Permission errors might occur with mounted filesystems
            logger.warning(
                f"Permission denied while cleaning up rootfs {rootfs_path}: {e}. "
                "Some files may remain. Try running with sudo to clean up."
            )
        except OSError as e:
            # Other OS errors during cleanup
            logger.warning(
                f"Failed to clean up rootfs {rootfs_path}: {e}. "
                "Some files may remain."
            )
        except Exception as e:
            # Catch-all for unexpected errors
            logger.warning(
                f"Unexpected error during rootfs cleanup {rootfs_path}: {e}"
            )
        finally:
            # Clear the rootfs_path from context to prevent double cleanup
            context.rootfs_path = None
    
    def _check_isolation_support(self) -> None:
        """Check if build isolation is supported on this platform.
        
        Isolation requires Linux with chroot capability. If not available,
        falls back to v0.1.0 behavior (non-isolated builds).
        """
        # Check if isolation is disabled in configuration
        if not self.enable_isolation:
            self.use_isolation = False
            logger.info("Build isolation disabled by configuration")
            return
        
        try:
            # Create isolation executor to test capability
            executor = IsolationExecutor()
            executor.validate_linux_environment()
            
            # If validation passes, isolation is supported
            self.use_isolation = True
            self.isolation_executor = executor
            self.layer_diff_manager = LayerDiffManager(self.layer_builder)
            
            # Initialize base image manager if storage is available
            if self.storage_manager:
                self.base_image_manager = BaseImageManager(
                    self.storage_manager,
                    cache_dir=self.base_image_cache_dir
                )
            
            logger.info("Build isolation enabled (Linux with chroot support detected)")
            
        except PlatformNotSupportedError as e:
            # Not on Linux - fall back to non-isolated builds
            self.use_isolation = False
            logger.info(
                f"Build isolation disabled: {e.message}. "
                "Falling back to v0.1.0 behavior (non-isolated builds)."
            )
        except Exception as e:
            # Other errors (e.g., permission issues) - fall back gracefully
            self.use_isolation = False
            logger.warning(
                f"Build isolation disabled due to: {e}. "
                "Falling back to v0.1.0 behavior (non-isolated builds)."
            )
    
    def build_image(self, context: BuildContext, tag: str) -> Image:
        """Build a container image from a Dockerfile.
        
        Args:
            context: Build context with paths and configuration
            tag: Tag for the resulting image
        
        Returns:
            Built Image object with manifest, config, and layers
        
        Raises:
            BuildError: If build fails at any stage
        """
        # Log isolation status at build start
        if self.use_isolation:
            logger.info(f"Starting build with isolation enabled: {tag}")
        else:
            logger.info(f"Starting build without isolation (v0.1.0 mode): {tag}")
        
        # Parse Dockerfile
        try:
            dockerfile = self.parser.parse(context.dockerfile_path)
        except Exception as e:
            raise BuildError(
                f"Failed to parse Dockerfile: {context.dockerfile_path}\n"
                f"Error: {e}"
            )
        
        # Validate Dockerfile
        if not dockerfile.is_valid:
            error_messages = "\n".join(str(err) for err in dockerfile.validation_errors)
            raise BuildError(
                f"Dockerfile validation failed:\n{error_messages}"
            )
        
        # Handle FROM instruction if isolation is enabled
        if self.use_isolation and self.base_image_manager:
            try:
                self._handle_from_instruction(dockerfile, context)
            except BuildError:
                # Error already has context, cleanup happens in _handle_from_instruction
                raise
            except Exception as e:
                # Unexpected error - ensure cleanup
                self._cleanup_rootfs(context)
                raise BuildError(
                    f"Unexpected error while handling FROM instruction: {e}"
                )
        
        # Execute instruction pipeline
        pipeline = InstructionPipeline(context)
        
        # Create a layer executor that wraps our RUN execution logic
        def layer_executor(instruction: Instruction, run_inst: RunInstruction) -> Optional[Layer]:
            return self._execute_run_instruction_impl(instruction, run_inst, context)
        
        try:
            pipeline_result = pipeline.execute(dockerfile, layer_executor)
        except BuildError:
            # Clean up on build failure
            self._cleanup_rootfs(context)
            raise
        except Exception as e:
            # Clean up on unexpected failure
            self._cleanup_rootfs(context)
            raise BuildError(
                f"Build pipeline execution failed: {e}"
            )
        
        # Build succeeded - clean up temporary rootfs
        self._cleanup_rootfs(context)
        
        # Combine base and new layers if isolation was used
        try:
            all_layers = self._combine_layers(pipeline_result.layers)
        except Exception as e:
            raise BuildError(
                f"Failed to combine base and new layers: {e}"
            )
        
        # Generate image configuration
        try:
            config = self._generate_image_config_from_pipeline(
                pipeline_result,
                all_layers,
                context
            )
        except Exception as e:
            raise BuildError(
                f"Failed to generate image configuration: {e}"
            )
        
        # Generate manifest
        try:
            manifest = self._generate_manifest(config, all_layers)
        except Exception as e:
            raise BuildError(
                f"Failed to generate image manifest: {e}"
            )
        
        # Create complete image
        try:
            image = Image(
                manifest=manifest,
                config=config,
                layers=all_layers
            )
        except Exception as e:
            raise BuildError(
                f"Failed to create image object: {e}"
            )
        
        # Validate final image
        validation_errors = image.validate()
        if validation_errors:
            raise BuildError(
                f"Image validation failed:\n" + 
                "\n".join(f"  - {err}" for err in validation_errors)
            )
        
        logger.info(f"Successfully built image: {tag}")
        return image
    
    def _execute_run_instruction_impl(
        self,
        instruction: Instruction,
        run_inst: RunInstruction,
        context: BuildContext
    ) -> Optional[Layer]:
        """Execute a RUN instruction and create a layer.
        
        Args:
            instruction: RUN instruction to execute
            run_inst: Parsed RUN instruction
            context: Build context
        
        Returns:
            Layer object or None if no changes
        
        Raises:
            BuildError: If command execution fails
        """
        # Check if isolation is enabled and rootfs exists
        if self.use_isolation and context.rootfs_path and context.rootfs_path.exists():
            # Use isolated execution with chroot
            return self._execute_run_with_isolation(instruction, run_inst, context)
        else:
            # Fall back to v0.1.0 behavior (non-isolated execution)
            return self._execute_run_without_isolation(instruction, run_inst, context)
    
    def _execute_run_without_isolation(
        self,
        instruction: Instruction,
        run_inst: RunInstruction,
        context: BuildContext
    ) -> Optional[Layer]:
        """Execute RUN instruction without isolation (v0.1.0 behavior).
        
        Args:
            instruction: RUN instruction to execute
            run_inst: Parsed RUN instruction
            context: Build context
        
        Returns:
            Layer object with marker file
        
        Raises:
            BuildError: If command execution fails
        """
        # Create a temporary directory for this layer's changes
        with tempfile.TemporaryDirectory() as layer_temp:
            layer_dir = Path(layer_temp) / "layer"
            layer_dir.mkdir()
            
            # For v0.1.0, we execute commands in a simple subprocess
            # In a real implementation, this would use chroot or containers
            try:
                # Execute the command
                # Note: This is a simplified implementation
                # A production version would need proper isolation
                result = subprocess.run(
                    run_inst.command,
                    shell=run_inst.is_shell_form,
                    cwd=context.context_path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    raise CommandExecutionError(
                        command=run_inst.command,
                        exit_code=result.returncode,
                        stdout=result.stdout,
                        stderr=result.stderr
                    )
                
                # For v0.1.0, we create a minimal layer with a marker file
                # In a real implementation, this would capture filesystem changes
                marker_file = layer_dir / "derpy_layer_marker.txt"
                marker_file.write_text(
                    f"Layer created from RUN: {run_inst.command}\n"
                    f"Executed at: {datetime.now(timezone.utc).isoformat()}\n"
                )
                
            except subprocess.TimeoutExpired:
                raise BuildError(f"RUN command timed out: {run_inst.command}")
            except Exception as e:
                raise BuildError(f"Failed to execute RUN command: {e}")
            
            # Create tar.gz layer from the changes
            try:
                layer = self.layer_builder.create_layer_from_directory(
                    layer_dir,
                    layer_name=f"run_{instruction.line_number}"
                )
                return layer
            except Exception as e:
                raise LayerCreationError(str(e), cause=e)
    
    def _execute_run_with_isolation(
        self,
        instruction: Instruction,
        run_inst: RunInstruction,
        context: BuildContext
    ) -> Optional[Layer]:
        """Execute RUN instruction in isolated chroot environment.
        
        This method implements the complete isolated execution flow:
        1. Create snapshot before command execution
        2. Setup chroot environment
        3. Execute command in chroot
        4. Create snapshot after command execution
        5. Capture filesystem diff
        6. Create layer from diff
        
        Args:
            instruction: RUN instruction to execute
            run_inst: Parsed RUN instruction
            context: Build context with rootfs_path
        
        Returns:
            Layer object with captured filesystem changes, or None if no changes
        
        Raises:
            BuildError: If command execution fails
        """
        if not context.rootfs_path:
            raise BuildError(
                "Rootfs path not set for isolated execution\n"
                "This is an internal error - the base image should have been extracted."
            )
        
        logger.info(f"Executing RUN in chroot: {run_inst.command}")
        
        try:
            # Step 1: Create snapshot before command execution
            logger.debug("Creating filesystem snapshot before command execution")
            try:
                before_snapshot = self.layer_diff_manager.create_snapshot(context.rootfs_path)
            except Exception as snapshot_error:
                raise BuildError(
                    f"Failed to create filesystem snapshot before RUN command\n"
                    f"Command: {run_inst.command}\n"
                    f"Rootfs: {context.rootfs_path}\n"
                    f"Error: {snapshot_error}"
                )
            
            # Step 2: Setup chroot environment
            try:
                self.isolation_executor.setup_chroot_environment(context.rootfs_path)
            except Exception as setup_error:
                # IsolationError will have detailed message
                if not isinstance(setup_error, BuildError):
                    raise BuildError(
                        f"Failed to setup chroot environment for RUN command\n"
                        f"Command: {run_inst.command}\n"
                        f"Rootfs: {context.rootfs_path}\n"
                        f"Error: {setup_error}"
                    )
                raise
            
            # Step 3: Execute command in chroot
            try:
                result = self.isolation_executor.execute_in_chroot(
                    rootfs=context.rootfs_path,
                    command=run_inst.command,
                    shell="/bin/sh",
                    timeout=self.chroot_timeout
                )
            except Exception as exec_error:
                # IsolationError will have detailed message
                if not isinstance(exec_error, BuildError):
                    raise BuildError(
                        f"Failed to execute RUN command in chroot\n"
                        f"Command: {run_inst.command}\n"
                        f"Error: {exec_error}"
                    )
                raise
            
            # Check execution result
            if not result.is_success():
                # Format error message with command details
                error_msg = (
                    f"RUN command failed with exit code {result.exit_code}\n"
                    f"Command: {run_inst.command}\n"
                    f"Duration: {result.duration:.2f}s"
                )
                
                if result.stdout and result.stdout.strip():
                    error_msg += f"\n\nStdout:\n{result.stdout.strip()}"
                
                if result.stderr and result.stderr.strip():
                    error_msg += f"\n\nStderr:\n{result.stderr.strip()}"
                
                raise CommandExecutionError(
                    command=run_inst.command,
                    exit_code=result.exit_code,
                    stdout=result.stdout,
                    stderr=result.stderr
                )
            
            logger.info(
                f"Command executed successfully in {result.duration:.2f}s: "
                f"{run_inst.command[:50]}..."
            )
            
            # Step 4-6: Capture filesystem diff and create layer
            logger.debug("Capturing filesystem changes")
            try:
                layer = self.layer_diff_manager.capture_diff(
                    rootfs=context.rootfs_path,
                    before_snapshot=before_snapshot,
                    instruction=instruction.raw_line.strip()
                )
            except Exception as diff_error:
                # FilesystemDiffError will have detailed message
                if not isinstance(diff_error, BuildError):
                    raise BuildError(
                        f"Failed to capture filesystem changes after RUN command\n"
                        f"Command: {run_inst.command}\n"
                        f"Error: {diff_error}"
                    )
                raise
            
            if layer:
                logger.info(f"Created layer from filesystem changes: {layer.digest[:19]}...")
            else:
                logger.info("No filesystem changes detected, no layer created")
            
            return layer
            
        except CommandExecutionError:
            raise
        except BuildError:
            raise
        except Exception as e:
            raise BuildError(
                f"Unexpected error while executing RUN command in isolation\n"
                f"Command: {run_inst.command}\n"
                f"Error: {e}"
            )
    
    def _generate_image_config_from_pipeline(
        self,
        pipeline_result: PipelineResult,
        all_layers: List[Layer],
        context: BuildContext
    ) -> ImageConfig:
        """Generate OCI image configuration from pipeline result.
        
        Args:
            pipeline_result: Result from instruction pipeline
            all_layers: All layers (base + new) in correct order
            context: Build context
        
        Returns:
            ImageConfig object
        """
        # Create container config
        container_config = ContainerConfig()
        
        # Set CMD if present
        if pipeline_result.cmd_instruction:
            cmd_value = pipeline_result.cmd_instruction
            # Parse CMD value
            if isinstance(cmd_value, str):
                if cmd_value.startswith("[") and cmd_value.endswith("]"):
                    # Exec form - parse as JSON-like array
                    import json
                    try:
                        container_config.cmd = json.loads(cmd_value)
                    except json.JSONDecodeError:
                        # Fallback to shell form
                        container_config.cmd = ["/bin/sh", "-c", cmd_value]
                else:
                    # Shell form
                    container_config.cmd = ["/bin/sh", "-c", cmd_value]
            else:
                container_config.cmd = cmd_value
        elif self.base_image and self.base_image.config.config.cmd:
            # Inherit CMD from base image if not overridden
            container_config.cmd = self.base_image.config.config.cmd
        
        # Create rootfs with diff IDs from all layers (base + new)
        rootfs = RootFS(
            type="layers",
            diff_ids=[layer.diff_id for layer in all_layers if layer.diff_id]
        )
        
        # Combine history: base image history + new history from pipeline
        history = self._combine_history(pipeline_result.history)
        
        # Create image config
        created_time = datetime.now(timezone.utc).isoformat()
        config = ImageConfig(
            architecture=self._normalize_architecture(context.platform_arch),
            os=self._normalize_os(context.platform_os),
            config=container_config,
            rootfs=rootfs,
            history=history,
            created=created_time,
            author="derpy v0.2.0"
        )
        
        return config
    
    def _combine_history(self, new_history: List[HistoryEntry]) -> List[HistoryEntry]:
        """Combine base image history with new history entries.
        
        Args:
            new_history: History entries from current build
            
        Returns:
            Combined history entries in correct order
        """
        if not self.base_image or not self.use_isolation:
            # No base image - return only new history
            return new_history
        
        # Combine base history + new history
        base_history = self.base_image.config.history or []
        all_history = list(base_history) + new_history
        
        logger.debug(
            f"Combined history: {len(base_history)} base + "
            f"{len(new_history)} new = {len(all_history)} total entries"
        )
        
        return all_history
    
    def _generate_manifest(self, config: ImageConfig, layers: List[Layer]) -> Manifest:
        """Generate OCI image manifest.
        
        Args:
            config: Image configuration
            layers: List of layers
        
        Returns:
            Manifest object
        """
        # Create config descriptor
        config_json = config.to_json()
        config_bytes = config_json.encode('utf-8')
        config_digest = f"sha256:{hashlib.sha256(config_bytes).hexdigest()}"
        
        config_descriptor = Descriptor(
            media_type=MEDIA_TYPE_IMAGE_CONFIG,
            digest=config_digest,
            size=len(config_bytes)
        )
        
        # Create layer descriptors
        layer_descriptors = [layer.to_descriptor() for layer in layers]
        
        # Create manifest
        manifest = Manifest(
            config=config_descriptor,
            layers=layer_descriptors
        )
        
        return manifest
    
    def _normalize_architecture(self, arch: str) -> str:
        """Normalize architecture name to OCI standard.
        
        Args:
            arch: Platform architecture string
        
        Returns:
            Normalized architecture name
        """
        arch_map = {
            "x86_64": "amd64",
            "aarch64": "arm64",
            "armv7l": "arm",
            "i386": "386",
            "i686": "386",
        }
        return arch_map.get(arch.lower(), arch.lower())
    
    def _normalize_os(self, os_name: str) -> str:
        """Normalize OS name to OCI standard.
        
        Args:
            os_name: Platform OS string
        
        Returns:
            Normalized OS name
        """
        os_map = {
            "darwin": "darwin",
            "linux": "linux",
            "windows": "windows",
        }
        return os_map.get(os_name.lower(), os_name.lower())
