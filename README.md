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

## ACA Architecture and Proxying

Production deployment uses two Azure Container Apps in the same ACA environment:

- `nginx-proxy` (external ingress): public entrypoint for all client traffic
- `team6` gRPC service (internal ingress): private backend only reachable from apps in the same ACA environment

### Request Path

```text
Internet Client (grpcurl)
  -> nginx-proxy.<env>.<region>.azurecontainerapps.io:443
  -> nginx-proxy container (listen 8080, HTTP/2)
  -> grpcs://team6.internal.<env>.<region>.azurecontainerapps.io:443
  -> ACA internal ingress (Envoy)
  -> team6 container gRPC listener
```

### Proxy Behavior

- NGINX terminates client-side TLS at ACA external ingress and forwards to the internal service using `grpcs`.
- Upstream SNI and Host must match the internal FQDN to avoid TLS/routing issues.
- Rate limiting is enforced in NGINX (`limit_req`) before proxying.
- Backend service reflection can still be used through the proxy (useful for contract validation).

### Testing Proxy
To test that the nginx-proxy is in fact rate-limiting, there is a shell script `test_rate_limit.sh`. It relies on the utility `grpcurl` being available. Below is the command to run and expected output:

```bash
./tests/test_rate_limiting.sh 
Target:   nginx-proxy.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443
Method:   haas.hardware.v1.HardwareService/RequestHardware
Requests: 20
Running burst test...

Summary
  Success responses      : 0
  Rate-limited responses : 20
  Other failures         : 0

PASS: Rate limiting detected.
```
## Debugging Notes (ACA + gRPC + NGINX)

Use this checklist when proxy calls fail with `Unavailable`, `502`, or `504`.

### 1) Validate listener vs ingress target port

Inside backend container:

```bash
ss -lntp
```

If app listens on `*:50052` but ACA ingress targets `50051`, proxy calls will fail.
Ensure backend listener port and ACA `targetPort` are identical.

### 2) Validate internal network reachability from proxy

Inside `nginx-proxy` container:

```bash
nc -vz -w 3 team6.internal.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io 443
```

`open` means routing is available to internal ingress.

### 3) Validate upstream protocol

For internal ACA ingress on 443, use TLS upstream in NGINX:

```nginx
grpc_ssl_server_name on;
grpc_ssl_name team6.internal.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io;
grpc_set_header Host team6.internal.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io;
grpc_pass grpcs://team6.internal.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443;
```

### 4) Interpret common failure signatures

- `504 Gateway Timeout`: upstream not reachable in time (wrong port, app cold start, network path issue).
- `502 Bad Gateway` + HTML: upstream reached but not valid gRPC response path.
- `connection refused`: no process listening on backend target port.

### 5) Keep replicas warm while troubleshooting

Cold starts can look like transient proxy failures. During debugging, set min replicas to 1 for the backend.

### 6) Use proto-driven grpcurl when needed

If reflection is unavailable/intermittent, call via local proto:

```bash
grpcurl -v -import-path proto -proto hardware/v1/hardware.proto \
  -d '{"hw_set_id":"HWSet1","project_id":"proj-abc","quantity":1}' \
  nginx-proxy.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443 \
  haas.hardware.v1.HardwareService/RequestHardware
```

## Testing

### Unit Tests

Activate the virtual environment and run pytest:

```bash
source .venv/bin/activate
python -m pytest -v
```

###
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
