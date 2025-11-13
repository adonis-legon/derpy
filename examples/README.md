# Derpy Example Dockerfiles

This directory contains example Dockerfiles demonstrating various use cases with Derpy.

## Available Examples

### 1. Minimal Example (`minimal/`)

The simplest possible Dockerfile using Alpine Linux. Perfect for testing and learning.

**Build**: `derpy build examples/minimal -f examples/minimal/Dockerfile -t minimal:latest`

### 2. Python Flask Application (`python-app/`)

A Python web application using Flask framework.

**Build**: `derpy build examples/python-app -f examples/python-app/Dockerfile -t flask-app:latest`

### 3. Nginx Web Server (`nginx-web/`)

A lightweight web server with custom HTML content.

**Build**: `derpy build examples/nginx-web -f examples/nginx-web/Dockerfile -t nginx-hello:latest`

### 4. Ubuntu Development Tools (`ubuntu-tools/`)

Ubuntu-based image with common development tools installed.

**Build**: `derpy build examples/ubuntu-tools -f examples/ubuntu-tools/Dockerfile -t ubuntu-dev:latest`

## General Usage Pattern

All examples follow this pattern:

```bash
# Navigate to example directory
cd examples/[example-name]

# Build the image
derpy build . -f Dockerfile -t [image-name]:[tag]

# List your images
derpy ls

# Push to registry (optional)
derpy push [image-name]:[tag]
```

## Supported Instructions (v0.1.0)

These examples only use instructions supported in Derpy v0.1.0:

- `FROM` - Specify base image
- `RUN` - Execute commands during build
- `CMD` - Set default command

## Tips

1. **Start Simple**: Begin with the minimal example to verify your setup
2. **Build Context**: The build context is the directory containing files needed for the build
3. **Layer Caching**: Each RUN instruction creates a new layer
4. **Image Size**: Chain commands with `&&` and clean up in the same RUN instruction to reduce size

## Troubleshooting

If builds fail:

1. Check that the base image is accessible
2. Verify commands exist in the base image
3. Review error messages for specific issues
4. Consult the main README.md troubleshooting section

## Contributing Examples

Have a useful example? Contributions are welcome! Please ensure:

- Only use supported instructions (FROM, RUN, CMD)
- Include a README.md explaining the example
- Keep it simple and focused on one concept
- Test the build before submitting
