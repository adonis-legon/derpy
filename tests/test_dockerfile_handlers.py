"""Tests for Dockerfile instruction handlers."""

import pytest
from derpy.dockerfile.handlers import (
    InstructionHandler,
    FromHandler,
    RunHandler,
    CmdHandler,
    FromInstruction,
    RunInstruction,
    CmdInstruction
)
from derpy.dockerfile.parser import InstructionType, Instruction


class TestInstructionHandler:
    """Tests for base InstructionHandler."""
    
    def test_instruction_handler_is_abstract(self):
        """Test that InstructionHandler is abstract."""
        # Should have process method
        assert hasattr(InstructionHandler, 'process')
    
    def test_instruction_handler_has_validate(self):
        """Test that InstructionHandler has validate method."""
        assert hasattr(InstructionHandler, 'validate')


class TestFromHandler:
    """Tests for FROM instruction handler."""
    
    def test_from_handler_exists(self):
        """Test FromHandler class exists."""
        assert FromHandler is not None
    
    def test_from_handler_has_process_method(self):
        """Test FromHandler has process method."""
        handler = FromHandler()
        assert hasattr(handler, 'process')
        assert callable(getattr(handler, 'process', None))
    
    def test_from_handler_has_validate_method(self):
        """Test FromHandler has validate method."""
        handler = FromHandler()
        assert hasattr(handler, 'validate')
        assert callable(getattr(handler, 'validate', None))


class TestRunHandler:
    """Tests for RUN instruction handler."""
    
    def test_run_handler_exists(self):
        """Test RunHandler class exists."""
        assert RunHandler is not None
    
    def test_run_handler_has_process_method(self):
        """Test RunHandler has process method."""
        handler = RunHandler()
        assert hasattr(handler, 'process')
        assert callable(getattr(handler, 'process', None))
    
    def test_run_handler_has_validate_method(self):
        """Test RunHandler has validate method."""
        handler = RunHandler()
        assert hasattr(handler, 'validate')
        assert callable(getattr(handler, 'validate', None))


class TestCmdHandler:
    """Tests for CMD instruction handler."""
    
    def test_cmd_handler_exists(self):
        """Test CmdHandler class exists."""
        assert CmdHandler is not None
    
    def test_cmd_handler_has_process_method(self):
        """Test CmdHandler has process method."""
        handler = CmdHandler()
        assert hasattr(handler, 'process')
        assert callable(getattr(handler, 'process', None))
    
    def test_cmd_handler_has_validate_method(self):
        """Test CmdHandler has validate method."""
        handler = CmdHandler()
        assert hasattr(handler, 'validate')
        assert callable(getattr(handler, 'validate', None))


class TestFromInstructionProcessing:
    """Tests for FROM instruction processing."""
    
    def test_process_simple_from(self):
        """Test processing simple FROM instruction."""
        handler = FromHandler()
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu:20.04",
            line_number=1,
            raw_line="FROM ubuntu:20.04"
        )
        result = handler.process(instruction)
        
        assert isinstance(result, FromInstruction)
        assert result.image == "ubuntu"
        assert result.tag == "20.04"
    
    def test_process_from_with_digest(self):
        """Test processing FROM with digest."""
        handler = FromHandler()
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu@sha256:abc123",
            line_number=1,
            raw_line="FROM ubuntu@sha256:abc123"
        )
        result = handler.process(instruction)
        
        assert result.image == "ubuntu"
        assert result.digest == "sha256:abc123"
    
    def test_validate_from_empty(self):
        """Test validating empty FROM instruction."""
        handler = FromHandler()
        instruction = Instruction(
            type=InstructionType.FROM,
            value="",
            line_number=1,
            raw_line="FROM"
        )
        errors = handler.validate(instruction)
        
        assert len(errors) > 0


class TestRunInstructionProcessing:
    """Tests for RUN instruction processing."""
    
    def test_process_simple_run(self):
        """Test processing simple RUN instruction."""
        handler = RunHandler()
        instruction = Instruction(
            type=InstructionType.RUN,
            value="apt-get update",
            line_number=2,
            raw_line="RUN apt-get update"
        )
        result = handler.process(instruction)
        
        assert isinstance(result, RunInstruction)
        assert result.command == "apt-get update"
        assert result.is_shell_form is True
    
    def test_validate_run_empty(self):
        """Test validating empty RUN instruction."""
        handler = RunHandler()
        instruction = Instruction(
            type=InstructionType.RUN,
            value="",
            line_number=2,
            raw_line="RUN"
        )
        errors = handler.validate(instruction)
        
        assert len(errors) > 0


class TestCmdInstructionProcessing:
    """Tests for CMD instruction processing."""
    
    def test_process_simple_cmd(self):
        """Test processing simple CMD instruction."""
        handler = CmdHandler()
        instruction = Instruction(
            type=InstructionType.CMD,
            value="echo hello",
            line_number=3,
            raw_line="CMD echo hello"
        )
        result = handler.process(instruction)
        
        assert isinstance(result, CmdInstruction)
        assert result.command == "echo hello"
        assert result.is_shell_form is True
    
    def test_validate_cmd_empty(self):
        """Test validating empty CMD instruction."""
        handler = CmdHandler()
        instruction = Instruction(
            type=InstructionType.CMD,
            value="",
            line_number=3,
            raw_line="CMD"
        )
        errors = handler.validate(instruction)
        
        assert len(errors) > 0


class TestInstructionDataClasses:
    """Tests for instruction data classes."""
    
    def test_from_instruction_str(self):
        """Test FromInstruction string representation."""
        from_inst = FromInstruction(image="ubuntu", tag="20.04")
        assert "ubuntu" in str(from_inst)
        assert "20.04" in str(from_inst)
    
    def test_run_instruction_str(self):
        """Test RunInstruction string representation."""
        run_inst = RunInstruction(command="apt-get update")
        assert "RUN" in str(run_inst)
        assert "apt-get update" in str(run_inst)
    
    def test_cmd_instruction_str(self):
        """Test CmdInstruction string representation."""
        cmd_inst = CmdInstruction(command="echo hello")
        assert "CMD" in str(cmd_inst)
        assert "echo hello" in str(cmd_inst)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
