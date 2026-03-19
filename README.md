# Hardware Resource Microservice

A gRPC microservice for managing hardware allocation in the HaaS (Hardware as a Service) platform, built with Python.

## Features

- **gRPC API**: Type-safe API defined in `proto/hardware.proto`
- **Layered Architecture**: Servicer → Service → Repository separation of concerns
- **Structured domain errors**: `INVALID_ARGUMENT`, `NOT_FOUND`, and `FAILED_PRECONDITION` mapped cleanly from service-layer exceptions
- **Async/await**: All RPC handlers and repository calls are fully async
- **Observability**: Prometheus metrics, structured logging (structlog), and OpenTelemetry tracing wired in via dependencies

## Architecture

```
├── proto/                  # Protocol Buffer definitions
├── src/                   # Source code
│   ├── config/           # Configuration management
│   ├── services/         # gRPC service implementations
│   ├── repositories/     # Data access layer
│   ├── utils/           # Utility functions
│   ├── generated/       # Auto-generated gRPC code
│   ├── server.py        # Main server application
│   └── client.py        # Sample client implementation
├── monitoring/           # Observability configuration
├── deployments/         # Deployment manifests
└── scripts/             # Development scripts
```

## Quick Start

### Prerequisites

- Python 3.9+
- Docker (optional)
- Make (optional, for convenience)

### Development Setup

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd cloud-native-resource-microservice
   make dev-setup  # or follow manual steps below
   ```

2. **Manual setup**:
   ```bash
   # Install dependencies
   pip install -r requirements-dev.txt
   
   # Generate gRPC code
   make proto
   
   # Copy environment file
   cp .env.example .env
   ```

3. **Run the server**:
   ```bash
   make run
   # or
   python -m src.server
   ```

### Using Docker

1. **Build and run**:
   ```bash
   docker-compose up -d
   ```

2. **View logs**:
   ```bash
   docker-compose logs -f resource-service
   ```

3. **Access monitoring** (after running `make monitoring-up`):
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)
   - Jaeger: http://localhost:16686

## API Usage

### gRPC Service

The service provides the following operations:

- `CreateResource`: Create a new resource
- `GetResource`: Retrieve a resource by ID
- `UpdateResource`: Update an existing resource
- `DeleteResource`: Delete a resource
- `ListResources`: List resources with pagination
- `WatchResources`: Stream resource updates in real-time

### Example Client Usage

```python
import asyncio
from src.client import ResourceServiceClient
from src.generated.resource_service_pb2 import ResourceType

async def example():
    async with ResourceServiceClient("localhost", 50051) as client:
        # Create a resource
        resource = await client.create_resource(
            name="my-server",
            description="A compute instance",
            resource_type=ResourceType.RESOURCE_TYPE_COMPUTE,
            metadata={"region": "us-east-1"}
        )
        print(f"Created resource: {resource.id}")
        
        # Get the resource
        retrieved = await client.get_resource(resource.id)
        print(f"Retrieved: {retrieved.name}")
        
        # List all resources
        resources, next_token, total = await client.list_resources()
        print(f"Total resources: {total}")

if __name__ == "__main__":
    asyncio.run(example())
```

### Using grpcurl for testing

```bash
# List available services
grpcurl -plaintext localhost:50051 list

# Create a resource
grpcurl -plaintext -d '{
  "name": "test-resource",
  "description": "A test resource",
  "type": "RESOURCE_TYPE_COMPUTE",
  "created_by": "user123"
}' localhost:50051 resource.v1.ResourceService/CreateResource

# Get a resource
grpcurl -plaintext -d '{"id": "<resource-id>"}' \
  localhost:50051 resource.v1.ResourceService/GetResource
```

## Development

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Run all checks
make check
```

### Protocol Buffers

```bash
# Regenerate gRPC code after modifying .proto files
make proto
```

## Configuration

The service is configured via environment variables. See [.env.example](.env.example) for all options.

Key configurations:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `50051` | gRPC server port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_METRICS` | `true` | Enable Prometheus metrics |
| `ENABLE_TRACING` | `true` | Enable distributed tracing |

## Monitoring

The service includes comprehensive observability:

### Metrics
- **Prometheus metrics** on `:8080/metrics`
- Request/response counters
- Latency histograms
- Error rates

### Logging
- **Structured logging** with configurable format (JSON/text)
- Request tracing with correlation IDs
- Configurable log levels

### Tracing
- **OpenTelemetry** integration
- Jaeger-compatible traces
- Request flow visualization

### Health Checks
- **gRPC health check** service
- **Docker health checks**
- **Kubernetes readiness/liveness probes**

## Deployment

### Docker
```bash
# Build image
make docker-build

# Run container
make docker-run
```

### Docker Compose
```bash
# Start all services
make docker-compose-up

# Start monitoring stack
make monitoring-up
```

### Kubernetes
```bash
# Apply manifests (when available)
make k8s-apply
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `make check`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Documentation**: See the `docs/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions