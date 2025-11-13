"""Additional tests for InstructionPipeline to increase coverage."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from derpy.build.pipeline import InstructionPipeline, PipelineResult
from derpy.dockerfile.parser import Instruction, InstructionType, Dockerfile
from derpy.dockerfile.handlers import FromInstruction, RunInstruction, CmdInstruction
from derpy.build.exceptions import BuildError
from derpy.oci.models import Layer, HistoryEntry


class TestInstructionPipelineInit:
    """Test InstructionPipeline initialization."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initializes with context."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        assert pipeline.context == mock_context
        assert pipeline.from_handler is not None
        assert pipeline.run_handler is not None
        assert pipeline.cmd_handler is not None


class TestInstructionPipelineProcessFrom:
    """Test FROM instruction processing."""
    
    def test_process_from_success(self):
        """Test successful FROM instruction processing."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu:20.04",
            raw_line="FROM ubuntu:20.04",
            line_number=1
        )
        
        result = pipeline._process_from(instruction)
        
        assert isinstance(result, FromInstruction)
        assert result.image == "ubuntu"
        assert result.tag == "20.04"
    
    def test_process_from_invalid(self):
        """Test FROM instruction processing with invalid instruction."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.FROM,
            value="",
            raw_line="FROM",
            line_number=1
        )
        
        with pytest.raises(BuildError, match="Invalid FROM instruction"):
            pipeline._process_from(instruction)


