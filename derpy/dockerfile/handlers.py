"""Instruction handlers for Dockerfile processing."""

from dataclasses import dataclass
from typing import List, Optional, Union
from abc import ABC, abstractmethod

from derpy.dockerfile.parser import Instruction, InstructionType


@dataclass
class FromInstruction:
    """Represents a parsed FROM instruction."""
    
    image: str
    tag: Optional[str] = None
    digest: Optional[str] = None
    platform: Optional[str] = None
    alias: Optional[str] = None
    
    def __str__(self) -> str:
        result = self.image
        if self.tag:
            result += f":{self.tag}"
        elif self.digest:
            result += f"@{self.digest}"
        if self.alias:
            result += f" AS {self.alias}"
        return result


@dataclass
class RunInstruction:
    """Represents a parsed RUN instruction."""
    
    command: str
    is_shell_form: bool = True
    
    def __str__(self) -> str:
        return f"RUN {self.command}"


@dataclass
class CmdInstruction:
    """Represents a parsed CMD instruction."""
    
    command: Union[str, List[str]]
    is_shell_form: bool = True
    
    def __str__(self) -> str:
        if self.is_shell_form:
            return f"CMD {self.command}"
        else:
            return f"CMD {self.command}"



class InstructionHandler(ABC):
    """Base class for instruction handlers."""
    
    @abstractmethod
    def process(self, instruction: Instruction) -> Union[FromInstruction, RunInstruction, CmdInstruction]:
        """
        Process an instruction and return a typed instruction object.
        
        Args:
            instruction: Raw instruction to process
            
        Returns:
            Typed instruction object
            
        Raises:
            ValueError: If instruction format is invalid
        """
        pass
    
    @abstractmethod
    def validate(self, instruction: Instruction) -> List[str]:
        """
        Validate instruction format.
        
        Args:
            instruction: Instruction to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        pass


class FromHandler(InstructionHandler):
    """Handler for FROM instructions."""
    
    def process(self, instruction: Instruction) -> FromInstruction:
        """
        Process a FROM instruction.
        
        Args:
            instruction: FROM instruction to process
            
        Returns:
            Parsed FromInstruction object
            
        Raises:
            ValueError: If instruction format is invalid
        """
        if instruction.type != InstructionType.FROM:
            raise ValueError(f"Expected FROM instruction, got {instruction.type}")
        
        errors = self.validate(instruction)
        if errors:
            raise ValueError(f"Invalid FROM instruction: {', '.join(errors)}")
        
        value = instruction.value.strip()
        
        # Parse platform if present
        platform = None
        if value.startswith("--platform="):
            parts = value.split(maxsplit=1)
            platform = parts[0].replace("--platform=", "")
            value = parts[1] if len(parts) > 1 else ""
        
        # Parse alias (AS clause)
        alias = None
        if " AS " in value.upper():
            # Case-insensitive split
            parts = value.split()
            as_index = -1
            for i, part in enumerate(parts):
                if part.upper() == "AS":
                    as_index = i
                    break
            
            if as_index > 0 and as_index < len(parts) - 1:
                alias = parts[as_index + 1]
                value = " ".join(parts[:as_index])
        
        # Parse image, tag, and digest
        image = value
        tag = None
        digest = None
        
        if "@" in image:
            # Digest format: image@sha256:...
            image, digest = image.split("@", 1)
        elif ":" in image:
            # Tag format: image:tag
            image, tag = image.rsplit(":", 1)
        
        return FromInstruction(
            image=image,
            tag=tag,
            digest=digest,
            platform=platform,
            alias=alias
        )

    
    def validate(self, instruction: Instruction) -> List[str]:
        """
        Validate FROM instruction format.
        
        Args:
            instruction: Instruction to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not instruction.value or not instruction.value.strip():
            errors.append("FROM instruction requires a base image")
            return errors
        
        value = instruction.value.strip()
        
        # Remove platform flag for validation
        if value.startswith("--platform="):
            parts = value.split(maxsplit=1)
            if len(parts) < 2:
                errors.append("FROM instruction with --platform flag requires an image")
                return errors
            value = parts[1]
        
        # Check if image name is present after removing AS clause
        if " AS " in value.upper():
            parts = value.split()
            as_index = -1
            for i, part in enumerate(parts):
                if part.upper() == "AS":
                    as_index = i
                    break
            
            if as_index == 0:
                errors.append("FROM instruction requires an image before AS clause")
            elif as_index == len(parts) - 1:
                errors.append("FROM instruction requires an alias after AS clause")
        
        return errors


class RunHandler(InstructionHandler):
    """Handler for RUN instructions."""
    
    def process(self, instruction: Instruction) -> RunInstruction:
        """
        Process a RUN instruction.
        
        Args:
            instruction: RUN instruction to process
            
        Returns:
            Parsed RunInstruction object
            
        Raises:
            ValueError: If instruction format is invalid
        """
        if instruction.type != InstructionType.RUN:
            raise ValueError(f"Expected RUN instruction, got {instruction.type}")
        
        errors = self.validate(instruction)
        if errors:
            raise ValueError(f"Invalid RUN instruction: {', '.join(errors)}")
        
        command = instruction.value.strip()
        
        # Determine if it's shell form or exec form
        # Exec form starts with [ and ends with ]
        is_shell_form = not (command.startswith("[") and command.endswith("]"))
        
        return RunInstruction(
            command=command,
            is_shell_form=is_shell_form
        )
    
    def validate(self, instruction: Instruction) -> List[str]:
        """
        Validate RUN instruction format.
        
        Args:
            instruction: Instruction to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not instruction.value or not instruction.value.strip():
            errors.append("RUN instruction requires a command")
        
        return errors



class CmdHandler(InstructionHandler):
    """Handler for CMD instructions."""
    
    def process(self, instruction: Instruction) -> CmdInstruction:
        """
        Process a CMD instruction.
        
        Args:
            instruction: CMD instruction to process
            
        Returns:
            Parsed CmdInstruction object
            
        Raises:
            ValueError: If instruction format is invalid
        """
        if instruction.type != InstructionType.CMD:
            raise ValueError(f"Expected CMD instruction, got {instruction.type}")
        
        errors = self.validate(instruction)
        if errors:
            raise ValueError(f"Invalid CMD instruction: {', '.join(errors)}")
        
        command = instruction.value.strip()
        
        # Determine if it's shell form or exec form
        # Exec form starts with [ and ends with ]
        is_shell_form = not (command.startswith("[") and command.endswith("]"))
        
        # For exec form, we could parse the JSON array, but for v0.1.0
        # we'll keep it as a string and let the build engine handle it
        return CmdInstruction(
            command=command,
            is_shell_form=is_shell_form
        )
    
    def validate(self, instruction: Instruction) -> List[str]:
        """
        Validate CMD instruction format.
        
        Args:
            instruction: Instruction to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not instruction.value or not instruction.value.strip():
            errors.append("CMD instruction requires a command")
        
        return errors
