FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy app source
COPY . /app

# Install app + runtime dependencies from pyproject.toml
RUN pip install --no-cache-dir .

# gRPC + metrics ports
EXPOSE 50051 8080

# Starts server (includes your repository smoke test path if present in src.server)
CMD ["python", "-m", "src.server"]