class TestInstructionPipelineProcessRun:
    """Test RUN instruction processing."""
    
    def test_process_run_success(self):
        """Test successful RUN instruction processing."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.RUN,
            value="apt-get update",
            raw_line="RUN apt-get update",
            line_number=2
        )
        
        mock_layer = Mock(spec=Layer)
        mock_executor = Mock(return_value=mock_layer)
        
        result = pipeline._process_run(instruction, mock_executor)
        
        assert result == mock_layer
        mock_executor.assert_called_once()
    
    def test_process_run_returns_none(self):
        """Test RUN instruction processing that returns None."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.RUN,
            value="echo hello",
            raw_line="RUN echo hello",
            line_number=2
        )
        
        mock_executor = Mock(return_value=None)
        
        result = pipeline._process_run(instruction, mock_executor)
        
        assert result is None
    
    def test_process_run_invalid(self):
        """Test RUN instruction processing with invalid instruction."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.RUN,
            value="",
            raw_line="RUN",
            line_number=2
        )
        
        mock_executor = Mock()
        
        with pytest.raises(BuildError, match="Invalid RUN instruction"):
            pipeline._process_run(instruction, mock_executor)


class TestInstructionPipelineProcessCmd:
    """Test CMD instruction processing."""
    
    def test_process_cmd_success(self):
        """Test successful CMD instruction processing."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.CMD,
            value='["echo", "hello"]',
            raw_line='CMD ["echo", "hello"]',
            line_number=3
        )
        
        result = pipeline._process_cmd(instruction)
        
        assert isinstance(result, str)
        assert "echo" in result
    
    def test_process_cmd_invalid(self):
        """Test CMD instruction processing with invalid instruction."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.CMD,
            value="",
            raw_line="CMD",
            line_number=3
        )
        
        with pytest.raises(BuildError, match="Invalid CMD instruction"):
            pipeline._process_cmd(instruction)


class TestInstructionPipelineCreateHistory:
    """Test history entry creation."""
    
    def test_create_history_entry(self):
        """Test creating history entry."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.RUN,
            value="apt-get update",
            raw_line="RUN apt-get update",
            line_number=2
        )
        
        created_time = datetime.now(timezone.utc).isoformat()
        
        entry = pipeline._create_history_entry(instruction, created_time, empty_layer=False)
        
        assert isinstance(entry, HistoryEntry)
        assert entry.created == created_time
        assert "derpy:" in entry.created_by
        assert "RUN apt-get update" in entry.created_by
        assert entry.empty_layer is False
        assert "Line 2" in entry.comment
    
    def test_create_history_entry_empty_layer(self):
        """Test creating history entry for empty layer."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        instruction = Instruction(
            type=InstructionType.FROM,
            value="ubuntu:20.04",
            raw_line="FROM ubuntu:20.04",
            line_number=1
        )
        
        created_time = datetime.now(timezone.utc).isoformat()
        
        entry = pipeline._create_history_entry(instruction, created_time, empty_layer=True)
        
        assert entry.empty_layer is True


class TestInstructionPipelineExecute:
    """Test full pipeline execution."""
    
    def test_execute_from_only(self):
        """Test executing pipeline with FROM only."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        dockerfile = Dockerfile(
            instructions=[
                Instruction(
                    type=InstructionType.FROM,
                    value="ubuntu:20.04",
                    raw_line="FROM ubuntu:20.04",
                    line_number=1
                )
            ],
            validation_errors=[]
        )
        
        mock_executor = Mock()
        
        result = pipeline.execute(dockerfile, mock_executor)
        
        assert isinstance(result, PipelineResult)
        assert len(result.layers) == 0
        assert len(result.history) == 1
        assert result.base_image is not None
        assert result.cmd_instruction is None
    
    def test_execute_from_and_run(self):
        """Test executing pipeline with FROM and RUN."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        dockerfile = Dockerfile(
            instructions=[
                Instruction(
                    type=InstructionType.FROM,
                    value="ubuntu:20.04",
                    raw_line="FROM ubuntu:20.04",
                    line_number=1
                ),
                Instruction(
                    type=InstructionType.RUN,
                    value="apt-get update",
                    raw_line="RUN apt-get update",
                    line_number=2
                )
            ],
            validation_errors=[]
        )
        
        mock_layer = Mock(spec=Layer)
        mock_executor = Mock(return_value=mock_layer)
        
        result = pipeline.execute(dockerfile, mock_executor)
        
        assert len(result.layers) == 1
        assert len(result.history) == 2
        assert result.layers[0] == mock_layer
    
    def test_execute_full_dockerfile(self):
        """Test executing pipeline with FROM, RUN, and CMD."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        dockerfile = Dockerfile(
            instructions=[
                Instruction(
                    type=InstructionType.FROM,
                    value="ubuntu:20.04",
                    raw_line="FROM ubuntu:20.04",
                    line_number=1
                ),
                Instruction(
                    type=InstructionType.RUN,
                    value="apt-get update",
                    raw_line="RUN apt-get update",
                    line_number=2
                ),
                Instruction(
                    type=InstructionType.CMD,
                    value='["bash"]',
                    raw_line='CMD ["bash"]',
                    line_number=3
                )
            ],
            validation_errors=[]
        )
        
        mock_layer = Mock(spec=Layer)
        mock_executor = Mock(return_value=mock_layer)
        
        result = pipeline.execute(dockerfile, mock_executor)
        
        assert len(result.layers) == 1
        assert len(result.history) == 3
        assert result.cmd_instruction is not None
        assert result.base_image is not None
    
    def test_execute_run_without_layer(self):
        """Test executing RUN that doesn't create a layer."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        dockerfile = Dockerfile(
            instructions=[
                Instruction(
                    type=InstructionType.FROM,
                    value="ubuntu:20.04",
                    raw_line="FROM ubuntu:20.04",
                    line_number=1
                ),
                Instruction(
                    type=InstructionType.RUN,
                    value="echo hello",
                    raw_line="RUN echo hello",
                    line_number=2
                )
            ],
            validation_errors=[]
        )
        
        mock_executor = Mock(return_value=None)
        
        result = pipeline.execute(dockerfile, mock_executor)
        
        assert len(result.layers) == 0
        assert len(result.history) == 2
        assert result.history[1].empty_layer is True
    
    def test_execute_unsupported_instruction(self):
        """Test executing pipeline with unsupported instruction."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        # Create a mock instruction with unsupported type
        unsupported_instruction = Instruction(
            type=InstructionType.UNSUPPORTED,
            value=". /app",
            raw_line="COPY . /app",
            line_number=2
        )
        
        dockerfile = Dockerfile(
            instructions=[
                Instruction(
                    type=InstructionType.FROM,
                    value="ubuntu:20.04",
                    raw_line="FROM ubuntu:20.04",
                    line_number=1
                ),
                unsupported_instruction
            ],
            validation_errors=[]
        )
        
        mock_executor = Mock()
        
        with pytest.raises(BuildError, match="Unsupported instruction"):
            pipeline.execute(dockerfile, mock_executor)
    
    def test_execute_with_exception(self):
        """Test executing pipeline when instruction processing raises exception."""
        mock_context = Mock()
        pipeline = InstructionPipeline(mock_context)
        
        dockerfile = Dockerfile(
            instructions=[
                Instruction(
                    type=InstructionType.FROM,
                    value="ubuntu:20.04",
                    raw_line="FROM ubuntu:20.04",
                    line_number=1
                ),
                Instruction(
                    type=InstructionType.RUN,
                    value="apt-get update",
                    raw_line="RUN apt-get update",
                    line_number=2
                )
            ],
            validation_errors=[]
        )
        
        mock_executor = Mock(side_effect=Exception("Execution failed"))
        
        with pytest.raises(BuildError, match="Failed to process instruction at line 2"):
            pipeline.execute(dockerfile, mock_executor)


class TestPipelineResultDataclass:
    """Test PipelineResult dataclass."""
    
    def test_pipeline_result_defaults(self):
        """Test PipelineResult with default values."""
        result = PipelineResult(layers=[], history=[])
        
        assert result.layers == []
        assert result.history == []
        assert result.cmd_instruction is None
        assert result.base_image is None
    
    def test_pipeline_result_with_all_fields(self):
        """Test PipelineResult with all fields."""
        mock_layer = Mock(spec=Layer)
        mock_history = Mock(spec=HistoryEntry)
        mock_base = Mock(spec=FromInstruction)
        
        result = PipelineResult(
            layers=[mock_layer],
            history=[mock_history],
            cmd_instruction="bash",
            base_image=mock_base
        )
        
        assert len(result.layers) == 1
        assert len(result.history) == 1
        assert result.cmd_instruction == "bash"
        assert result.base_image == mock_base


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
