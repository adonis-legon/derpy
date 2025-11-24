"""Tests for daemon request handlers.

Property 7: Request format validation
Property 10: Invalid request rejection
Feature: daemon-socket-support, Property 7: Request format validation
Feature: daemon-socket-support, Property 10: Invalid request rejection
Validates: Requirements 3.1, 3.4
"""

import pytest
from hypothesis import given, strategies as st, settings
from derpy.daemon.handlers import RequestHandler
from derpy.daemon.protocol import (
    BuildRequest,
    BuildResponse,
    ListRequest,
    ListResponse,
    RemoveRequest,
    RemoveResponse,
    PurgeRequest,
    PurgeResponse,
)


class TestRequestHandler:
    """Tests for RequestHandler class."""
    
    def test_create_request_handler(self):
        """Test creating a request handler."""
        handler = RequestHandler()
        assert handler is not None
    
    def test_handle_build_request_stub(self):
        """Test handling a build request (stub implementation)."""
        handler = RequestHandler()
        request = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="/path/to/Dockerfile",
            tag="myapp:latest"
        )
        response = handler.handle_request(request)
        
        assert isinstance(response, BuildResponse)
        # Stub returns failure
        assert response.success is False
        assert response.error_message is not None
    
    def test_handle_list_request(self):
        """Test handling a list request."""
        handler = RequestHandler()
        request = ListRequest()
        response = handler.handle_request(request)
        
        assert isinstance(response, ListResponse)
        # Returns list of images (may be empty if no images stored)
        assert isinstance(response.images, list)
    
    def test_handle_remove_request(self):
        """Test handling a remove request."""
        handler = RequestHandler()
        request = RemoveRequest(tag="nonexistent:latest")
        response = handler.handle_request(request)
        
        assert isinstance(response, RemoveResponse)
        # Returns failure for nonexistent image
        assert response.success is False
        assert response.error_message is not None
        assert "not found" in response.error_message.lower()
    
    def test_handle_purge_request(self):
        """Test handling a purge request."""
        handler = RequestHandler()
        request = PurgeRequest(force=True)
        response = handler.handle_request(request)
        
        assert isinstance(response, PurgeResponse)
        # Returns success with count of removed images (may be 0)
        assert response.success is True
        assert response.removed_count >= 0
    
    def test_handle_request_unknown_type(self):
        """Test handling a request with unknown type."""
        handler = RequestHandler()
        
        # Create a mock request with unknown type
        class UnknownRequest:
            type = "unknown"
            
            def validate(self):
                return []
        
        request = UnknownRequest()
        
        with pytest.raises(ValueError, match="Unknown request type"):
            handler.handle_request(request)
    
    def test_handle_request_missing_type(self):
        """Test handling a request without type field."""
        handler = RequestHandler()
        
        # Create a mock request without type
        class NoTypeRequest:
            pass
        
        request = NoTypeRequest()
        
        with pytest.raises(ValueError, match="missing 'type' field"):
            handler.handle_request(request)


