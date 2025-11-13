# Minimal Example

This is the simplest possible Dockerfile example for testing Derpy.

## Building

```bash
cd examples/minimal
derpy build . -f Dockerfile -t minimal:latest
```

## What This Does

1. Uses Alpine Linux (smallest base image)
2. Runs a simple echo command during build
3. Sets an echo command as the default

## Use Case

Perfect for:

- Testing Derpy installation
- Learning basic Dockerfile syntax
- Quick validation of build functionality
