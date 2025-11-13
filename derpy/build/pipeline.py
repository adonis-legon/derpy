"""Instruction execution pipeline for building images."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, TYPE_CHECKING
from datetime import datetime, timezone

from derpy.dockerfile.parser import Dockerfile, Instruction, InstructionType
from derpy.dockerfile.handlers import FromHandler, RunHandler, CmdHandler, FromInstruction
from derpy.oci.models import Layer, HistoryEntry
from derpy.build.exceptions import BuildError

if TYPE_CHECKING:
    from derpy.build.engine import BuildContext


@dataclass
class PipelineResult:
    """Result of executing the instruction pipeline."""
    
    layers: List[Layer]
    history: List[HistoryEntry]
    cmd_instruction: Optional[str] = None
    base_image: Optional[FromInstruction] = None


class InstructionPipeline:
    """Pipeline for executing Dockerfile instructions in sequence."""
    
    def __init__(self, context: "BuildContext"):
        """Initialize the instruction pipeline.
        
        Args:
            context: Build context
        """
        self.context = context
        self.from_handler = FromHandler()
        self.run_handler = RunHandler()
        self.cmd_handler = CmdHandler()
    
    def execute(self, dockerfile: Dockerfile, layer_executor) -> PipelineResult:
        """Execute all instructions in the Dockerfile.
        
        Args:
            dockerfile: Parsed Dockerfile
            layer_executor: Callable that executes RUN instructions and returns layers
        
        Returns:
            PipelineResult with layers, history, and metadata
        
        Raises:
            BuildError: If execution fails
        """
        layers: List[Layer] = []
        history: List[HistoryEntry] = []
        cmd_instruction: Optional[str] = None
        base_image: Optional[FromInstruction] = None
        
        created_time = datetime.now(timezone.utc).isoformat()
        
        # Process each instruction
        for instruction in dockerfile.instructions:
            try:
                if instruction.type == InstructionType.FROM:
                    # Process FROM instruction
                    base_image = self._process_from(instruction)
                    history.append(self._create_history_entry(
                        instruction,
                        created_time,
                        empty_layer=True
                    ))
                
                elif instruction.type == InstructionType.RUN:
                    # Process RUN instruction
                    layer = self._process_run(instruction, layer_executor)
                    if layer:
                        layers.append(layer)
                    history.append(self._create_history_entry(
                        instruction,
                        created_time,
                        empty_layer=(layer is None)
                    ))
                
                elif instruction.type == InstructionType.CMD:
                    # Process CMD instruction
                    cmd_instruction = self._process_cmd(instruction)
                    history.append(self._create_history_entry(
                        instruction,
                        created_time,
                        empty_layer=True
                    ))
                
                else:
                    # Unsupported instruction - should have been caught by validation
                    raise BuildError(f"Unsupported instruction: {instruction.type}")
            
            except BuildError:
                raise
            except Exception as e:
                raise BuildError(
                    f"Failed to process instruction at line {instruction.line_number}: {e}"
                )
        
        return PipelineResult(
            layers=layers,
            history=history,
            cmd_instruction=cmd_instruction,
            base_image=base_image
        )
    
    def _process_from(self, instruction: Instruction) -> FromInstruction:
        """Process a FROM instruction.
        
        Args:
            instruction: FROM instruction
        
        Returns:
            Parsed FromInstruction
        
        Raises:
            BuildError: If processing fails
        """
        try:
            from_inst = self.from_handler.process(instruction)
            return from_inst
        except ValueError as e:
            raise BuildError(f"Invalid FROM instruction at line {instruction.line_number}: {e}")
    
    def _process_run(self, instruction: Instruction, layer_executor) -> Optional[Layer]:
        """Process a RUN instruction.
        
        Args:
            instruction: RUN instruction
            layer_executor: Callable that executes the instruction and returns a layer
        
        Returns:
            Layer object or None
        
        Raises:
            BuildError: If processing fails
        """
        try:
            run_inst = self.run_handler.process(instruction)
            # Execute the RUN instruction using the provided executor
            layer = layer_executor(instruction, run_inst)
            return layer
        except ValueError as e:
            raise BuildError(f"Invalid RUN instruction at line {instruction.line_number}: {e}")
    
    def _process_cmd(self, instruction: Instruction) -> str:
        """Process a CMD instruction.
        
        Args:
            instruction: CMD instruction
        
        Returns:
            CMD value as string
        
        Raises:
            BuildError: If processing fails
        """
        try:
            cmd_inst = self.cmd_handler.process(instruction)
            return cmd_inst.command
        except ValueError as e:
            raise BuildError(f"Invalid CMD instruction at line {instruction.line_number}: {e}")
    
    def _create_history_entry(
        self,
        instruction: Instruction,
        created_time: str,
        empty_layer: bool = False
    ) -> HistoryEntry:
        """Create a history entry for an instruction.
        
        Args:
            instruction: Dockerfile instruction
            created_time: ISO format timestamp
            empty_layer: Whether this instruction creates an empty layer
        
        Returns:
            HistoryEntry object
        """
        return HistoryEntry(
            created=created_time,
            created_by=f"derpy: {instruction.raw_line.strip()}",
            empty_layer=empty_layer,
            comment=f"Line {instruction.line_number}"
        )
