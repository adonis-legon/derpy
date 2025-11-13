"""Tests for Dockerfile parser."""

import pytest
from pathlib import Path
import tempfile
from derpy.dockerfile.parser import DockerfileParser, InstructionType


class TestDockerfileParser:
    """Tests for DockerfileParser."""
    
    def test_parse_simple_dockerfile(self):
        """Test parsing a simple Dockerfile."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("RUN apt-get update\n")
            f.write("CMD [\"echo\", \"hello\"]\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) == 3
            assert dockerfile.instructions[0].type == InstructionType.FROM
            assert dockerfile.instructions[1].type == InstructionType.RUN
            assert dockerfile.instructions[2].type == InstructionType.CMD
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_with_comments(self):
        """Test parsing Dockerfile with comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("FROM ubuntu:20.04\n")
            f.write("# Another comment\n")
            f.write("RUN apt-get update\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Comments should be ignored
            assert len(dockerfile.instructions) == 2
            assert dockerfile.instructions[0].type == InstructionType.FROM
            assert dockerfile.instructions[1].type == InstructionType.RUN
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_with_empty_lines(self):
        """Test parsing Dockerfile with empty lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("\n")
            f.write("RUN apt-get update\n")
            f.write("\n\n")
            f.write("CMD [\"echo\", \"hello\"]\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Empty lines should be ignored
            assert len(dockerfile.instructions) == 3
        finally:
            dockerfile_path.unlink()
    
    def test_parse_from_instruction(self):
        """Test parsing FROM instruction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) == 1
            instruction = dockerfile.instructions[0]
            assert instruction.type == InstructionType.FROM
            assert "ubuntu:20.04" in instruction.value
        finally:
            dockerfile_path.unlink()
    
    def test_parse_run_instruction(self):
        """Test parsing RUN instruction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("RUN apt-get update && apt-get install -y curl\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) == 2
            run_instruction = dockerfile.instructions[1]
            assert run_instruction.type == InstructionType.RUN
            assert "apt-get" in run_instruction.value
        finally:
            dockerfile_path.unlink()
    
    def test_parse_cmd_instruction(self):
        """Test parsing CMD instruction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("CMD [\"echo\", \"hello world\"]\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) == 2
            cmd_instruction = dockerfile.instructions[1]
            assert cmd_instruction.type == InstructionType.CMD
        finally:
            dockerfile_path.unlink()
    
    def test_dockerfile_validation(self):
        """Test Dockerfile validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("RUN apt-get update\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert dockerfile.is_valid
            assert len(dockerfile.validation_errors) == 0
        finally:
            dockerfile_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestDockerfileValidation:
    """Tests for Dockerfile validation."""
    
    def test_dockerfile_with_multiple_from(self):
        """Test Dockerfile with multiple FROM instructions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("RUN apt-get update\n")
            f.write("FROM alpine:latest\n")
            f.write("RUN apk add curl\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Should have 4 instructions
            assert len(dockerfile.instructions) == 4
            # Two FROM instructions
            from_count = sum(1 for i in dockerfile.instructions if i.type == InstructionType.FROM)
            assert from_count == 2
        finally:
            dockerfile_path.unlink()
    
    def test_dockerfile_with_multiline_run(self):
        """Test Dockerfile with multiline RUN instruction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("RUN apt-get update && \\\n")
            f.write("    apt-get install -y curl && \\\n")
            f.write("    apt-get clean\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Should parse multiline as single instruction
            assert len(dockerfile.instructions) >= 2
        finally:
            dockerfile_path.unlink()
    
    def test_dockerfile_cmd_exec_form(self):
        """Test Dockerfile with CMD in exec form."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write('CMD ["echo", "hello", "world"]\n')
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) == 2
            cmd_instruction = dockerfile.instructions[1]
            assert cmd_instruction.type == InstructionType.CMD
            assert "[" in cmd_instruction.value
        finally:
            dockerfile_path.unlink()
    
    def test_dockerfile_with_tabs(self):
        """Test Dockerfile with tab characters."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM\tubuntu:20.04\n")
            f.write("RUN\tapt-get update\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Should handle tabs
            assert len(dockerfile.instructions) == 2
        finally:
            dockerfile_path.unlink()
    
    def test_dockerfile_case_insensitive(self):
        """Test that Dockerfile instructions are case-insensitive."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("from ubuntu:20.04\n")
            f.write("run apt-get update\n")
            f.write("cmd echo hello\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) == 3
            assert dockerfile.instructions[0].type == InstructionType.FROM
            assert dockerfile.instructions[1].type == InstructionType.RUN
            assert dockerfile.instructions[2].type == InstructionType.CMD
        finally:
            dockerfile_path.unlink()


class TestInstructionType:
    """Tests for InstructionType enum."""
    
    def test_instruction_type_values(self):
        """Test InstructionType enum values."""
        assert InstructionType.FROM.value == "FROM"
        assert InstructionType.RUN.value == "RUN"
        assert InstructionType.CMD.value == "CMD"
        assert InstructionType.UNSUPPORTED.value == "UNSUPPORTED"
    
    def test_instruction_type_members(self):
        """Test InstructionType has expected members."""
        members = [member.name for member in InstructionType]
        assert "FROM" in members
        assert "RUN" in members
        assert "CMD" in members
        assert "UNSUPPORTED" in members
