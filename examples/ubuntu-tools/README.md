# Ubuntu Development Tools Example

This example demonstrates building an Ubuntu-based container with common development tools.

## Building

```bash
cd examples/ubuntu-tools
derpy build . -f Dockerfile -t ubuntu-dev:latest
```

## What This Does

1. Uses Ubuntu 22.04 LTS base image
2. Installs common development tools (curl, wget, git, vim)
3. Cleans up apt cache to reduce image size
4. Sets bash as the default command

## Notes

- The `&&` chains commands together in a single RUN instruction
- `rm -rf /var/lib/apt/lists/*` removes package lists to reduce image size
- Multiple packages can be installed in a single apt-get command
