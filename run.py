from __future__ import annotations

import logging
import os
from concurrent import futures

import grpc
from grpc_reflection.v1alpha import reflection

from app.config import Config
from app.db import close_mongo, init_mongo, seed_hardware
from gen.hardware.v1 import hardware_pb2, hardware_pb2_grpc
from app.servicers.hardware_servicer import HardwareServicer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def serve() -> None:
    init_mongo()
    seed_hardware()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    hardware_pb2_grpc.add_HardwareServiceServicer_to_server(
        HardwareServicer(),
        server,
    )

    # Enable server reflection so clients can discover services
    service_names = (
        hardware_pb2.DESCRIPTOR.services_by_name["HardwareService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    addr = f"[::]:{Config.GRPC_PORT}"
    server.add_insecure_port(addr)
    server.start()
    logger.info("gRPC server listening on %s", addr)

    try:
        server.wait_for_termination()
    finally:
        close_mongo()


if __name__ == "__main__":
    serve()
