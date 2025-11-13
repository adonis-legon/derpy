"""Dockerfile parsing and validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union
from enum import Enum

from derpy.core.exceptions import (
    BuildError,
    DockerfileNotFoundError,
    DockerfileSyntaxError,
    UnsupportedInstructionError
)


class InstructionType(Enum):
    """Supported Dockerfile instruction types."""
    FROM = "FROM"
    RUN = "RUN"
    CMD = "CMD"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class Instruction:
    """Represents a parsed Dockerfile instruction."""
    
    type: InstructionType
    value: str
    line_number: int
    raw_line: str
    
    def __repr__(self) -> str:
        return f"Instruction({self.type.value}, line={self.line_number})"


@dataclass
class ValidationError:
    """Represents a Dockerfile validation error."""
    
    line_number: int
    message: str
    raw_line: str
    
    def __str__(self) -> str:
        return f"Line {self.line_number}: {self.message}\n  {self.raw_line}"


@dataclass
class Dockerfile:
    """Represents a parsed Dockerfile."""
    
    instructions: List[Instruction]
    validation_errors: List[ValidationError]
    path: Optional[Path] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if Dockerfile has no validation errors."""
        return len(self.validation_errors) == 0


class DockerfileParser:
    """Parser for Dockerfile syntax with validation."""
    
    SUPPORTED_INSTRUCTIONS = {
        InstructionType.FROM,
        InstructionType.RUN,
        InstructionType.CMD
    }
    
    def __init__(self):
        """Initialize the Dockerfile parser."""
        self._instructions: List[Instruction] = []
        self._errors: List[ValidationError] = []
    
    def parse(self, dockerfile_path: Path) -> Dockerfile:
        """
        Parse a Dockerfile from the given path.
        
        Args:
            dockerfile_path: Path to the Dockerfile
            
        Returns:
            Parsed Dockerfile object with instructions and validation errors
            
        Raises:
            DockerfileNotFoundError: If the file cannot be found
            BuildError: If the file cannot be read
        """
        if not dockerfile_path.exists():
            raise DockerfileNotFoundError(str(dockerfile_path))
        
        if not dockerfile_path.is_file():
            raise BuildError(f"Path is not a file: {dockerfile_path}")
        
        try:
            content = dockerfile_path.read_text()
        except Exception as e:
            raise BuildError(f"Failed to read Dockerfile: {e}", cause=e)
        
        self._instructions = []
        self._errors = []
        
        instructions = self.extract_instructions(content)
        errors = self.validate_syntax(content)
        
        return Dockerfile(
            instructions=instructions,
            validation_errors=errors,
            path=dockerfile_path
        )

    
    def extract_instructions(self, content: str) -> List[Instruction]:
        """
        Extract instructions from Dockerfile content.
        
        Args:
            content: Raw Dockerfile content
            
        Returns:
            List of parsed instructions
        """
        instructions: List[Instruction] = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Parse instruction
            instruction = self._parse_line(line, line_num)
            if instruction:
                instructions.append(instruction)
        
        return instructions
    
    def _parse_line(self, line: str, line_number: int) -> Optional[Instruction]:
        """
        Parse a single line into an instruction.
        
        Args:
            line: Raw line content
            line_number: Line number in the file
            
        Returns:
            Parsed instruction or None if line is invalid
        """
        stripped = line.strip()
        
        # Split instruction and value
        parts = stripped.split(maxsplit=1)
        if not parts:
            return None
        
        instruction_name = parts[0].upper()
        instruction_value = parts[1] if len(parts) > 1 else ""
        
        # Determine instruction type
        try:
            instruction_type = InstructionType[instruction_name]
        except KeyError:
            instruction_type = InstructionType.UNSUPPORTED
        
        return Instruction(
            type=instruction_type,
            value=instruction_value.strip(),
            line_number=line_number,
            raw_line=line
        )

    
    def validate_syntax(self, content: str) -> List[ValidationError]:
        """
        Validate Dockerfile syntax and report errors.
        
        Args:
            content: Raw Dockerfile content
            
        Returns:
            List of validation errors with line numbers
        """
        errors: List[ValidationError] = []
        lines = content.splitlines()
        has_from = False
        
        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Parse instruction
            instruction = self._parse_line(line, line_num)
            if not instruction:
                errors.append(ValidationError(
                    line_number=line_num,
                    message="Invalid instruction format",
                    raw_line=line
                ))
                continue
            
            # Check for unsupported instructions
            if instruction.type == InstructionType.UNSUPPORTED:
                errors.append(ValidationError(
                    line_number=line_num,
                    message=f"Unsupported instruction: {instruction.raw_line.split()[0]}. "
                           f"Only FROM, RUN, and CMD are supported in v0.1.0",
                    raw_line=line
                ))
                continue
            
            # Validate FROM instruction
            if instruction.type == InstructionType.FROM:
                has_from = True
                if not instruction.value:
                    errors.append(ValidationError(
                        line_number=line_num,
                        message="FROM instruction requires a base image",
                        raw_line=line
                    ))
            
            # Validate RUN instruction
            elif instruction.type == InstructionType.RUN:
                if not instruction.value:
                    errors.append(ValidationError(
                        line_number=line_num,
                        message="RUN instruction requires a command",
                        raw_line=line
                    ))
            
            # Validate CMD instruction
            elif instruction.type == InstructionType.CMD:
                if not instruction.value:
                    errors.append(ValidationError(
                        line_number=line_num,
                        message="CMD instruction requires a command",
                        raw_line=line
                    ))
        
        # Check if Dockerfile has at least one FROM instruction
        if not has_from and lines:
            errors.append(ValidationError(
                line_number=1,
                message="Dockerfile must contain at least one FROM instruction",
                raw_line=""
            ))
        
        return errors
