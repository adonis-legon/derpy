FROM python:3.11-slim

# Install dependencies
RUN pip install --no-cache-dir flask requests

# Set default command
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
