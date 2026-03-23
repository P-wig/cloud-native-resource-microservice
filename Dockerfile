FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy proto sources and compile
COPY proto /app/proto
COPY gen   /app/gen
COPY scripts/compile_protos.sh /app/scripts/compile_protos.sh
RUN chmod +x /app/scripts/compile_protos.sh \
    && bash /app/scripts/compile_protos.sh

# Copy application code
COPY app /app/app
COPY run.py /app/run.py

EXPOSE 50051

CMD ["python", "run.py"]
