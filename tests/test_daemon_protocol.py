"""Tests for daemon protocol messages.

Property 12: JSON request serialization
Feature: daemon-socket-support, Property 12: JSON request serialization
Validates: Requirements 4.1
"""

import pytest
from hypothesis import given, strategies as st
from derpy.daemon.protocol import (
    BuildRequest,
    ListRequest,
    RemoveRequest,
    PurgeRequest,
    BuildResponse,
    ListResponse,
    RemoveResponse,
    PurgeResponse,
    OutputMessage,
    ImageInfo,
    deserialize_message,
)


class TestBuildRequest:
    """Tests for BuildRequest message."""
    
    def test_create_build_request(self):
        """Test creating a valid build request."""
        req = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="/path/to/Dockerfile",
            tag="myapp:latest"
        )
        assert req.type == "build"
        assert req.context_path == "/path/to/context"
        assert req.dockerfile_path == "/path/to/Dockerfile"
        assert req.tag == "myapp:latest"
    
    def test_build_request_to_json(self):
        """Test build request serialization to JSON."""
        req = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="/path/to/Dockerfile",
            tag="myapp:latest",
            build_args={"VERSION": "1.0"}
        )
        json_str = req.to_json()
        assert isinstance(json_str, str)
        assert "build" in json_str
        assert "/path/to/context" in json_str
        assert "myapp:latest" in json_str
    
    def test_build_request_from_json(self):
        """Test build request deserialization from JSON."""
        json_str = '{"type": "build", "context_path": "/path/to/context", "dockerfile_path": "/path/to/Dockerfile", "tag": "myapp:latest", "build_args": {}}'
        req = BuildRequest.from_json(json_str)
        assert req.type == "build"
        assert req.context_path == "/path/to/context"
        assert req.dockerfile_path == "/path/to/Dockerfile"
        assert req.tag == "myapp:latest"
    
    def test_build_request_validation_success(self):
        """Test build request validation with valid data."""
        req = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="/path/to/Dockerfile",
            tag="myapp:latest"
        )
        errors = req.validate()
        assert len(errors) == 0
    
    def test_build_request_validation_missing_context(self):
        """Test build request validation with missing context_path."""
        req = BuildRequest(
            context_path="",
            dockerfile_path="/path/to/Dockerfile",
            tag="myapp:latest"
        )
        errors = req.validate()
        assert len(errors) > 0
        assert any("context_path" in err for err in errors)
    
    def test_build_request_validation_missing_tag(self):
        """Test build request validation with missing tag."""
        req = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="/path/to/Dockerfile",
            tag=""
        )
        errors = req.validate()
        assert len(errors) > 0
        assert any("tag" in err for err in errors)


class TestListRequest:
    """Tests for ListRequest message."""
    
    def test_create_list_request(self):
        """Test creating a valid list request."""
        req = ListRequest()
        assert req.type == "list"
    
    def test_list_request_to_json(self):
        """Test list request serialization to JSON."""
        req = ListRequest()
        json_str = req.to_json()
        assert isinstance(json_str, str)
        assert "list" in json_str
    
    def test_list_request_from_json(self):
        """Test list request deserialization from JSON."""
        json_str = '{"type": "list"}'
        req = ListRequest.from_json(json_str)
        assert req.type == "list"
    
    def test_list_request_validation(self):
        """Test list request validation."""
        req = ListRequest()
        errors = req.validate()
        assert len(errors) == 0


class TestRemoveRequest:
    """Tests for RemoveRequest message."""
    
    def test_create_remove_request(self):
        """Test creating a valid remove request."""
        req = RemoveRequest(tag="myapp:latest")
        assert req.type == "remove"
        assert req.tag == "myapp:latest"
    
    def test_remove_request_validation_success(self):
        """Test remove request validation with valid data."""
        req = RemoveRequest(tag="myapp:latest")
        errors = req.validate()
        assert len(errors) == 0
    
    def test_remove_request_validation_missing_tag(self):
        """Test remove request validation with missing tag."""
        req = RemoveRequest(tag="")
        errors = req.validate()
        assert len(errors) > 0
        assert any("tag" in err for err in errors)


class TestPurgeRequest:
    """Tests for PurgeRequest message."""
    
    def test_create_purge_request(self):
        """Test creating a valid purge request."""
        req = PurgeRequest(force=True)
        assert req.type == "purge"
        assert req.force is True
    
    def test_purge_request_validation(self):
        """Test purge request validation."""
        req = PurgeRequest()
        errors = req.validate()
        assert len(errors) == 0


