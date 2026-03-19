# Dockerfile for Python microservice
# Customize this for your specific service needs

# Choose your Python version
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY proto/ ./proto/
COPY src/ ./src/
COPY .env.example .env

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; grpc.aio.secure_channel('localhost:50051', grpc.ssl_channel_credentials())" || exit 1

# Run server
CMD ["python", "-m", "src.server"]