# Dockerfile for Python microservice
# Customize this for your specific service needs

# Choose your Python version
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# TODO: Install system dependencies your service needs
# Example: 
# RUN apt-get update && apt-get install -y \
#     postgresql-client \
#     && rm -rf /var/lib/apt/lists/*

# TODO: Copy requirements and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# TODO: Copy your source code
# COPY src/ ./src/
# COPY config/ ./config/

# TODO: Set environment variables
# ENV PYTHONPATH=/app/src
# ENV DATABASE_URL=your_database_url
# ENV API_KEY=your_api_key

# TODO: Expose the port your service runs on
# EXPOSE 5000

# TODO: Add health check for your service
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:5000/health || exit 1

# TODO: Run your application
# CMD ["python", "-m", "src.server"]

# Example for Flask:
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

# Example for FastAPI:
# CMD ["uvicorn", "src.server:app", "--host=0.0.0.0", "--port=5000"]