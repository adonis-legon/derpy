"""Tests for build pipeline module."""

import pytest
from derpy.build.pipeline import InstructionPipeline, PipelineResult


class TestInstructionPipeline:
    """Tests for InstructionPipeline class."""
    
    def test_instruction_pipeline_exists(self):
        """Test InstructionPipeline class exists."""
        assert InstructionPipeline is not None
    
    def test_instruction_pipeline_has_execute(self):
        """Test InstructionPipeline has execute method."""
        assert hasattr(InstructionPipeline, 'execute')
        assert callable(getattr(InstructionPipeline, 'execute', None))


class TestPipelineResult:
    """Tests for PipelineResult class."""
    
    def test_pipeline_result_creation(self):
        """Test creating PipelineResult."""
        result = PipelineResult(layers=[], history=[])
        assert result is not None
        assert result.layers == []
        assert result.history == []
        assert result.cmd_instruction is None
        assert result.base_image is None
    
    def test_pipeline_result_with_cmd(self):
        """Test PipelineResult with cmd instruction."""
        result = PipelineResult(
            layers=[],
            history=[],
            cmd_instruction="echo hello"
        )
        assert result.cmd_instruction == "echo hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
