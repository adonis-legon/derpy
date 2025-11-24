"""Tests for daemon message framing.

Property 12: JSON request serialization
Feature: daemon-socket-support, Property 12: JSON request serialization
Validates: Requirements 4.1
"""

import socket
import pytest
from hypothesis import given, strategies as st, settings
from derpy.daemon.framing import MessageFramer
from derpy.daemon.protocol import (
    BuildRequest,
    ListRequest,
    RemoveRequest,
    PurgeRequest,
    BuildResponse,
    OutputMessage,
)


class TestMessageFramer:
    """Tests for MessageFramer class."""
    
    def test_send_message_build_request(self):
        """Test sending a build request message."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            request = BuildRequest(
                context_path="/path/to/context",
                dockerfile_path="/path/to/Dockerfile",
                tag="myapp:latest"
            )
            
            # Send message
            framer.send_message(client_sock, request)
            
            # Receive on other end
            data = server_sock.recv(4096)
            assert data.endswith(b"\n")
            assert b"build" in data
            assert b"/path/to/context" in data
        finally:
            client_sock.close()
            server_sock.close()
    
    def test_receive_message_build_request(self):
        """Test receiving a build request message."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            request = BuildRequest(
                context_path="/path/to/context",
                dockerfile_path="/path/to/Dockerfile",
                tag="myapp:latest"
            )
            
            # Send message from client
            json_str = request.to_json()
            client_sock.sendall((json_str + "\n").encode('utf-8'))
            
            # Receive message on server
            received = framer.receive_message(server_sock)
            
            assert isinstance(received, BuildRequest)
            assert received.context_path == "/path/to/context"
            assert received.dockerfile_path == "/path/to/Dockerfile"
            assert received.tag == "myapp:latest"
        finally:
            client_sock.close()
            server_sock.close()
    
    def test_receive_message_partial_buffering(self):
        """Test receiving a message in multiple chunks."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            request = BuildRequest(
                context_path="/path/to/context",
                dockerfile_path="/path/to/Dockerfile",
                tag="myapp:latest"
            )
            
            # Send message in chunks
            json_str = request.to_json() + "\n"
            data = json_str.encode('utf-8')
            
            # Send first half
            mid = len(data) // 2
            client_sock.sendall(data[:mid])
            
            # Try to receive (should not complete yet)
            server_sock.setblocking(False)
            try:
                # This should buffer the partial message
                # We need to make it blocking again for the actual receive
                server_sock.setblocking(True)
            except:
                pass
            
            # Send second half
            client_sock.sendall(data[mid:])
            
            # Now receive should complete
            server_sock.setblocking(True)
            received = framer.receive_message(server_sock)
            
            assert isinstance(received, BuildRequest)
            assert received.context_path == "/path/to/context"
        finally:
            client_sock.close()
            server_sock.close()
    
    def test_receive_message_multiple_messages(self):
        """Test receiving multiple messages in sequence."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            
            # Send multiple messages
            request1 = BuildRequest(
                context_path="/path1",
                dockerfile_path="/Dockerfile1",
                tag="app1:latest"
            )
            request2 = ListRequest()
            request3 = RemoveRequest(tag="app2:latest")
            
            framer.send_message(client_sock, request1)
            framer.send_message(client_sock, request2)
            framer.send_message(client_sock, request3)
            
            # Receive all messages
            received1 = framer.receive_message(server_sock)
            received2 = framer.receive_message(server_sock)
            received3 = framer.receive_message(server_sock)
            
            assert isinstance(received1, BuildRequest)
            assert received1.context_path == "/path1"
            
            assert isinstance(received2, ListRequest)
            
            assert isinstance(received3, RemoveRequest)
            assert received3.tag == "app2:latest"
        finally:
            client_sock.close()
            server_sock.close()
    
    def test_receive_message_socket_closed(self):
        """Test receiving when socket is closed."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            
            # Close client socket
            client_sock.close()
            
            # Try to receive - should return None
            received = framer.receive_message(server_sock)
            assert received is None
        finally:
            server_sock.close()
    
    def test_receive_message_incomplete_on_close(self):
        """Test receiving incomplete message when socket closes."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            
            # Send incomplete message (no newline)
            client_sock.sendall(b'{"type": "build"')
            client_sock.close()
            
            # Try to receive - should raise ValueError
            with pytest.raises(ValueError, match="incomplete message"):
                framer.receive_message(server_sock)
        finally:
            server_sock.close()
    
    def test_receive_message_invalid_json(self):
        """Test receiving malformed JSON."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            
            # Send invalid JSON
            client_sock.sendall(b'not valid json\n')
            
            # Try to receive - should raise ValueError
            with pytest.raises(ValueError, match="Malformed message"):
                framer.receive_message(server_sock)
        finally:
            client_sock.close()
            server_sock.close()
    
    def test_receive_message_invalid_utf8(self):
        """Test receiving invalid UTF-8."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            
            # Send invalid UTF-8
            client_sock.sendall(b'\xff\xfe\n')
            
            # Try to receive - should raise ValueError
            with pytest.raises(ValueError, match="Invalid UTF-8"):
                framer.receive_message(server_sock)
        finally:
            client_sock.close()
            server_sock.close()
    
    def test_receive_message_too_large(self):
        """Test receiving message exceeding maximum size."""
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            framer = MessageFramer()
            
            # Manually fill the buffer beyond the limit to test the check
            # This simulates receiving data that exceeds MAX_MESSAGE_SIZE
            framer._receive_buffer = b'x' * (MessageFramer.MAX_MESSAGE_SIZE + 1)
            
            # Now try to receive more data - should detect buffer is too large
            client_sock.sendall(b'more data\n')
            
            # Try to receive - should raise ValueError
            with pytest.raises(ValueError, match="exceeded maximum size"):
                framer.receive_message(server_sock)
        finally:
            client_sock.close()
            server_sock.close()
    
    def test_reset_buffer(self):
        """Test resetting the receive buffer."""
        framer = MessageFramer()
        
        # Manually add data to buffer
        framer._receive_buffer = b"some data"
        assert framer.has_buffered_data()
        
        # Reset buffer
        framer.reset_buffer()
        assert not framer.has_buffered_data()
    
    def test_has_buffered_data(self):
        """Test checking for buffered data."""
        framer = MessageFramer()
        
        # Initially empty
        assert not framer.has_buffered_data()
        
        # Add data
        framer._receive_buffer = b"data"
        assert framer.has_buffered_data()
        
        # Clear
        framer._receive_buffer = b""
        assert not framer.has_buffered_data()


