#!/usr/bin/env bash
# Compile .proto files into Python gRPC stubs.
# Run from the repo root: bash scripts/compile_protos.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROTO_DIR="$REPO_ROOT/proto"
OUT_DIR="$REPO_ROOT/gen"

python -m grpc_tools.protoc \
    -I "$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    --pyi_out="$OUT_DIR" \
    hardware/v1/hardware.proto

# Fix the import path in the generated gRPC stub so it uses a package-relative
# import instead of a bare module import.
GRPC_FILE="$OUT_DIR/hardware/v1/hardware_pb2_grpc.py"
if [[ -f "$GRPC_FILE" ]]; then
    sed -i.bak 's/^from hardware\.v1 import hardware_pb2/from gen.hardware.v1 import hardware_pb2/' "$GRPC_FILE"
    rm -f "$GRPC_FILE.bak"
fi

PB2_FILE="$OUT_DIR/hardware/v1/hardware_pb2.py"
if [[ -f "$PB2_FILE" ]]; then
    sed -i.bak 's/^from hardware\.v1 import hardware_pb2/from gen.hardware.v1 import hardware_pb2/' "$PB2_FILE"
    rm -f "$PB2_FILE.bak"
fi

echo "Proto compilation complete → $OUT_DIR/hardware/v1/"
