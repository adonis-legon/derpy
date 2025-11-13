# Nginx Web Server Example

This example demonstrates building a simple nginx web server with custom content.

## Building

```bash
cd examples/nginx-web
derpy build . -f Dockerfile -t nginx-hello:latest
```

## What This Does

1. Uses nginx Alpine base image (lightweight)
2. Creates a custom HTML index page
3. Configures nginx to run in foreground mode

## Notes

- Alpine-based images are smaller and more efficient
- The `daemon off;` directive keeps nginx running in the foreground, which is required for containers
