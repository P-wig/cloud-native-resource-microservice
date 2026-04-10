#!/usr/bin/env bash

set -euo pipefail

TARGET="${TARGET:-nginx-proxy.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443}"
METHOD="${METHOD:-haas.hardware.v1.HardwareService/RequestHardware}"
PAYLOAD="${PAYLOAD:-{\"hw_set_id\":\"HWSet1\",\"project_id\":\"proj-abc\",\"quantity\":1}}"
REQUESTS="${REQUESTS:-20}"

usage() {
  cat <<EOF
Usage: tests/test_rate_limiting.sh [request_count]

Sends a burst of gRPC requests with grpcurl and verifies that at least one
response is rate-limited.

Optional environment variables:
  TARGET   gRPC host:port (default: ${TARGET})
  METHOD   Fully-qualified gRPC method (default: ${METHOD})
  PAYLOAD  JSON payload sent with each request
  REQUESTS Total requests in one burst (default: ${REQUESTS})

Example:
  REQUESTS=30 tests/test_rate_limiting.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -n "${1:-}" ]]; then
  REQUESTS="$1"
fi

if ! command -v grpcurl >/dev/null 2>&1; then
  echo "ERROR: grpcurl is required but was not found in PATH." >&2
  exit 2
fi

if ! [[ "$REQUESTS" =~ ^[0-9]+$ ]] || [[ "$REQUESTS" -lt 1 ]]; then
  echo "ERROR: request_count must be a positive integer." >&2
  exit 2
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

echo "Target:   $TARGET"
echo "Method:   $METHOD"
echo "Requests: $REQUESTS"
echo "Running burst test..."

pids=()
for i in $(seq 1 "$REQUESTS"); do
  (
    grpcurl -v -d "$PAYLOAD" "$TARGET" "$METHOD" >"$tmpdir/$i.out" 2>&1 || true
  ) &
  pids+=("$!")
done

for pid in "${pids[@]}"; do
  wait "$pid"
done

rate_limited=0
success=0
other_failures=0

for i in $(seq 1 "$REQUESTS"); do
  out_file="$tmpdir/$i.out"

  if grep -Eqi '429|resource_exhausted|too many requests|rate[ -]?limit' "$out_file"; then
    rate_limited=$((rate_limited + 1))
  elif grep -Eqi '^ERROR:|Code: [A-Z_]+' "$out_file"; then
    other_failures=$((other_failures + 1))
  else
    success=$((success + 1))
  fi
done

echo
echo "Summary"
echo "  Success responses      : $success"
echo "  Rate-limited responses : $rate_limited"
echo "  Other failures         : $other_failures"

if [[ "$rate_limited" -ge 1 ]]; then
  echo
  echo "PASS: Rate limiting detected."
  exit 0
fi

echo
echo "FAIL: No rate-limited responses detected."
echo "Tip: increase REQUESTS or run again during low network jitter."
exit 1