class TestBuildResponse:
    """Tests for BuildResponse message."""
    
    def test_create_build_response_success(self):
        """Test creating a successful build response."""
        resp = BuildResponse(
            success=True,
            exit_code=0,
            image_digest="sha256:abc123"
        )
        assert resp.success is True
        assert resp.exit_code == 0
        assert resp.image_digest == "sha256:abc123"
    
    def test_create_build_response_failure(self):
        """Test creating a failed build response."""
        resp = BuildResponse(
            success=False,
            exit_code=1,
            error_message="Build failed"
        )
        assert resp.success is False
        assert resp.exit_code == 1
        assert resp.error_message == "Build failed"
    
    def test_build_response_validation_success(self):
        """Test build response validation with valid success data."""
        resp = BuildResponse(
            success=True,
            exit_code=0,
            image_digest="sha256:abc123"
        )
        errors = resp.validate()
        assert len(errors) == 0
    
    def test_build_response_validation_failure(self):
        """Test build response validation with valid failure data."""
        resp = BuildResponse(
            success=False,
            exit_code=1,
            error_message="Build failed"
        )
        errors = resp.validate()
        assert len(errors) == 0
    
    def test_build_response_validation_inconsistent(self):
        """Test build response validation with inconsistent data."""
        resp = BuildResponse(
            success=True,
            exit_code=1  # Inconsistent: success but non-zero exit code
        )
        errors = resp.validate()
        assert len(errors) > 0


class TestListResponse:
    """Tests for ListResponse message."""
    
    def test_create_list_response(self):
        """Test creating a list response."""
        images = [
            ImageInfo(
                tag="myapp:latest",
                digest="sha256:abc123",
                size=1024,
                created="2024-01-01T00:00:00Z"
            )
        ]
        resp = ListResponse(images=images)
        assert len(resp.images) == 1
        assert resp.images[0].tag == "myapp:latest"
    
    def test_list_response_validation(self):
        """Test list response validation."""
        resp = ListResponse(images=[])
        errors = resp.validate()
        assert len(errors) == 0


class TestRemoveResponse:
    """Tests for RemoveResponse message."""
    
    def test_create_remove_response_success(self):
        """Test creating a successful remove response."""
        resp = RemoveResponse(success=True)
        assert resp.success is True
    
    def test_create_remove_response_failure(self):
        """Test creating a failed remove response."""
        resp = RemoveResponse(
            success=False,
            error_message="Image not found"
        )
        assert resp.success is False
        assert resp.error_message == "Image not found"
    
    def test_remove_response_validation_failure_without_message(self):
        """Test remove response validation requires error message on failure."""
        resp = RemoveResponse(success=False)
        errors = resp.validate()
        assert len(errors) > 0
        assert any("error_message" in err for err in errors)


class TestPurgeResponse:
    """Tests for PurgeResponse message."""
    
    def test_create_purge_response_success(self):
        """Test creating a successful purge response."""
        resp = PurgeResponse(
            success=True,
            removed_count=5
        )
        assert resp.success is True
        assert resp.removed_count == 5
    
    def test_purge_response_validation_negative_count(self):
        """Test purge response validation with negative count."""
        resp = PurgeResponse(
            success=True,
            removed_count=-1
        )
        errors = resp.validate()
        assert len(errors) > 0
        assert any("removed_count" in err for err in errors)


class TestOutputMessage:
    """Tests for OutputMessage."""
    
    def test_create_output_message(self):
        """Test creating an output message."""
        msg = OutputMessage(
            type="output",
            content="Building image...",
            timestamp=1234567890.0
        )
        assert msg.type == "output"
        assert msg.content == "Building image..."
        assert msg.timestamp == 1234567890.0
    
    def test_output_message_validation_success(self):
        """Test output message validation with valid data."""
        msg = OutputMessage(
            type="output",
            content="Building image...",
            timestamp=1234567890.0
        )
        errors = msg.validate()
        assert len(errors) == 0
    
    def test_output_message_validation_invalid_type(self):
        """Test output message validation with invalid type."""
        msg = OutputMessage(
            type="invalid",
            content="Building image...",
            timestamp=1234567890.0
        )
        errors = msg.validate()
        assert len(errors) > 0
        assert any("type" in err for err in errors)


class TestDeserializeMessage:
    """Tests for deserialize_message function."""
    
    def test_deserialize_build_request(self):
        """Test deserializing a build request."""
        json_str = '{"type": "build", "context_path": "/path", "dockerfile_path": "/Dockerfile", "tag": "app:latest", "build_args": {}}'
        msg = deserialize_message(json_str)
        assert isinstance(msg, BuildRequest)
        assert msg.type == "build"
    
    def test_deserialize_list_request(self):
        """Test deserializing a list request."""
        json_str = '{"type": "list"}'
        msg = deserialize_message(json_str)
        assert isinstance(msg, ListRequest)
        assert msg.type == "list"
    
    def test_deserialize_unknown_type(self):
        """Test deserializing unknown message type."""
        json_str = '{"type": "unknown"}'
        with pytest.raises(ValueError, match="Unknown message type"):
            deserialize_message(json_str)
    
    def test_deserialize_missing_type(self):
        """Test deserializing message without type field."""
        json_str = '{"data": "value"}'
        with pytest.raises(ValueError, match="missing 'type' field"):
            deserialize_message(json_str)
    
    def test_deserialize_invalid_json(self):
        """Test deserializing invalid JSON."""
        json_str = 'not valid json'
        with pytest.raises(ValueError, match="Invalid JSON"):
            deserialize_message(json_str)


