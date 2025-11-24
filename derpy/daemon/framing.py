"""Message framing for socket communication.

This module implements newline-delimited message framing for sending and
receiving JSON messages over Unix domain sockets. It handles partial message
buffering and provides error handling for malformed messages.
"""

import socket
from typing import Optional
from derpy.daemon.protocol import BaseMessage, deserialize_message


class MessageFramer:
    """Handles message framing over Unix domain sockets.
    
    Messages are framed using newline delimiters. Each message is a single
    line of JSON terminated with '\n'. The framer handles partial message
    buffering when receiving data.
    """
    
    # Maximum message size (1MB) to prevent memory exhaustion
    MAX_MESSAGE_SIZE = 1024 * 1024
    
    # Buffer size for socket reads
    BUFFER_SIZE = 4096
    
    def __init__(self):
        """Initialize message framer with empty receive buffer."""
        self._receive_buffer = b""
    
    @staticmethod
    def send_message(sock: socket.socket, message: BaseMessage) -> None:
        """Send a message over socket.
        
        Serializes the message to JSON and sends it with newline delimiter.
        
        Args:
            sock: Socket to send message on
            message: Message to send
            
        Raises:
            OSError: If socket send fails
            ValueError: If message serialization fails
        """
        try:
            json_str = message.to_json()
        except Exception as e:
            raise ValueError(f"Failed to serialize message: {e}")
        
        # Add newline delimiter
        data = (json_str + "\n").encode('utf-8')
        
        # Send all data
        try:
            sock.sendall(data)
        except OSError as e:
            raise OSError(f"Failed to send message: {e}")
    
    @staticmethod
    def send_message_raw(sock: socket.socket, message: str) -> None:
        """Send a raw string message over socket.
        
        Sends the message as-is (should already include newline if needed).
        Used for streaming output messages that are already serialized.
        
        Args:
            sock: Socket to send message on
            message: Raw message string to send (should include newline)
            
        Raises:
            OSError: If socket send fails
        """
        try:
            sock.sendall(message.encode('utf-8'))
        except OSError as e:
            raise OSError(f"Failed to send raw message: {e}")
    
    def receive_message(self, sock: socket.socket) -> Optional[BaseMessage]:
        """Receive a message from socket.
        
        Reads data from socket until a complete newline-delimited message
        is received. Handles partial message buffering across multiple reads.
        
        Args:
            sock: Socket to receive message from
            
        Returns:
            Deserialized message, or None if socket closed
            
        Raises:
            OSError: If socket receive fails
            ValueError: If message is malformed or too large
        """
        while True:
            # Check if we have a complete message in buffer
            if b"\n" in self._receive_buffer:
                # Extract message up to newline
                message_bytes, self._receive_buffer = self._receive_buffer.split(b"\n", 1)
                
                # Check message size
                if len(message_bytes) > self.MAX_MESSAGE_SIZE:
                    raise ValueError(
                        f"Message too large: {len(message_bytes)} bytes "
                        f"(max {self.MAX_MESSAGE_SIZE})"
                    )
                
                # Decode and deserialize
                try:
                    json_str = message_bytes.decode('utf-8')
                except UnicodeDecodeError as e:
                    raise ValueError(f"Invalid UTF-8 in message: {e}")
                
                try:
                    return deserialize_message(json_str)
                except ValueError as e:
                    raise ValueError(f"Malformed message: {e}")
            
            # Need more data - read from socket
            try:
                chunk = sock.recv(self.BUFFER_SIZE)
            except socket.timeout:
                # Re-raise timeout errors without wrapping
                raise
            except OSError as e:
                raise OSError(f"Failed to receive data: {e}")
            
            # Socket closed
            if not chunk:
                # If buffer has data, it's an incomplete message
                if self._receive_buffer:
                    raise ValueError("Socket closed with incomplete message")
                return None
            
            # Add to buffer
            self._receive_buffer += chunk
            
            # Check total buffer size
            if len(self._receive_buffer) > self.MAX_MESSAGE_SIZE:
                raise ValueError(
                    f"Message buffer exceeded maximum size: {self.MAX_MESSAGE_SIZE} bytes"
                )
    
    def reset_buffer(self) -> None:
        """Reset the receive buffer.
        
        Useful when starting a new connection or recovering from errors.
        """
        self._receive_buffer = b""
    
    def has_buffered_data(self) -> bool:
        """Check if there is data in the receive buffer.
        
        Returns:
            True if buffer contains data, False otherwise
        """
        return len(self._receive_buffer) > 0
