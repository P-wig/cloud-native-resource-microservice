from __future__ import annotations

import argparse

import grpc

from src.generated import hardware_pb2, hardware_pb2_grpc


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple gRPC client for HardwareService")
    parser.add_argument("--host", default="localhost", help="gRPC server host")
    parser.add_argument("--port", type=int, default=50051, help="gRPC server port")
    parser.add_argument("--hw-set-id", default="HWSetSmoke", help="Hardware set ID")
    parser.add_argument("--project-id", default="demo-project", help="Project ID")
    parser.add_argument("--quantity", type=int, default=1, help="Requested quantity")
    args = parser.parse_args()

    target = f"{args.host}:{args.port}"
    request_cls = getattr(hardware_pb2, "HardwareRequest")
    request = request_cls(
        hw_set_id=args.hw_set_id,
        project_id=args.project_id,
        quantity=args.quantity,
    )

    with grpc.insecure_channel(target) as channel:
        stub = hardware_pb2_grpc.HardwareServiceStub(channel)
        try:
            response = stub.RequestHardware(request, timeout=5)
            print("RequestHardware OK")
            print(
                f"hw_set_id={response.hw_set_id}, name={response.name}, "
                f"capacity={response.capacity}, available={response.available}, "
                f"checked_out={response.checked_out}"
            )
        except grpc.RpcError as exc:
            print("RequestHardware failed")
            code = getattr(exc, "code", lambda: None)()
            details = getattr(exc, "details", lambda: "")()
            status_name = code.name if code is not None else "UNKNOWN"
            print(f"status={status_name}")
            print(f"details={details}")


if __name__ == "__main__":
    main()