# Property-Based Tests

class TestPropertyBasedSerialization:
    """Property-based tests for message serialization.
    
    Feature: daemon-socket-support, Property 12: JSON request serialization
    Validates: Requirements 4.1
    """
    
    @given(
        context_path=st.text(min_size=1, max_size=200),
        dockerfile_path=st.text(min_size=1, max_size=200),
        tag=st.text(min_size=1, max_size=100),
        build_args=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.text(min_size=0, max_size=100),
            max_size=10
        )
    )
    def test_build_request_round_trip(self, context_path, dockerfile_path, tag, build_args):
        """
        Property 12: JSON request serialization
        For any valid build request, serializing then deserializing should produce
        an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create original request
        original = BuildRequest(
            context_path=context_path,
            dockerfile_path=dockerfile_path,
            tag=tag,
            build_args=build_args
        )
        
        # Serialize to JSON
        json_str = original.to_json()
        
        # Deserialize back
        deserialized = BuildRequest.from_json(json_str)
        
        # Verify equivalence
        assert deserialized.type == original.type
        assert deserialized.context_path == original.context_path
        assert deserialized.dockerfile_path == original.dockerfile_path
        assert deserialized.tag == original.tag
        assert deserialized.build_args == original.build_args
    
    @given(tag=st.text(min_size=1, max_size=100))
    def test_remove_request_round_trip(self, tag):
        """
        Property 12: JSON request serialization
        For any valid remove request, serializing then deserializing should produce
        an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create original request
        original = RemoveRequest(tag=tag)
        
        # Serialize to JSON
        json_str = original.to_json()
        
        # Deserialize back
        deserialized = RemoveRequest.from_json(json_str)
        
        # Verify equivalence
        assert deserialized.type == original.type
        assert deserialized.tag == original.tag
    
    @given(force=st.booleans())
    def test_purge_request_round_trip(self, force):
        """
        Property 12: JSON request serialization
        For any valid purge request, serializing then deserializing should produce
        an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create original request
        original = PurgeRequest(force=force)
        
        # Serialize to JSON
        json_str = original.to_json()
        
        # Deserialize back
        deserialized = PurgeRequest.from_json(json_str)
        
        # Verify equivalence
        assert deserialized.type == original.type
        assert deserialized.force == original.force
    
    def test_list_request_round_trip(self):
        """
        Property 12: JSON request serialization
        For any valid list request, serializing then deserializing should produce
        an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create original request
        original = ListRequest()
        
        # Serialize to JSON
        json_str = original.to_json()
        
        # Deserialize back
        deserialized = ListRequest.from_json(json_str)
        
        # Verify equivalence
        assert deserialized.type == original.type
    
    @given(
        success=st.booleans(),
        exit_code=st.integers(min_value=0, max_value=255),
        error_message=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        image_digest=st.one_of(st.none(), st.text(min_size=1, max_size=100))
    )
    def test_build_response_round_trip(self, success, exit_code, error_message, image_digest):
        """
        Property 12: JSON request serialization
        For any valid build response, serializing then deserializing should produce
        an equivalent response.
        
        Validates: Requirements 4.1
        """
        # Ensure consistency: success=True requires exit_code=0
        if success:
            exit_code = 0
        else:
            if exit_code == 0:
                exit_code = 1
            if not error_message:
                error_message = "Build failed"
        
        # Create original response
        original = BuildResponse(
            success=success,
            exit_code=exit_code,
            error_message=error_message,
            image_digest=image_digest
        )
        
        # Serialize to JSON
        json_str = original.to_json()
        
        # Deserialize back
        deserialized = BuildResponse.from_json(json_str)
        
        # Verify equivalence
        assert deserialized.success == original.success
        assert deserialized.exit_code == original.exit_code
        assert deserialized.error_message == original.error_message
        assert deserialized.image_digest == original.image_digest
    
    @given(
        msg_type=st.sampled_from(["output", "error", "progress"]),
        content=st.text(min_size=0, max_size=500),
        timestamp=st.floats(min_value=0, max_value=2000000000, allow_nan=False, allow_infinity=False)
    )
    def test_output_message_round_trip(self, msg_type, content, timestamp):
        """
        Property 12: JSON request serialization
        For any valid output message, serializing then deserializing should produce
        an equivalent message.
        
        Validates: Requirements 4.1
        """
        # Create original message
        original = OutputMessage(
            type=msg_type,
            content=content,
            timestamp=timestamp
        )
        
        # Serialize to JSON
        json_str = original.to_json()
        
        # Deserialize back
        deserialized = OutputMessage.from_json(json_str)
        
        # Verify equivalence
        assert deserialized.type == original.type
        assert deserialized.content == original.content
        assert abs(deserialized.timestamp - original.timestamp) < 0.001  # Float comparison


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
