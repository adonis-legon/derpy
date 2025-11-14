"""Isolation executor for running commands in chroot environments.

This module provides functionality for executing commands in isolated
chroot environments, enabling proper container build isolation on Linux.
"""

import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional
import shutil

from derpy.core.exceptions import IsolationError, PlatformNotSupportedError
from derpy.core.logging import get_logger
from derpy.build.models import ExecutionResult


class IsolationExecutor:
    """Executes commands in chrooted filesystem environments.
    
    Provides Linux-specific chroot isolation for running build commands
    in base image filesystems. Handles environment setup, command execution,
    and cleanup.
    """
    
    def __init__(self):
        """Initialize the isolation executor."""
        self.logger = get_logger('isolation')
    
    def validate_linux_environment(self) -> None:
        """Verify running on Linux with chroot capability.
        
        Checks:
        1. Operating system is Linux
        2. Running as root or with CAP_SYS_CHROOT capability
        
        Raises:
            PlatformNotSupportedError: If not running on Linux
            IsolationError: If chroot capability is not available
        """
        # Check if running on Linux
        current_platform = platform.system()
        if current_platform != "Linux":
            raise PlatformNotSupportedError(
                operation="chroot isolation",
                required_platform="Linux",
                current_platform=current_platform
            )
        
        # Check if running as root
        if os.geteuid() != 0:
            # Not root, check for CAP_SYS_CHROOT capability
            try:
                # Try to check capabilities using capsh if available
                result = subprocess.run(
                    ["capsh", "--print"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    # Check if CAP_SYS_CHROOT is in current capabilities
                    if "cap_sys_chroot" not in result.stdout.lower():
                        raise IsolationError(
                            "Insufficient permissions for chroot. "
                            "Run with sudo or grant CAP_SYS_CHROOT capability."
                        )
                else:
                    # capsh failed, assume no capability
                    raise IsolationError(
                        "Insufficient permissions for chroot. "
                        "Run with sudo or grant CAP_SYS_CHROOT capability."
                    )
            except FileNotFoundError:
                # capsh not available, just warn that we need root
                raise IsolationError(
                    "Insufficient permissions for chroot. "
                    "Run with sudo to use build isolation features."
                )
            except subprocess.TimeoutExpired:
                raise IsolationError(
                    "Failed to check chroot capability (timeout). "
                    "Run with sudo to use build isolation features."
                )
        
        self.logger.debug("Linux environment validation passed")
    
    def setup_chroot_environment(self, rootfs: Path) -> None:
        """Prepare rootfs for chroot execution.
        
        Sets up the chroot environment by:
        1. Mounting /proc, /sys, /dev if needed
        2. Copying /etc/resolv.conf for DNS resolution
        3. Verifying shell exists in rootfs
        
        Args:
            rootfs: Path to root filesystem directory
            
        Raises:
            IsolationError: If environment setup fails
        """
        if not rootfs.exists() or not rootfs.is_dir():
            raise IsolationError(f"Rootfs directory does not exist: {rootfs}")
        
        self.logger.debug(f"Setting up chroot environment at {rootfs}")
        
        try:
            # Mount /proc if not already mounted
            proc_path = rootfs / "proc"
            proc_path.mkdir(exist_ok=True)
            if not self._is_mounted(proc_path):
                self.logger.debug(f"Mounting /proc at {proc_path}")
                subprocess.run(
                    ["mount", "-t", "proc", "proc", str(proc_path)],
                    check=True,
                    capture_output=True
                )
            
            # Mount /sys if not already mounted
            sys_path = rootfs / "sys"
            sys_path.mkdir(exist_ok=True)
            if not self._is_mounted(sys_path):
                self.logger.debug(f"Mounting /sys at {sys_path}")
                subprocess.run(
                    ["mount", "-t", "sysfs", "sysfs", str(sys_path)],
                    check=True,
                    capture_output=True
                )
            
            # Mount /dev if not already mounted
            dev_path = rootfs / "dev"
            dev_path.mkdir(exist_ok=True)
            if not self._is_mounted(dev_path):
                self.logger.debug(f"Binding /dev at {dev_path}")
                subprocess.run(
                    ["mount", "--bind", "/dev", str(dev_path)],
                    check=True,
                    capture_output=True
                )
            
            # Copy /etc/resolv.conf for DNS resolution
            host_resolv = Path("/etc/resolv.conf")
            rootfs_resolv = rootfs / "etc" / "resolv.conf"
            
            if host_resolv.exists():
                # Ensure /etc directory exists
                (rootfs / "etc").mkdir(exist_ok=True)
                
                # Backup existing resolv.conf if it exists
                if rootfs_resolv.exists():
                    backup_path = rootfs / "etc" / "resolv.conf.derpy-backup"
                    shutil.copy2(rootfs_resolv, backup_path)
                    self.logger.debug(f"Backed up existing resolv.conf to {backup_path}")
                
                # Copy host's resolv.conf
                shutil.copy2(host_resolv, rootfs_resolv)
                self.logger.debug(f"Copied /etc/resolv.conf to {rootfs_resolv}")
            
            # Verify shell exists in rootfs
            shell_path = rootfs / "bin" / "sh"
            if not shell_path.exists():
                raise IsolationError(
                    f"Shell not found in rootfs: /bin/sh. "
                    f"The base image may be incomplete or corrupted."
                )
            
            self.logger.debug("Chroot environment setup complete")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to setup chroot environment: {e.stderr.decode() if e.stderr else str(e)}"
            raise IsolationError(error_msg, cause=e)
        except OSError as e:
            raise IsolationError(f"Failed to setup chroot environment: {str(e)}", cause=e)
    
    def _is_mounted(self, path: Path) -> bool:
        """Check if a path is a mount point.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path is a mount point, False otherwise
        """
        try:
            # Use mountpoint command if available
            result = subprocess.run(
                ["mountpoint", "-q", str(path)],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback: check if path is in /proc/mounts
            try:
                with open("/proc/mounts", "r") as f:
                    mounts = f.read()
                    return str(path) in mounts
            except OSError:
                # If we can't determine, assume not mounted
                return False
    
    def execute_in_chroot(
        self,
        rootfs: Path,
        command: str,
        shell: str = "/bin/sh",
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute command in chrooted environment.
        
        Uses os.chroot() to change root directory, then executes the command
        with the specified shell.
        
        Args:
            rootfs: Path to root filesystem
            command: Command to execute
            shell: Shell to use (from base image), defaults to /bin/sh
            timeout: Command timeout in seconds, defaults to 300
            
        Returns:
            ExecutionResult with stdout, stderr, exit_code, and duration
            
        Raises:
            IsolationError: If chroot or command execution fails
        """
        if not rootfs.exists() or not rootfs.is_dir():
            raise IsolationError(f"Rootfs directory does not exist: {rootfs}")
        
        # Verify shell exists in rootfs
        shell_path = rootfs / shell.lstrip("/")
        if not shell_path.exists():
            raise IsolationError(
                f"Shell not found in rootfs: {shell}. "
                f"Ensure the base image contains the specified shell."
            )
        
        self.logger.debug(f"Executing command in chroot: {command}")
        
        start_time = time.time()
        
        try:
            # We need to use a subprocess that will chroot and then execute
            # We can't use os.chroot() directly in the parent process
            # Instead, we'll use chroot command or create a helper script
            
            # Use the chroot command to execute in the isolated environment
            chroot_cmd = [
                "chroot",
                str(rootfs),
                shell,
                "-c",
                command
            ]
            
            # Check if we should stream output (verbose/debug mode)
            import logging
            should_stream = self.logger.isEnabledFor(logging.INFO)
            
            if should_stream:
                # Stream output in real-time for verbose/debug mode
                import sys
                
                stdout_lines = []
                stderr_lines = []
                
                process = subprocess.Popen(
                    chroot_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1  # Line buffered
                )
                
                # Use select to read from both stdout and stderr
                import select
                
                # Set streams to non-blocking
                import os
                import fcntl
                for stream in [process.stdout, process.stderr]:
                    fd = stream.fileno()
                    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                start = time.time()
                while True:
                    # Check timeout
                    if time.time() - start > timeout:
                        process.kill()
                        process.wait()
                        raise subprocess.TimeoutExpired(chroot_cmd, timeout)
                    
                    # Check if process has finished
                    if process.poll() is not None:
                        # Read any remaining output
                        for line in process.stdout:
                            stdout_lines.append(line)
                            sys.stdout.write(line)
                            sys.stdout.flush()
                        for line in process.stderr:
                            stderr_lines.append(line)
                            sys.stderr.write(line)
                            sys.stderr.flush()
                        break
                    
                    # Wait for data with timeout
                    readable, _, _ = select.select(
                        [process.stdout, process.stderr], [], [], 0.1
                    )
                    
                    for stream in readable:
                        try:
                            line = stream.readline()
                            if line:
                                if stream == process.stdout:
                                    stdout_lines.append(line)
                                    sys.stdout.write(line)
                                    sys.stdout.flush()
                                else:
                                    stderr_lines.append(line)
                                    sys.stderr.write(line)
                                    sys.stderr.flush()
                        except IOError:
                            # No data available
                            pass
                
                result_stdout = ''.join(stdout_lines)
                result_stderr = ''.join(stderr_lines)
                exit_code = process.returncode
                
            else:
                # Non-streaming mode (quiet mode)
                result = subprocess.run(
                    chroot_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                result_stdout = result.stdout
                result_stderr = result.stderr
                exit_code = result.returncode
            
            duration = time.time() - start_time
            
            execution_result = ExecutionResult(
                exit_code=exit_code,
                stdout=result_stdout,
                stderr=result_stderr,
                duration=duration,
                command=command
            )
            
            if execution_result.is_success():
                self.logger.debug(
                    f"Command executed successfully in {duration:.2f}s"
                )
            else:
                self.logger.warning(
                    f"Command failed with exit code {exit_code} "
                    f"in {duration:.2f}s"
                )
            
            return execution_result
            
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            error_msg = f"Command timed out after {timeout}s: {command}"
            self.logger.error(error_msg)
            
            # Return a failed execution result
            return ExecutionResult(
                exit_code=124,  # Standard timeout exit code
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=f"Command timed out after {timeout}s",
                duration=duration,
                command=command
            )
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            error_msg = f"Failed to execute command in chroot: {e}"
            self.logger.error(error_msg)
            
            return ExecutionResult(
                exit_code=e.returncode,
                stdout=e.stdout if e.stdout else "",
                stderr=e.stderr if e.stderr else str(e),
                duration=duration,
                command=command
            )
            
        except OSError as e:
            duration = time.time() - start_time
            raise IsolationError(
                f"Failed to execute command in chroot: {str(e)}",
                cause=e
            )
    
    def cleanup_chroot_environment(self, rootfs: Path) -> None:
        """Clean up chroot environment.
        
        Unmounts /proc, /sys, /dev and removes temporary files.
        Handles cleanup errors gracefully by logging warnings.
        
        Args:
            rootfs: Path to root filesystem directory
        """
        if not rootfs.exists():
            self.logger.debug(f"Rootfs does not exist, skipping cleanup: {rootfs}")
            return
        
        self.logger.debug(f"Cleaning up chroot environment at {rootfs}")
        
        # Unmount in reverse order: /dev, /sys, /proc
        mount_points = [
            rootfs / "dev",
            rootfs / "sys",
            rootfs / "proc"
        ]
        
        for mount_point in mount_points:
            if mount_point.exists() and self._is_mounted(mount_point):
                try:
                    self.logger.debug(f"Unmounting {mount_point}")
                    subprocess.run(
                        ["umount", str(mount_point)],
                        check=True,
                        capture_output=True,
                        timeout=10
                    )
                except subprocess.CalledProcessError as e:
                    # Log warning but don't fail
                    self.logger.warning(
                        f"Failed to unmount {mount_point}: "
                        f"{e.stderr.decode() if e.stderr else str(e)}"
                    )
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Timeout while unmounting {mount_point}")
        
        # Restore original resolv.conf if backup exists
        backup_resolv = rootfs / "etc" / "resolv.conf.derpy-backup"
        target_resolv = rootfs / "etc" / "resolv.conf"
        
        if backup_resolv.exists():
            try:
                shutil.move(str(backup_resolv), str(target_resolv))
                self.logger.debug("Restored original resolv.conf")
            except OSError as e:
                self.logger.warning(f"Failed to restore resolv.conf: {e}")
        
        self.logger.debug("Chroot environment cleanup complete")
