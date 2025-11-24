"""Daemon protocol message classes.

This module implements the message protocol for communication between the
Derpy CLI client and the derpyd daemon over Unix domain sockets.

All messages are serialized as JSON and transmitted with newline delimiters.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
import json


@dataclass
class BaseMessage:
    """Base class for protocol messages.
    
    Provides common serialization/deserialization functionality.
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the message
        """
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Deserialize from dictionary.
        
        Args:
            data: Dictionary containing message data
            
        Returns:
            Message instance
        """
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str):
        """Deserialize from JSON string.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Message instance
            
        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to deserialize message: {e}")


# Request Messages

@dataclass
class BuildRequest(BaseMessage):
    """Request to build a container image.
    
    Attributes:
        type: Request type identifier (always "build")
        context_path: Absolute path to build context directory
        dockerfile_path: Absolute path to Dockerfile
        tag: Image tag (e.g., "myapp:latest")
        build_args: Optional build arguments as key-value pairs
    """
    type: str = "build"
    context_path: str = ""
    dockerfile_path: str = ""
    tag: str = ""
    build_args: Dict[str, str] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """Validate request fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.context_path:
            errors.append("context_path is required")
        
        if not self.dockerfile_path:
            errors.append("dockerfile_path is required")
        
        if not self.tag:
            errors.append("tag is required")
        
        if self.type != "build":
            errors.append(f"Invalid type: expected 'build', got '{self.type}'")
        
        return errors


@dataclass
class ListRequest(BaseMessage):
    """Request to list local images.
    
    Attributes:
        type: Request type identifier (always "list")
    """
    type: str = "list"
    
    def validate(self) -> List[str]:
        """Validate request fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.type != "list":
            errors.append(f"Invalid type: expected 'list', got '{self.type}'")
        
        return errors


@dataclass
class RemoveRequest(BaseMessage):
    """Request to remove a container image.
    
    Attributes:
        type: Request type identifier (always "remove")
        tag: Image tag to remove
    """
    type: str = "remove"
    tag: str = ""
    
    def validate(self) -> List[str]:
        """Validate request fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.tag:
            errors.append("tag is required")
        
        if self.type != "remove":
            errors.append(f"Invalid type: expected 'remove', got '{self.type}'")
        
        return errors


@dataclass
class PurgeRequest(BaseMessage):
    """Request to purge all local images.
    
    Attributes:
        type: Request type identifier (always "purge")
        force: Whether to force removal without confirmation
    """
    type: str = "purge"
    force: bool = False
    
    def validate(self) -> List[str]:
        """Validate request fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.type != "purge":
            errors.append(f"Invalid type: expected 'purge', got '{self.type}'")
        
        return errors


# Response Messages

@dataclass
class BuildResponse(BaseMessage):
    """Response from build operation.
    
    Attributes:
        success: Whether the build succeeded
        exit_code: Exit code from build process
        error_message: Error message if build failed
        image_digest: SHA256 digest of built image if successful
    """
    success: bool = False
    exit_code: int = 0
    error_message: Optional[str] = None
    image_digest: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate response fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.success and self.exit_code != 0:
            errors.append("success=True but exit_code is non-zero")
        
        if not self.success and self.exit_code == 0:
            errors.append("success=False but exit_code is zero")
        
        if not self.success and not self.error_message:
            errors.append("error_message is required when success=False")
        
        return errors


@dataclass
class ImageInfo:
    """Information about a container image.
    
    Attributes:
        tag: Image tag
        digest: Image digest
        size: Image size in bytes
        created: Creation timestamp
    """
    tag: str
    digest: str
    size: int
    created: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageInfo":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ListResponse(BaseMessage):
    """Response from list images operation.
    
    Attributes:
        images: List of image information
    """
    images: List[ImageInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "images": [img.to_dict() for img in self.images]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListResponse":
        """Deserialize from dictionary."""
        images = [ImageInfo.from_dict(img) for img in data.get("images", [])]
        return cls(images=images)
    
    def validate(self) -> List[str]:
        """Validate response fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        # List response is always valid (empty list is acceptable)
        return []


@dataclass
class RemoveResponse(BaseMessage):
    """Response from remove image operation.
    
    Attributes:
        success: Whether the removal succeeded
        error_message: Error message if removal failed
    """
    success: bool = False
    error_message: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate response fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.success and not self.error_message:
            errors.append("error_message is required when success=False")
        
        return errors


@dataclass
class PurgeResponse(BaseMessage):
    """Response from purge all images operation.
    
    Attributes:
        success: Whether the purge succeeded
        removed_count: Number of images removed
        error_message: Error message if purge failed
    """
    success: bool = False
    removed_count: int = 0
    error_message: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate response fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.success and not self.error_message:
            errors.append("error_message is required when success=False")
        
        if self.removed_count < 0:
            errors.append("removed_count cannot be negative")
        
        return errors


# Streaming Messages

@dataclass
class OutputMessage(BaseMessage):
    """Streaming output message during build.
    
    Attributes:
        type: Message type ("output", "error", "progress")
        content: Output content
        timestamp: Unix timestamp when message was generated
    """
    type: str = "output"
    content: str = ""
    timestamp: float = 0.0
    
    def validate(self) -> List[str]:
        """Validate message fields.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        valid_types = ["output", "error", "progress"]
        if self.type not in valid_types:
            errors.append(f"Invalid type: must be one of {valid_types}")
        
        if self.timestamp < 0:
            errors.append("timestamp cannot be negative")
        
        return errors


# Message type registry for deserialization
MESSAGE_TYPES = {
    "build": BuildRequest,
    "list": ListRequest,
    "remove": RemoveRequest,
    "purge": PurgeRequest,
    "output": OutputMessage,
    "error": OutputMessage,
    "progress": OutputMessage,
}


def deserialize_message(json_str: str) -> BaseMessage:
    """Deserialize a JSON message to the appropriate message type.
    
    Args:
        json_str: JSON string to deserialize
        
    Returns:
        Deserialized message instance
        
    Raises:
        ValueError: If message type is unknown or JSON is invalid
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    msg_type = data.get("type")
    if not msg_type:
        raise ValueError("Message missing 'type' field")
    
    message_class = MESSAGE_TYPES.get(msg_type)
    if not message_class:
        raise ValueError(f"Unknown message type: {msg_type}")
    
    return message_class.from_dict(data)
