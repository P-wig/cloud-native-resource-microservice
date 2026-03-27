# cloud-native-microservice

gRPC + MongoDB hardware management microservice for the Cloud Native App Team Project.

## Architecture

| Layer            | Technology              |
| ---------------- | ----------------------- |
| Transport        | gRPC (protobuf)         |
| Reverse Proxy    | nginx 1.27              |
| Language         | Python 3.12             |
| Database         | MongoDB 7               |
| Containerisation | Docker / Docker Compose |

### Why gRPC instead of Flask?

The shared contract between teams is a `.proto` file that defines a **Protocol Buffers + gRPC** service. Flask is an HTTP/REST framework and cannot natively serve protobuf-encoded gRPC calls. Instead, this service uses the `grpcio` library which:

- Speaks the gRPC wire protocol directly (HTTP/2 + protobuf).
- Auto-generates Python stubs from the `.proto` file so request/response types are strongly typed.
- Enables service reflection so clients can discover available RPCs.

### Request Flow

```
Client
  └── Request
    └── gRPC
      └── Reverse Proxy
        └── gRPC Server
          └── MongoDB
```

## Project Structure

```
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── run.py                          # gRPC server entrypoint
├── nginx/
│ ├── nginx.conf # reverse proxy + rate limiting config
│ └── logs/ # access and error logs (generated at runtime)
├── proto/
│   └── hardware/v1/hardware.proto  # shared proto contract
├── gen/
│   └── hardware/v1/                # compiled Python stubs (auto-generated)
├── app/
│   ├── config.py                   # env-based configuration
│   ├── db.py                       # MongoDB connection + seeding
│   ├── mongo_utils.py              # serialisation helpers
│   └── servicers/
│       └── hardware_servicer.py    # gRPC service implementation
└── scripts/
    └── compile_protos.sh           # proto → Python compilation
```

## Quick Start

### With Docker Compose (recommended)

```bash
docker compose up --build
```

This starts MongoDB and the gRPC service on port **50051**.

### Local Development

```bash
# Create venv and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Compile proto stubs
bash scripts/compile_protos.sh

# Start MongoDB (if not already running)
docker run -d -p 27017:27017 mongo:7

# Run the server
python run.py
```

## gRPC API

Defined in `proto/hardware/v1/hardware.proto`:

| RPC                    | Request              | Response               | Description                     |
| ---------------------- | -------------------- | ---------------------- | ------------------------------- |
| `GetHardwareResources` | `Empty`              | `HardwareListResponse` | List all hardware sets          |
| `GetHardware`          | `GetHardwareRequest` | `Hardware`             | Get a single hardware set by ID |
| `RequestHardware`      | `HardwareRequest`    | `Hardware`             | Check out units for a project   |
| `ReturnHardware`       | `HardwareRequest`    | `Hardware`             | Return units from a project     |

### Testing with grpcurl

```bash
# List services (requires reflection)
grpcurl -plaintext localhost:50051 list

# Get all hardware
grpcurl -plaintext localhost:50051 haas.hardware.v1.HardwareService/GetHardwareResources

# Check out 10 units of HWSet1 for project "proj-abc"
grpcurl -plaintext -d '{"hw_set_id":"HWSet1","project_id":"proj-abc","quantity":10}' \
  localhost:50051 haas.hardware.v1.HardwareService/RequestHardware

# Return 5 units
grpcurl -plaintext -d '{"hw_set_id":"HWSet1","project_id":"proj-abc","quantity":5}' \
  localhost:50051 haas.hardware.v1.HardwareService/ReturnHardware
```

## Deploy Application

This service is designed to be deployed as an independent container (for example: Azure Container Apps).

At runtime, clients can use **server reflection** to discover the service and available RPCs without needing the `.proto` file locally.

### Verify Deployment (Reflection)

Use `grpcurl` against the deployed endpoint to list the service methods:

```bash
grpcurl -v team6.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443 \
  list haas.hardware.v1.HardwareService

# Expected output:
# haas.hardware.v1.HardwareService.GetHardware
# haas.hardware.v1.HardwareService.GetHardwareResources
# haas.hardware.v1.HardwareService.RequestHardware
# haas.hardware.v1.HardwareService.ReturnHardware
```

### Simple Deployed Examples

```bash
# Get all hardware resources
grpcurl -v -d '{}' team6.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443 \
  haas.hardware.v1.HardwareService/GetHardwareResources

# Request (check out) 10 units of HWSet1 for project "proj-abc"
grpcurl -v -d '{"hw_set_id":"HWSet1","project_id":"proj-abc","quantity":10}' \
  team6.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443 \
  haas.hardware.v1.HardwareService/RequestHardware

# Return 5 units
grpcurl -v -d '{"hw_set_id":"HWSet1","project_id":"proj-abc","quantity":5}' \
  team6.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443 \
  haas.hardware.v1.HardwareService/ReturnHardware
```

## Testing

### Unit Tests

Activate the virtual environment and run pytest:

```bash
source .venv/bin/activate
python -m pytest -v
```



## Environment Variables

| Variable    | Default                     | Description               |
| ----------- | --------------------------- | ------------------------- |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB`  | `hardware_service`          | Database name             |
| `GRPC_PORT` | `50051`                     | Port for the gRPC server  |

## Logging

nginx logs all requests passing through the proxy to `nginx/logs/` (generated at runtime, not committed).

To stream logs live:
```bash
# Git Bash / WSL
tail -f nginx/logs/grpc_access.log

# PowerShell
Get-Content nginx/logs/grpc_access.log -Wait
```
