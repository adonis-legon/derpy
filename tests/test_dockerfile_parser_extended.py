"""Extended tests for Dockerfile parser."""

import pytest
from pathlib import Path
import tempfile
from derpy.dockerfile.parser import (
    DockerfileParser,
    InstructionType,
    Dockerfile,
    Instruction
)


class TestDockerfileParserEdgeCases:
    """Tests for Dockerfile parser edge cases."""
    
    def test_parse_dockerfile_with_multiline_run(self):
        """Test parsing Dockerfile with multiline RUN."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("RUN apt-get update && \\\n")
            f.write("    apt-get install -y curl\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Should handle multiline instructions
            assert len(dockerfile.instructions) >= 2
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_with_tabs(self):
        """Test parsing Dockerfile with tabs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM\tubuntu:20.04\n")
            f.write("RUN\tapt-get update\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) == 2
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_with_inline_comments(self):
        """Test parsing Dockerfile with inline comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04  # Base image\n")
            f.write("RUN apt-get update  # Update packages\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Should parse instructions, comments may be stripped
            assert len(dockerfile.instructions) >= 2
        finally:
            dockerfile_path.unlink()
    
    def test_parse_empty_dockerfile(self):
        """Test parsing empty Dockerfile."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Empty dockerfile should have no instructions
            assert len(dockerfile.instructions) == 0
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_only_comments(self):
        """Test parsing Dockerfile with only comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("# Another comment\n")
            f.write("# Yet another comment\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Only comments, no instructions
            assert len(dockerfile.instructions) == 0
        finally:
            dockerfile_path.unlink()


class TestInstructionTypeEnum:
    """Tests for InstructionType enum."""
    
    def test_instruction_type_from(self):
        """Test FROM instruction type."""
        assert InstructionType.FROM.value == "FROM"
    
    def test_instruction_type_run(self):
        """Test RUN instruction type."""
        assert InstructionType.RUN.value == "RUN"
    
    def test_instruction_type_cmd(self):
        """Test CMD instruction type."""
        assert InstructionType.CMD.value == "CMD"
    
    def test_instruction_type_unsupported(self):
        """Test UNSUPPORTED instruction type."""
        assert InstructionType.UNSUPPORTED.value == "UNSUPPORTED"


class TestDockerfileModel:
    """Tests for Dockerfile model."""
    
    def test_dockerfile_has_instructions(self):
        """Test Dockerfile has instructions attribute."""
        dockerfile = Dockerfile(instructions=[], validation_errors=[], path=Path("/tmp/Dockerfile"))
        assert hasattr(dockerfile, 'instructions')
        assert isinstance(dockerfile.instructions, list)
    
    def test_dockerfile_has_path(self):
        """Test Dockerfile has path attribute."""
        dockerfile = Dockerfile(instructions=[], validation_errors=[], path=Path("/tmp/Dockerfile"))
        assert hasattr(dockerfile, 'path')
        assert isinstance(dockerfile.path, Path)
    
    def test_dockerfile_is_valid_attribute(self):
        """Test Dockerfile has is_valid attribute."""
        dockerfile = Dockerfile(instructions=[], validation_errors=[], path=Path("/tmp/Dockerfile"))
        assert hasattr(dockerfile, 'is_valid')
        assert dockerfile.is_valid is True
    
    def test_dockerfile_validation_errors_attribute(self):
        """Test Dockerfile has validation_errors attribute."""
        dockerfile = Dockerfile(instructions=[], validation_errors=[], path=Path("/tmp/Dockerfile"))
        assert hasattr(dockerfile, 'validation_errors')
        assert isinstance(dockerfile.validation_errors, list)
    
    def test_dockerfile_is_valid_with_errors(self):
        """Test Dockerfile is_valid with validation errors."""
        from derpy.dockerfile.parser import ValidationError
        error = ValidationError(line_number=1, message="Test error", raw_line="TEST")
        dockerfile = Dockerfile(instructions=[], validation_errors=[error], path=Path("/tmp/Dockerfile"))
        assert dockerfile.is_valid is False


class TestInstructionModel:
    """Tests for Instruction model."""
    
    def test_instruction_has_type(self):
        """Test Instruction has type attribute."""
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu:20.04",
            line_number=1,
            raw_line="FROM ubuntu:20.04"
        )
        assert instruction.type == InstructionType.FROM
    
    def test_instruction_has_value(self):
        """Test Instruction has value attribute."""
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu:20.04",
            line_number=1,
            raw_line="FROM ubuntu:20.04"
        )
        assert instruction.value == "ubuntu:20.04"
    
    def test_instruction_has_line_number(self):
        """Test Instruction has line_number attribute."""
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu:20.04",
            line_number=1,
            raw_line="FROM ubuntu:20.04"
        )
        assert instruction.line_number == 1
    
    def test_instruction_repr(self):
        """Test Instruction string representation."""
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu:20.04",
            line_number=1,
            raw_line="FROM ubuntu:20.04"
        )
        repr_str = repr(instruction)
        assert "FROM" in repr_str
        assert "1" in repr_str


class TestDockerfileParserValidation:
    """Tests for Dockerfile parser validation."""
    
    def test_parse_dockerfile_missing_from(self):
        """Test parsing Dockerfile without FROM instruction."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("RUN apt-get update\n")
            f.write("CMD echo hello\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Should parse but may have validation errors
            assert dockerfile is not None
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_multiple_from(self):
        """Test parsing Dockerfile with multiple FROM instructions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\n")
            f.write("RUN apt-get update\n")
            f.write("FROM alpine:latest\n")
            f.write("RUN apk add curl\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Multi-stage builds have multiple FROM
            from_count = sum(1 for i in dockerfile.instructions if i.type == InstructionType.FROM)
            assert from_count == 2
        finally:
            dockerfile_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestDockerfileParserRobustness:
    """Robustness tests for Dockerfile parser."""
    
    def test_parse_dockerfile_with_windows_line_endings(self):
        """Test parsing Dockerfile with Windows line endings."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM ubuntu:20.04\r\n")
            f.write("RUN apt-get update\r\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) >= 2
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_with_mixed_case(self):
        """Test parsing Dockerfile with mixed case instructions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("from ubuntu:20.04\n")
            f.write("Run apt-get update\n")
            f.write("cmd echo hello\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            # Parser should handle case-insensitive instructions
            assert dockerfile is not None
        finally:
            dockerfile_path.unlink()
    
    def test_parse_dockerfile_with_extra_whitespace(self):
        """Test parsing Dockerfile with extra whitespace."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
            f.write("FROM    ubuntu:20.04\n")
            f.write("RUN     apt-get update\n")
            f.write("CMD     echo hello\n")
            dockerfile_path = Path(f.name)
        
        try:
            parser = DockerfileParser()
            dockerfile = parser.parse(dockerfile_path)
            
            assert len(dockerfile.instructions) >= 3
        finally:
            dockerfile_path.unlink()


class TestInstructionTypeComparison:
    """Tests for InstructionType comparisons."""
    
    def test_instruction_type_equality(self):
        """Test InstructionType equality."""
        assert InstructionType.FROM == InstructionType.FROM
        assert InstructionType.RUN == InstructionType.RUN
        assert InstructionType.CMD == InstructionType.CMD
    
    def test_instruction_type_inequality(self):
        """Test InstructionType inequality."""
        assert InstructionType.FROM != InstructionType.RUN
        assert InstructionType.RUN != InstructionType.CMD
        assert InstructionType.CMD != InstructionType.FROM
    
    def test_instruction_type_in_set(self):
        """Test InstructionType in set."""
        supported = {InstructionType.FROM, InstructionType.RUN, InstructionType.CMD}
        
        assert InstructionType.FROM in supported
        assert InstructionType.RUN in supported
        assert InstructionType.CMD in supported
        assert InstructionType.UNSUPPORTED not in supported


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
