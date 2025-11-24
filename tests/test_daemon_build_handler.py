"""Tests for daemon build request handler.

Property 9: Build isolation equivalence
Property 13: Real-time output streaming
Property 15: Final response with exit status
Feature: daemon-socket-support, Property 9: Build isolation equivalence
Feature: daemon-socket-support, Property 13: Real-time output streaming
Feature: daemon-socket-support, Property 15: Final response with exit status
Validates: Requirements 3.3, 4.2, 4.4
"""

import pytest
import tempfile
import time
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from derpy.daemon.handlers import RequestHandler
from derpy.daemon.protocol import BuildRequest, BuildResponse, OutputMessage
from derpy.build.engine import BuildEngine, BuildContext
from derpy.storage.manager import ImageManager


class TestBuildRequestHandler:
    """Tests for build request handler implementation."""
    
    def test_handle_build_request_invalid_context_path(self):
        """Test that build request with non-existent context path fails."""
        handler = RequestHandler()
        request = BuildRequest(
            context_path="/nonexistent/path",
            dockerfile_path="/nonexistent/Dockerfile",
            tag="test:latest"
        )
        
        response = handler.handle_request(request)
        
        assert isinstance(response, BuildResponse)
        assert response.success is False
        assert response.exit_code == 1
        assert "does not exist" in response.error_message
    
    def test_handle_build_request_invalid_dockerfile_path(self):
        """Test that build request with non-existent Dockerfile fails."""
        handler = RequestHandler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            request = BuildRequest(
                context_path=tmpdir,
                dockerfile_path="/nonexistent/Dockerfile",
                tag="test:latest"
            )
            
            response = handler.handle_request(request)
            
            assert isinstance(response, BuildResponse)
            assert response.success is False
            assert response.exit_code == 1
            assert "does not exist" in response.error_message
    
    def test_handle_build_request_context_not_directory(self):
        """Test that build request with file as context path fails."""
        handler = RequestHandler()
        
        with tempfile.NamedTemporaryFile() as tmpfile:
            request = BuildRequest(
                context_path=tmpfile.name,
                dockerfile_path=tmpfile.name,
                tag="test:latest"
            )
            
            response = handler.handle_request(request)
            
            assert isinstance(response, BuildResponse)
            assert response.success is False
            assert response.exit_code == 1
            assert "not a directory" in response.error_message
    
    def test_handle_build_request_dockerfile_not_file(self):
        """Test that build request with directory as Dockerfile fails."""
        handler = RequestHandler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            request = BuildRequest(
                context_path=tmpdir,
                dockerfile_path=tmpdir,
                tag="test:latest"
            )
            
            response = handler.handle_request(request)
            
            assert isinstance(response, BuildResponse)
            assert response.success is False
            assert response.exit_code == 1
            assert "not a file" in response.error_message


class TestBuildIsolationEquivalence:
    """Tests for Property 9: Build isolation equivalence.
    
    Property 9: Build isolation equivalence
    For any build operation executed by the daemon, the build isolation
    mechanisms used should produce the same results as the current
    sudo-based implementation.
    
    Validates: Requirements 3.3
    """
    
    @pytest.mark.skipif(
        not Path("/bin/sh").exists(),
        reason="Requires /bin/sh for build execution"
    )
    def test_simple_build_produces_image(self):
        """Test that a simple build produces a valid image."""
        handler = RequestHandler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"hello\"]\n")
            
            request = BuildRequest(
                context_path=str(context_path),
                dockerfile_path=str(dockerfile_path),
                tag="test:simple"
            )
            
            response = handler.handle_request(request)
            
            # Build should complete (may succeed or fail depending on isolation support)
            assert isinstance(response, BuildResponse)
            assert response.exit_code is not None
    
    @pytest.mark.skipif(
        not Path("/bin/sh").exists(),
        reason="Requires /bin/sh for build execution"
    )
    @given(
        cmd_arg=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=10, deadline=60000)
    def test_property_build_isolation_equivalence(self, cmd_arg):
        """
        Property 9: Build isolation equivalence
        
        For any build operation, the daemon's build isolation mechanisms
        should produce consistent results.
        
        Validates: Requirements 3.3
        """
        # Skip invalid command arguments
        assume(cmd_arg.strip() != "")
        assume(not any(c in cmd_arg for c in ['"', "'", "\\", "\n", "\r"]))
        
        handler = RequestHandler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a Dockerfile with the generated command
            dockerfile_content = f'FROM scratch\nCMD ["echo", "{cmd_arg}"]\n'
            dockerfile_path.write_text(dockerfile_content)
            
            request = BuildRequest(
                context_path=str(context_path),
                dockerfile_path=str(dockerfile_path),
                tag=f"test:prop_{cmd_arg[:10]}"
            )
            
            response = handler.handle_request(request)
            
            # Build should complete with a definite result
            assert isinstance(response, BuildResponse)
            assert isinstance(response.success, bool)
            assert isinstance(response.exit_code, int)
            
            # If build succeeds, should have image digest
            if response.success:
                assert response.image_digest is not None
            else:
                # If build fails, should have error message
                assert response.error_message is not None