class TestRequestValidation:
    """Tests for request validation.
    
    Property 7: Request format validation
    For any request received by the daemon, the request format should be
    validated before processing.
    
    Property 10: Invalid request rejection
    For any invalid request, the daemon should reject it and return a
    descriptive error message.
    """
    
    def test_invalid_build_request_missing_context(self):
        """Test that build request with missing context_path is rejected."""
        handler = RequestHandler()
        request = BuildRequest(
            context_path="",  # Invalid: empty
            dockerfile_path="/path/to/Dockerfile",
            tag="myapp:latest"
        )
        
        response = handler.handle_request(request)
        
        assert isinstance(response, BuildResponse)
        assert response.success is False
        assert response.error_message is not None
        assert "context_path" in response.error_message
    
    def test_invalid_build_request_missing_dockerfile(self):
        """Test that build request with missing dockerfile_path is rejected."""
        handler = RequestHandler()
        request = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="",  # Invalid: empty
            tag="myapp:latest"
        )
        
        response = handler.handle_request(request)
        
        assert isinstance(response, BuildResponse)
        assert response.success is False
        assert response.error_message is not None
        assert "dockerfile_path" in response.error_message
    
    def test_invalid_build_request_missing_tag(self):
        """Test that build request with missing tag is rejected."""
        handler = RequestHandler()
        request = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="/path/to/Dockerfile",
            tag=""  # Invalid: empty
        )
        
        response = handler.handle_request(request)
        
        assert isinstance(response, BuildResponse)
        assert response.success is False
        assert response.error_message is not None
        assert "tag" in response.error_message
    
    def test_invalid_remove_request_missing_tag(self):
        """Test that remove request with missing tag is rejected."""
        handler = RequestHandler()
        request = RemoveRequest(tag="")  # Invalid: empty
        
        response = handler.handle_request(request)
        
        assert isinstance(response, RemoveResponse)
        assert response.success is False
        assert response.error_message is not None
        assert "tag" in response.error_message
    
    def test_valid_build_request_accepted(self):
        """Test that valid build request is accepted and processed."""
        handler = RequestHandler()
        request = BuildRequest(
            context_path="/path/to/context",
            dockerfile_path="/path/to/Dockerfile",
            tag="myapp:latest"
        )
        
        response = handler.handle_request(request)
        
        # Should not fail validation (stub will fail for other reasons)
        assert isinstance(response, BuildResponse)
        # Error message should not mention validation
        if response.error_message:
            assert "Invalid request" not in response.error_message
    
    def test_valid_list_request_accepted(self):
        """Test that valid list request is accepted and processed."""
        handler = RequestHandler()
        request = ListRequest()
        
        response = handler.handle_request(request)
        
        assert isinstance(response, ListResponse)
    
    def test_valid_remove_request_accepted(self):
        """Test that valid remove request is accepted and processed."""
        handler = RequestHandler()
        request = RemoveRequest(tag="myapp:latest")
        
        response = handler.handle_request(request)
        
        # Should not fail validation (stub will fail for other reasons)
        assert isinstance(response, RemoveResponse)
    
    def test_valid_purge_request_accepted(self):
        """Test that valid purge request is accepted and processed."""
        handler = RequestHandler()
        request = PurgeRequest(force=True)
        
        response = handler.handle_request(request)
        
        # Should not fail validation (stub will fail for other reasons)
        assert isinstance(response, PurgeResponse)
    
    @given(
        context_path=st.text(min_size=1, max_size=200),
        dockerfile_path=st.text(min_size=1, max_size=200),
        tag=st.text(min_size=1, max_size=128)
    )
    @settings(max_examples=100)
    def test_property_valid_build_requests_accepted(
        self, context_path, dockerfile_path, tag
    ):
        """
        Property 7: Request format validation
        
        For any valid build request (with non-empty required fields),
        the request should pass validation and be processed.
        
        Validates: Requirements 3.1
        """
        handler = RequestHandler()
        request = BuildRequest(
            context_path=context_path,
            dockerfile_path=dockerfile_path,
            tag=tag
        )
        
        # Should not raise validation error
        response = handler.handle_request(request)
        
        assert isinstance(response, BuildResponse)
        # If there's an error, it should not be a validation error
        if response.error_message:
            assert "Invalid request" not in response.error_message
    
    @given(tag=st.text(min_size=1, max_size=128))
    @settings(max_examples=100)
    def test_property_valid_remove_requests_accepted(self, tag):
        """
        Property 7: Request format validation
        
        For any valid remove request (with non-empty tag),
        the request should pass validation and be processed.
        
        Validates: Requirements 3.1
        """
        handler = RequestHandler()
        request = RemoveRequest(tag=tag)
        
        # Should not raise validation error
        response = handler.handle_request(request)
        
        assert isinstance(response, RemoveResponse)
        # If there's an error, it should not be a validation error
        if response.error_message:
            assert "Invalid request" not in response.error_message
    
    @given(force=st.booleans())
    @settings(max_examples=100)
    def test_property_valid_purge_requests_accepted(self, force):
        """
        Property 7: Request format validation
        
        For any valid purge request, the request should pass validation
        and be processed.
        
        Validates: Requirements 3.1
        """
        handler = RequestHandler()
        request = PurgeRequest(force=force)
        
        # Should not raise validation error
        response = handler.handle_request(request)
        
        assert isinstance(response, PurgeResponse)
        # If there's an error, it should not be a validation error
        if response.error_message:
            assert "Invalid request" not in response.error_message
    
    @given(dummy=st.just(None))
    @settings(max_examples=100)
    def test_property_valid_list_requests_accepted(self, dummy):
        """
        Property 7: Request format validation
        
        For any valid list request, the request should pass validation
        and be processed.
        
        Validates: Requirements 3.1
        """
        handler = RequestHandler()
        request = ListRequest()
        
        # Should not raise validation error
        response = handler.handle_request(request)
        
        assert isinstance(response, ListResponse)
    
    @given(
        missing_field=st.sampled_from(["context_path", "dockerfile_path", "tag"])
    )
    @settings(max_examples=100)
    def test_property_invalid_build_requests_rejected(self, missing_field):
        """
        Property 10: Invalid request rejection
        
        For any build request with a missing required field, the daemon
        should reject it and return a descriptive error message.
        
        Validates: Requirements 3.4
        """
        handler = RequestHandler()
        
        # Create request with one field empty
        fields = {
            "context_path": "/path/to/context",
            "dockerfile_path": "/path/to/Dockerfile",
            "tag": "myapp:latest"
        }
        fields[missing_field] = ""  # Make this field invalid
        
        request = BuildRequest(**fields)
        response = handler.handle_request(request)
        
        # Should return error response
        assert isinstance(response, BuildResponse)
        assert response.success is False
        assert response.error_message is not None
        # Error message should mention the missing field
        assert missing_field in response.error_message
    
    @given(dummy=st.just(None))
    @settings(max_examples=100)
    def test_property_invalid_remove_requests_rejected(self, dummy):
        """
        Property 10: Invalid request rejection
        
        For any remove request with missing tag, the daemon should
        reject it and return a descriptive error message.
        
        Validates: Requirements 3.4
        """
        handler = RequestHandler()
        request = RemoveRequest(tag="")  # Invalid: empty tag
        
        response = handler.handle_request(request)
        
        # Should return error response
        assert isinstance(response, RemoveResponse)
        assert response.success is False
        assert response.error_message is not None
        # Error message should mention the missing tag
        assert "tag" in response.error_message
    
    @given(
        wrong_type=st.sampled_from(["invalid", "unknown", "bad_type", ""])
    )
    @settings(max_examples=100)
    def test_property_wrong_type_requests_rejected(self, wrong_type):
        """
        Property 10: Invalid request rejection
        
        For any request with an invalid/unknown type field, the daemon should
        reject it and raise a descriptive error.
        
        Validates: Requirements 3.4
        """
        handler = RequestHandler()
        
        # Create a mock request with invalid type
        class InvalidTypeRequest:
            def __init__(self, req_type):
                self.type = req_type
            
            def validate(self):
                return []
        
        request = InvalidTypeRequest(wrong_type)
        
        # Should raise ValueError for unknown type
        with pytest.raises(ValueError, match="Unknown request type"):
            handler.handle_request(request)
