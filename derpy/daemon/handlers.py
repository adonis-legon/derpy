"""Request handlers for daemon operations.

This module implements handlers for processing client requests received
by the derpyd daemon. Each handler is responsible for executing a specific
operation (build, list, remove, purge) and returning appropriate responses.
"""

from typing import Optional, Callable
import logging
from pathlib import Path
import sys
import io
import time
import tempfile

from derpy.daemon.protocol import (
    BuildRequest,
    BuildResponse,
    ListRequest,
    ListResponse,
    RemoveRequest,
    RemoveResponse,
    PurgeRequest,
    PurgeResponse,
    BaseMessage,
    OutputMessage,
)
from derpy.daemon.security import (
    InputValidator,
    PathValidator,
    PrivilegeManager,
    LogSanitizer,
)
from derpy.build.engine import BuildEngine, BuildContext
from derpy.storage.manager import ImageManager
from derpy.core.exceptions import BuildError


logger = logging.getLogger(__name__)


class RequestHandler:
    """Handles execution of client requests.
    
    This class provides a dispatcher that routes requests to appropriate
    handler methods based on request type. Each handler method validates
    the request, executes the operation, and returns a response.
    
    Attributes:
        storage_lock: Lock for coordinating storage access (optional)
        base_image_cache_lock: Lock for coordinating base image cache access (optional)
    """
    
    def __init__(self, storage_lock=None, base_image_cache_lock=None):
        """Initialize request handler.
        
        Args:
            storage_lock: Threading lock for storage operations (optional)
            base_image_cache_lock: Threading lock for base image cache operations (optional)
        """
        self.storage_lock = storage_lock
        self.base_image_cache_lock = base_image_cache_lock
    
    def handle_request(
        self,
        request: BaseMessage,
        output_callback: Optional[Callable[[str], None]] = None
    ) -> BaseMessage:
        """Dispatch request to appropriate handler based on request type.
        
        This method validates the request format, routes it to the correct
        handler method, and returns the response. Invalid requests are
        rejected with descriptive error messages.
        
        Args:
            request: Request message to handle
            output_callback: Optional callback for streaming output (used by build)
            
        Returns:
            Response message appropriate for the request type
            
        Raises:
            ValueError: If request type is unknown or invalid
        """
        # Validate request has a type field
        if not hasattr(request, 'type'):
            raise ValueError("Request missing 'type' field")
        
        request_type = request.type
        
        # Validate request format before dispatching
        if hasattr(request, 'validate'):
            validation_errors = request.validate()
            if validation_errors:
                error_msg = "; ".join(validation_errors)
                logger.warning(f"Request validation failed: {error_msg}")
                
                # Return appropriate error response based on request type
                if request_type == "build":
                    return BuildResponse(
                        success=False,
                        exit_code=1,
                        error_message=f"Invalid request: {error_msg}"
                    )
                elif request_type == "remove":
                    return RemoveResponse(
                        success=False,
                        error_message=f"Invalid request: {error_msg}"
                    )
                elif request_type == "purge":
                    return PurgeResponse(
                        success=False,
                        error_message=f"Invalid request: {error_msg}"
                    )
                else:
                    raise ValueError(f"Invalid request: {error_msg}")
        
        # Dispatch to appropriate handler
        if request_type == "build":
            if not isinstance(request, BuildRequest):
                raise ValueError(f"Expected BuildRequest, got {type(request).__name__}")
            return self.handle_build_request(request, output_callback)
        
        elif request_type == "list":
            if not isinstance(request, ListRequest):
                raise ValueError(f"Expected ListRequest, got {type(request).__name__}")
            return self.handle_list_request(request)
        
        elif request_type == "remove":
            if not isinstance(request, RemoveRequest):
                raise ValueError(f"Expected RemoveRequest, got {type(request).__name__}")
            return self.handle_remove_request(request)
        
        elif request_type == "purge":
            if not isinstance(request, PurgeRequest):
                raise ValueError(f"Expected PurgeRequest, got {type(request).__name__}")
            return self.handle_purge_request(request)
        
        else:
            raise ValueError(f"Unknown request type: {request_type}")
    
    def handle_build_request(
        self,
        request: BuildRequest,
        output_callback: Optional[Callable[[str], None]] = None
    ) -> BuildResponse:
        """Execute a build request.
        
        This method:
        1. Validates all input fields for security
        2. Creates BuildContext from request parameters
        3. Validates build context and Dockerfile paths
        4. Instantiates BuildEngine with isolation enabled
        5. Executes build with output streaming to client
        6. Captures stdout/stderr and sends as OutputMessage instances
        7. Sends final BuildResponse with success/failure status
        8. Handles build errors and exceptions
        
        Args:
            request: Build request to execute
            output_callback: Optional callback for streaming output
            
        Returns:
            Build response with success/failure status
        """
        # Sanitize log message to avoid leaking credentials
        sanitized_tag = LogSanitizer.sanitize_log_message(request.tag)
        logger.info(f"Build request received: tag={sanitized_tag}")
        
        # Validate tag
        tag_errors = InputValidator.validate_tag(request.tag)
        if tag_errors:
            error_msg = f"Invalid tag: {'; '.join(tag_errors)}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        # Validate paths
        context_path_errors = InputValidator.validate_path(request.context_path, must_exist=True)
        if context_path_errors:
            error_msg = f"Invalid context path: {'; '.join(context_path_errors)}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        dockerfile_path_errors = InputValidator.validate_path(request.dockerfile_path, must_exist=True)
        if dockerfile_path_errors:
            error_msg = f"Invalid Dockerfile path: {'; '.join(dockerfile_path_errors)}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        # Validate build args
        build_args_errors = InputValidator.validate_build_args(request.build_args)
        if build_args_errors:
            error_msg = f"Invalid build args: {'; '.join(build_args_errors)}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        # Convert paths to Path objects
        context_path = Path(request.context_path)
        dockerfile_path = Path(request.dockerfile_path)
        
        # Validate paths exist
        if not context_path.exists():
            error_msg = f"Build context path does not exist: {context_path}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        if not context_path.is_dir():
            error_msg = f"Build context path is not a directory: {context_path}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        if not dockerfile_path.exists():
            error_msg = f"Dockerfile does not exist: {dockerfile_path}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        if not dockerfile_path.is_file():
            error_msg = f"Dockerfile path is not a file: {dockerfile_path}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        # Create BuildContext
        try:
            build_context = BuildContext(
                context_path=context_path,
                dockerfile_path=dockerfile_path,
                build_args=request.build_args
            )
        except Exception as e:
            error_msg = f"Failed to create build context: {e}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        # Create temporary directory with restrictive permissions for build
        temp_dir = None
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="derpy-build-"))
            PrivilegeManager.set_restrictive_permissions(temp_dir, mode=0o700)
            logger.debug(f"Created temporary build directory: {temp_dir}")
        except Exception as e:
            error_msg = f"Failed to create temporary directory: {e}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        # Instantiate BuildEngine with isolation enabled
        # Use locks if provided for thread-safe access to shared resources
        try:
            # Use system-wide storage location for daemon
            storage_manager = ImageManager(repository_path=Path("/var/lib/derpy"))
            
            # Wrap storage manager methods with locks if available
            if self.storage_lock:
                original_store = storage_manager.store_image
                def locked_store(image, tag):
                    with self.storage_lock:
                        return original_store(image, tag)
                storage_manager.store_image = locked_store
            
            build_engine = BuildEngine(
                storage_manager=storage_manager,
                enable_isolation=True
            )
            
            # Wrap base image manager methods with locks if available
            if self.base_image_cache_lock and hasattr(build_engine, 'base_image_manager'):
                base_mgr = build_engine.base_image_manager
                if base_mgr:
                    original_pull = base_mgr.pull_base_image
                    def locked_pull(image_ref):
                        with self.base_image_cache_lock:
                            return original_pull(image_ref)
                    base_mgr.pull_base_image = locked_pull
            
        except Exception as e:
            error_msg = f"Failed to initialize build engine: {e}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
        
        # Capture stdout/stderr for streaming
        if output_callback:
            # Redirect stdout/stderr to capture output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            # Create string buffers
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            
            # Create wrapper that both captures and streams
            class StreamingWriter(io.StringIO):
                def __init__(self, callback, msg_type="output"):
                    super().__init__()
                    self.callback = callback
                    self.msg_type = msg_type
                
                def write(self, text):
                    if text and text.strip():
                        # Send output message to client
                        msg = OutputMessage(
                            type=self.msg_type,
                            content=text,
                            timestamp=time.time()
                        )
                        self.callback(msg.to_json() + "\n")
                    return super().write(text)
            
            sys.stdout = StreamingWriter(output_callback, "output")
            sys.stderr = StreamingWriter(output_callback, "error")
        
        # Execute build
        try:
            logger.info(f"Starting build: {request.tag}")
            image = build_engine.build_image(build_context, request.tag)
            
            # Store image in local repository
            storage_manager.store_image(request.tag, image)
            
            logger.info(f"Build completed successfully: {request.tag}")
            
            # Get image digest
            image_digest = image.manifest.config.digest if image.manifest else None
            
            return BuildResponse(
                success=True,
                exit_code=0,
                image_digest=image_digest
            )
            
        except BuildError as e:
            error_msg = f"Build failed: {e}"
            logger.error(error_msg)
            
            # Send error output if callback available
            if output_callback:
                error_output = OutputMessage(
                    type="error",
                    content=f"\nBuild failed: {e}\n",
                    timestamp=time.time()
                )
                output_callback(error_output.to_json() + "\n")
            
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=str(e)
            )
            
        except Exception as e:
            error_msg = f"Unexpected error during build: {e}"
            # Sanitize error message before logging
            sanitized_error = LogSanitizer.sanitize_log_message(str(e))
            logger.error(f"Unexpected error during build: {sanitized_error}", exc_info=True)
            
            # Send error output if callback available
            if output_callback:
                error_output = OutputMessage(
                    type="error",
                    content=f"\nUnexpected error: {e}\n",
                    timestamp=time.time()
                )
                output_callback(error_output.to_json() + "\n")
            
            return BuildResponse(
                success=False,
                exit_code=1,
                error_message=error_msg
            )
            
        finally:
            # Restore stdout/stderr
            if output_callback:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Clean up temporary directory
            if temp_dir and temp_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")
    
    def handle_list_request(self, request: ListRequest) -> ListResponse:
        """Execute a list images request.
        
        Uses ImageManager.list_local_images() to retrieve all images
        from the local repository and returns them in the response.
        
        Args:
            request: List request to execute
            
        Returns:
            List response with image information
        """
        logger.info("List request received")
        
        try:
            # Get storage manager - use system-wide storage location for daemon
            storage_manager = ImageManager(repository_path=Path("/var/lib/derpy"))
            
            # List all local images with lock if available
            if self.storage_lock:
                with self.storage_lock:
                    images = storage_manager.list_local_images()
            else:
                images = storage_manager.list_local_images()
            
            # Convert ImageInfo objects to protocol ImageInfo objects
            from derpy.daemon.protocol import ImageInfo as ProtocolImageInfo
            protocol_images = []
            for img in images:
                protocol_img = ProtocolImageInfo(
                    tag=img.tag,
                    digest="",  # Not available in storage ImageInfo
                    size=img.size,
                    created=img.created
                )
                protocol_images.append(protocol_img)
            
            logger.info(f"Listed {len(protocol_images)} images")
            return ListResponse(images=protocol_images)
            
        except Exception as e:
            error_msg = f"Failed to list images: {e}"
            logger.error(error_msg, exc_info=True)
            # Return empty list on error (list operation should not fail)
            return ListResponse(images=[])
    
    def handle_remove_request(self, request: RemoveRequest) -> RemoveResponse:
        """Execute a remove image request.
        
        Uses ImageManager.remove_image() to remove the specified image
        from the local repository.
        
        Args:
            request: Remove request to execute
            
        Returns:
            Remove response with success/failure status
        """
        # Sanitize tag for logging
        sanitized_tag = LogSanitizer.sanitize_log_message(request.tag)
        logger.info(f"Remove request received: tag={sanitized_tag}")
        
        # Validate tag
        tag_errors = InputValidator.validate_tag(request.tag)
        if tag_errors:
            error_msg = f"Invalid tag: {'; '.join(tag_errors)}"
            logger.error(error_msg)
            return RemoveResponse(
                success=False,
                error_message=error_msg
            )
        
        try:
            # Get storage manager - use system-wide storage location for daemon
            storage_manager = ImageManager(repository_path=Path("/var/lib/derpy"))
            
            # Remove the image with lock if available
            if self.storage_lock:
                with self.storage_lock:
                    removed = storage_manager.remove_image(request.tag)
            else:
                removed = storage_manager.remove_image(request.tag)
            
            if removed:
                logger.info(f"Successfully removed image: {request.tag}")
                return RemoveResponse(success=True)
            else:
                error_msg = f"Image not found: {request.tag}"
                logger.warning(error_msg)
                return RemoveResponse(
                    success=False,
                    error_message=error_msg
                )
            
        except Exception as e:
            error_msg = f"Failed to remove image '{request.tag}': {e}"
            logger.error(error_msg, exc_info=True)
            return RemoveResponse(
                success=False,
                error_message=error_msg
            )
    
    def handle_purge_request(self, request: PurgeRequest) -> PurgeResponse:
        """Execute a purge all images request.
        
        Uses ImageManager.remove_all_images() to remove all images
        from the local repository.
        
        Args:
            request: Purge request to execute
            
        Returns:
            Purge response with success/failure status and count of removed images
        """
        logger.info(f"Purge request received: force={request.force}")
        
        try:
            # Get storage manager - use system-wide storage location for daemon
            storage_manager = ImageManager(repository_path=Path("/var/lib/derpy"))
            
            # Remove all images with lock if available
            if self.storage_lock:
                with self.storage_lock:
                    removed_count = storage_manager.remove_all_images()
            else:
                removed_count = storage_manager.remove_all_images()
            
            logger.info(f"Successfully purged {removed_count} images")
            return PurgeResponse(
                success=True,
                removed_count=removed_count
            )
            
        except Exception as e:
            error_msg = f"Failed to purge images: {e}"
            logger.error(error_msg, exc_info=True)
            return PurgeResponse(
                success=False,
                removed_count=0,
                error_message=error_msg
            )
