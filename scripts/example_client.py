#!/usr/bin/env python3
"""Example gRPC client for the Hardware API."""

import asyncio
import logging
import sys
from pathlib import Path

import grpc
from google.protobuf.empty_pb2 import Empty

# Add project root to path so imports like src.generated.* resolve when run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generated import hardware_pb2, hardware_pb2_grpc  # noqa: E402


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


class HardwareClient:
    def __init__(self, host: str = "localhost", port: int = 50051) -> None:
        self.target = f"{host}:{port}"
        self.channel: grpc.aio.Channel | None = None
        self.stub: hardware_pb2_grpc.HardwareServiceStub | None = None

    async def __aenter__(self) -> "HardwareClient":
        self.channel = grpc.aio.insecure_channel(self.target)
        self.stub = hardware_pb2_grpc.HardwareServiceStub(self.channel)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.channel is not None:
            await self.channel.close()

    async def list_hardware(self):
        assert self.stub is not None
        response = await self.stub.GetHardwareResources(Empty())
        return response.hardware_sets

    async def request_hardware(self, hw_set_id: str, project_id: str, quantity: int):
        assert self.stub is not None
        request = hardware_pb2.HardwareRequest(
            hw_set_id=hw_set_id,
            project_id=project_id,
            quantity=quantity,
        )
        return await self.stub.RequestHardware(request)

    async def return_hardware(self, hw_set_id: str, project_id: str, quantity: int):
        assert self.stub is not None
        request = hardware_pb2.HardwareRequest(
            hw_set_id=hw_set_id,
            project_id=project_id,
            quantity=quantity,
        )
        return await self.stub.ReturnHardware(request)


async def main() -> int:
    configure_logging()
    logger = logging.getLogger("example_client")

    # Adjust these values to match your seeded data.
    hw_set_id = "hw-set-1"
    project_id = "demo-project"
    quantity = 1

    try:
        async with HardwareClient("localhost", 50051) as client:
            logger.info("Connected to hardware service at localhost:50051")

            logger.info("Listing hardware resources...")
            hardware_sets = await client.list_hardware()
            if not hardware_sets:
                logger.warning("No hardware sets returned.")
            for item in hardware_sets:
                logger.info(
                    "hw_set_id=%s name=%s available=%s checked_out=%s capacity=%s",
                    item.hw_set_id,
                    item.name,
                    item.available,
                    item.checked_out,
                    item.capacity,
                )

            logger.info(
                "Requesting hardware: hw_set_id=%s project_id=%s quantity=%s",
                hw_set_id,
                project_id,
                quantity,
            )
            requested = await client.request_hardware(hw_set_id, project_id, quantity)
            logger.info(
                "After request: hw_set_id=%s available=%s checked_out=%s",
                requested.hw_set_id,
                requested.available,
                requested.checked_out,
            )

            logger.info(
                "Returning hardware: hw_set_id=%s project_id=%s quantity=%s",
                hw_set_id,
                project_id,
                quantity,
            )
            returned = await client.return_hardware(hw_set_id, project_id, quantity)
            logger.info(
                "After return: hw_set_id=%s available=%s checked_out=%s",
                returned.hw_set_id,
                returned.available,
                returned.checked_out,
            )

    except grpc.aio.AioRpcError as exc:
        logger.error(
            "gRPC error: code=%s details=%s",
            exc.code().name if exc.code() else "UNKNOWN",
            exc.details(),
        )
        return 1
    except Exception:
        logger.exception("Unexpected error while running example client")
        return 1

    logger.info("Example client completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))