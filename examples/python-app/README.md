# Python Flask Application Example

This example demonstrates building a simple Python Flask application container.

## Building

```bash
cd examples/python-app
derpy build . -f Dockerfile -t flask-app:latest
```

## What This Does

1. Uses Python 3.11 slim base image
2. Installs Flask and requests packages
3. Sets Flask as the default command

## Notes

- The `--no-cache-dir` flag reduces image size by not storing pip cache
- Flask runs on all interfaces (0.0.0.0) to be accessible from outside the container
