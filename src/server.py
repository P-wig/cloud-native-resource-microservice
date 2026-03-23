"""
gRPC Transport Layer — server.py

This is the only file in the codebase that knows about gRPC.
Its responsibilities are:
  - Define the gRPC servicer class that implements the HardwareService RPC methods
  - Receive incoming RPC requests and pass them to the service layer
  - Catch domain exceptions from the service layer and translate them into
    gRPC status codes (INVALID_ARGUMENT, NOT_FOUND, FAILED_PRECONDITION, etc.)
  - Wire together the repository, service, and gRPC server at startup
  - Handle server startup, graceful shutdown, and health checks

What does NOT belong here:
  - Business rules or validation logic  → src/services/resource_service.py
  - Database queries                    → src/repositories/resource_repository.py
  - Proto message definitions           → proto/hardware.proto
"""

import os
import asyncio
from concurrent import futures

import grpc
from src.config.settings import get_settings
from src.repositories.resource_repository import HardwareRepository
from src.services.resource_service import (
    HardwareService,
    InvalidHardwareRequestError,
    HardwareNotFoundError,
    InsufficientHardwareError,
)
from src.generated import hardware_pb2_grpc  # generated after running make proto


class HardwareServicer(hardware_pb2_grpc.HardwareServiceServicer):

    def __init__(self, hardware_service: HardwareService):
        self.hardware_service = hardware_service

    def RequestHardware(self, request, context):
        try:
            return asyncio.run(
                self.hardware_service.request_hardware(
                hw_set_id=request.hw_set_id,
                project_id=request.project_id,
                quantity=request.quantity,
                )
            )
        except InvalidHardwareRequestError as exc:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except HardwareNotFoundError as exc:
            context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
        except InsufficientHardwareError as exc:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))

    # TODO (separate branch): Implement ReturnHardware
    #   - Mirror RequestHardware error handling (same three status codes)
    #   - Call self.hardware_service.return_hardware() once implemented in service layer
    def ReturnHardware(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ReturnHardware not implemented")

    # TODO (separate branch): Implement GetHardwareResources
    #   - No request validation needed (takes an Empty message)
    #   - Call repository.get_all_hardware() via the service layer
    #   - Return a HardwareListResponse wrapping the list of Hardware messages
    def GetHardwareResources(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetHardwareResources not implemented")


async def _smoke_test_repository(repository: HardwareRepository) -> None:
    hw_set_id = "HWSetSmoke"

    collection = repository.db.get_collection(hw_set_id)
    collection.delete_many({})

    await repository.create_hardware(
        hw_set_id=hw_set_id,
        name="Smoke Test Hardware",
        capacity=4,
        available=4,
        checked_out=0,
    )
    hardware = await repository.get_hardware(hw_set_id)

    if hardware is None:
        raise RuntimeError("Smoke test failed: get_hardware returned None")

    print(
        f"Mongo smoke test OK: hw_set_id={hardware.hw_set_id}, "
        f"available={hardware.available}, checked_out={hardware.checked_out}"
    )


def serve() -> None:
    repository = HardwareRepository()
    settings = get_settings()
    try:
        if os.getenv("RUN_STARTUP_SMOKE_TEST", "false").lower() == "true":
            asyncio.run(_smoke_test_repository(repository))
        # start gRPC server normally
        hardware_service = HardwareService(repository)
        servicer = HardwareServicer(hardware_service)

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=settings.max_workers))
        hardware_pb2_grpc.add_HardwareServiceServicer_to_server(servicer, server)

        listen_addr = f"{settings.server_host}:{settings.server_port}"
        server.add_insecure_port(listen_addr)

        server.start()
        print(f"gRPC server listening on {listen_addr}")
        server.wait_for_termination()
    finally:
        repository.close()


if __name__ == "__main__":
    serve()