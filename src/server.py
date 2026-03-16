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

import grpc
from src.services.resource_service import (
    HardwareService,
    InvalidHardwareRequestError,
    HardwareNotFoundError,
    InsufficientHardwareError,
)
from src.generated import hardware_pb2_grpc  # generated after running make proto

# TODO (separate branch): import hardware_pb2 for constructing HardwareListResponse
# from src.generated import hardware_pb2


class HardwareServicer(hardware_pb2_grpc.HardwareServiceServicer):

    # DONE: Servicer class defined and wired to HardwareService
    # DONE: RequestHardware implemented with full error mapping:
    #         INVALID_ARGUMENT, NOT_FOUND, FAILED_PRECONDITION

    def __init__(self, hardware_service: HardwareService):
        self.hardware_service = hardware_service

    async def RequestHardware(self, request, context):
        try:
            return await self.hardware_service.request_hardware(
                hw_set_id=request.hw_set_id,
                project_id=request.project_id,
                quantity=request.quantity,
            )
        except InvalidHardwareRequestError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except HardwareNotFoundError as exc:
            await context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
        except InsufficientHardwareError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))

    # TODO (separate branch): Implement ReturnHardware
    #   - Mirror RequestHardware error handling (same three status codes)
    #   - Call self.hardware_service.return_hardware() once implemented in service layer
    async def ReturnHardware(self, request, context):
        pass

    # TODO (separate branch): Implement GetHardwareResources
    #   - No request validation needed (takes an Empty message)
    #   - Call repository.get_all_hardware() via the service layer
    #   - Return a HardwareListResponse wrapping the list of Hardware messages
    async def GetHardwareResources(self, request, context):
        pass


# TODO (separate branch): Add serve() function to start the gRPC server
#   - Create grpc.aio.server()
#   - Instantiate HardwareRepository with a real DB session
#   - Instantiate HardwareService with the repository
#   - Add HardwareServicer to the server via hardware_pb2_grpc.add_HardwareServiceServicer_to_server()
#   - Bind to the configured port (from src/config/settings.py)
#   - Add gRPC health check service
#   - Call server.start() and server.wait_for_termination()