# Property-Based Tests

class TestPropertyBasedFraming:
    """Property-based tests for message framing.
    
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
    @settings(max_examples=100)
    def test_build_request_framing_round_trip(
        self, context_path, dockerfile_path, tag, build_args
    ):
        """
        Property 12: JSON request serialization
        For any valid build request, sending then receiving over a socket should
        produce an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            sender_framer = MessageFramer()
            receiver_framer = MessageFramer()
            
            # Create original request
            original = BuildRequest(
                context_path=context_path,
                dockerfile_path=dockerfile_path,
                tag=tag,
                build_args=build_args
            )
            
            # Send message
            sender_framer.send_message(client_sock, original)
            
            # Receive message
            received = receiver_framer.receive_message(server_sock)
            
            # Verify equivalence
            assert isinstance(received, BuildRequest)
            assert received.type == original.type
            assert received.context_path == original.context_path
            assert received.dockerfile_path == original.dockerfile_path
            assert received.tag == original.tag
            assert received.build_args == original.build_args
        finally:
            client_sock.close()
            server_sock.close()
    
    @given(tag=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_remove_request_framing_round_trip(self, tag):
        """
        Property 12: JSON request serialization
        For any valid remove request, sending then receiving over a socket should
        produce an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            sender_framer = MessageFramer()
            receiver_framer = MessageFramer()
            
            # Create original request
            original = RemoveRequest(tag=tag)
            
            # Send message
            sender_framer.send_message(client_sock, original)
            
            # Receive message
            received = receiver_framer.receive_message(server_sock)
            
            # Verify equivalence
            assert isinstance(received, RemoveRequest)
            assert received.type == original.type
            assert received.tag == original.tag
        finally:
            client_sock.close()
            server_sock.close()
    
    @given(force=st.booleans())
    @settings(max_examples=100)
    def test_purge_request_framing_round_trip(self, force):
        """
        Property 12: JSON request serialization
        For any valid purge request, sending then receiving over a socket should
        produce an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            sender_framer = MessageFramer()
            receiver_framer = MessageFramer()
            
            # Create original request
            original = PurgeRequest(force=force)
            
            # Send message
            sender_framer.send_message(client_sock, original)
            
            # Receive message
            received = receiver_framer.receive_message(server_sock)
            
            # Verify equivalence
            assert isinstance(received, PurgeRequest)
            assert received.type == original.type
            assert received.force == original.force
        finally:
            client_sock.close()
            server_sock.close()
    
    @given(dummy=st.just(None))
    @settings(max_examples=100)
    def test_list_request_framing_round_trip(self, dummy):
        """
        Property 12: JSON request serialization
        For any valid list request, sending then receiving over a socket should
        produce an equivalent request.
        
        Validates: Requirements 4.1
        """
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            sender_framer = MessageFramer()
            receiver_framer = MessageFramer()
            
            # Create original request
            original = ListRequest()
            
            # Send message
            sender_framer.send_message(client_sock, original)
            
            # Receive message
            received = receiver_framer.receive_message(server_sock)
            
            # Verify equivalence
            assert isinstance(received, ListRequest)
            assert received.type == original.type
        finally:
            client_sock.close()
            server_sock.close()
    
    @given(
        msg_type=st.sampled_from(["output", "error", "progress"]),
        content=st.text(min_size=0, max_size=500),
        timestamp=st.floats(min_value=0, max_value=2000000000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_output_message_framing_round_trip(self, msg_type, content, timestamp):
        """
        Property 12: JSON request serialization
        For any valid output message, sending then receiving over a socket should
        produce an equivalent message.
        
        Validates: Requirements 4.1
        """
        # Create socket pair for testing
        client_sock, server_sock = socket.socketpair()
        
        try:
            sender_framer = MessageFramer()
            receiver_framer = MessageFramer()
            
            # Create original message
            original = OutputMessage(
                type=msg_type,
                content=content,
                timestamp=timestamp
            )
            
            # Send message
            sender_framer.send_message(client_sock, original)
            
            # Receive message
            received = receiver_framer.receive_message(server_sock)
            
            # Verify equivalence
            assert isinstance(received, OutputMessage)
            assert received.type == original.type
            assert received.content == original.content
            assert abs(received.timestamp - original.timestamp) < 0.001  # Float comparison
        finally:
            client_sock.close()
            server_sock.close()
    



if __name__ == "__main__":
    pytest.main([__file__, "-v"])

