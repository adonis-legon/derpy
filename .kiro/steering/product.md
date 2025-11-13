Derpy is an independent container tool that builds, manages, and distributes OCI-compliant container images without depending on Docker, Podman, containerd, or any other container runtime. It's a Python CLI application that implements container functionality from scratch while maintaining full OCI compliance for interoperability with existing container ecosystems.

Version 0.1.0 (alpha) supports core Dockerfile instructions (FROM, RUN, CMD) and provides essential functionality for building images, managing a local repository, and pushing to OCI-compliant registries. The tool works cross-platform on Windows, Linux, and macOS.

Key design principles:

- Runtime independence: No dependency on existing container runtimes
- Minimal dependencies: Uses only essential Python packages (PyYAML, click, requests)
- OCI compliance: Ensures images work with Docker, Podman, Kubernetes, and other OCI-compatible tools
- Cross-platform: Consistent behavior across all major operating systems