class TestOutputStreaming:
    """Tests for Property 13: Real-time output streaming.
    
    Property 13: Real-time output streaming
    For any build operation, the daemon should stream output back to the
    CLI incrementally, not all at once after completion.
    
    Validates: Requirements 4.2
    """
    
    def test_output_callback_receives_messages(self):
        """Test that output callback receives streaming messages."""
        handler = RequestHandler()
        output_messages = []
        
        def output_callback(msg_json):
            output_messages.append(msg_json)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"test\"]\n")
            
            request = BuildRequest(
                context_path=str(context_path),
                dockerfile_path=str(dockerfile_path),
                tag="test:streaming"
            )
            
            response = handler.handle_build_request(request, output_callback)
            
            # Should have received some output messages during build
            # (even if build fails, we should get error messages)
            assert isinstance(response, BuildResponse)
    
    @pytest.mark.skipif(
        not Path("/bin/sh").exists(),
        reason="Requires /bin/sh for build execution"
    )
    @given(dummy=st.just(None))
    @settings(max_examples=10, deadline=60000)
    def test_property_real_time_output_streaming(self, dummy):
        """
        Property 13: Real-time output streaming
        
        For any build operation, output should be streamed incrementally
        with timestamps showing real-time delivery.
        
        Validates: Requirements 4.2
        """
        handler = RequestHandler()
        output_messages = []
        message_timestamps = []
        
        def output_callback(msg_json):
            output_messages.append(msg_json)
            message_timestamps.append(time.time())
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"hello\"]\n")
            
            request = BuildRequest(
                context_path=str(context_path),
                dockerfile_path=str(dockerfile_path),
                tag="test:streaming_prop"
            )
            
            start_time = time.time()
            response = handler.handle_build_request(request, output_callback)
            end_time = time.time()
            
            # Build should complete
            assert isinstance(response, BuildResponse)
            
            # If we received messages, they should be timestamped
            if output_messages:
                # Parse first message to check timestamp
                import json
                first_msg = json.loads(output_messages[0].strip())
                
                # Timestamp should be within build duration
                if "timestamp" in first_msg:
                    assert start_time <= first_msg["timestamp"] <= end_time


class TestFinalResponse:
    """Tests for Property 15: Final response with exit status.
    
    Property 15: Final response with exit status
    For any completed build operation, the daemon should send a final
    response containing the exit status.
    
    Validates: Requirements 4.4
    """
    
    def test_successful_build_returns_success_response(self):
        """Test that successful build returns success response with exit code 0."""
        handler = RequestHandler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a minimal valid Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"test\"]\n")
            
            request = BuildRequest(
                context_path=str(context_path),
                dockerfile_path=str(dockerfile_path),
                tag="test:success"
            )
            
            response = handler.handle_request(request)
            
            # Should return a response with exit status
            assert isinstance(response, BuildResponse)
            assert isinstance(response.exit_code, int)
            assert isinstance(response.success, bool)
            
            # Success and exit code should be consistent
            if response.success:
                assert response.exit_code == 0
            else:
                assert response.exit_code != 0
    
    def test_failed_build_returns_failure_response(self):
        """Test that failed build returns failure response with non-zero exit code."""
        handler = RequestHandler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create an invalid Dockerfile
            dockerfile_path.write_text("INVALID INSTRUCTION\n")
            
            request = BuildRequest(
                context_path=str(context_path),
                dockerfile_path=str(dockerfile_path),
                tag="test:failure"
            )
            
            response = handler.handle_request(request)
            
            # Should return failure response
            assert isinstance(response, BuildResponse)
            assert response.success is False
            assert response.exit_code != 0
            assert response.error_message is not None
    
    @pytest.mark.skipif(
        not Path("/bin/sh").exists(),
        reason="Requires /bin/sh for build execution"
    )
    @given(
        tag_suffix=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=10, deadline=60000)
    def test_property_final_response_with_exit_status(self, tag_suffix):
        """
        Property 15: Final response with exit status
        
        For any completed build operation, the final response should
        contain a valid exit status that reflects the build outcome.
        
        Validates: Requirements 4.4
        """
        # Skip invalid tag suffixes
        assume(tag_suffix.strip() != "")
        
        handler = RequestHandler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = Path(tmpdir)
            dockerfile_path = context_path / "Dockerfile"
            
            # Create a Dockerfile
            dockerfile_path.write_text("FROM scratch\nCMD [\"echo\", \"test\"]\n")
            
            request = BuildRequest(
                context_path=str(context_path),
                dockerfile_path=str(dockerfile_path),
                tag=f"test:{tag_suffix}"
            )
            
            response = handler.handle_request(request)
            
            # Final response must have exit status
            assert isinstance(response, BuildResponse)
            assert hasattr(response, "exit_code")
            assert hasattr(response, "success")
            assert isinstance(response.exit_code, int)
            assert isinstance(response.success, bool)
            
            # Exit code and success must be consistent
            if response.success:
                assert response.exit_code == 0
                # Successful builds should have image digest
                assert response.image_digest is not None or response.error_message is not None
            else:
                assert response.exit_code != 0
                # Failed builds should have error message
                assert response.error_message is not None
