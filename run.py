# run.py — gRPC server entrypoint
#
# This file is responsible for starting the hardware microservice. It:
#   1. Opens a connection to MongoDB and seeds it with default hardware sets
#      if the database is empty.
#   2. Creates a gRPC server backed by a thread pool (handles concurrent requests).
#   3. Registers HardwareServicer as the handler for all incoming RPC calls —
#      this is the class that contains the actual business logic (query Mongo,
#      validate input, return results).
#   4. Enables server reflection so tools like grpcurl can discover available
#      RPCs without needing the .proto file locally.
#   5. Binds to the configured port (default 50051) and starts listening.
#   6. Blocks until the process is interrupted, then closes the Mongo connection
#      cleanly on the way out.
#
# To run: python run.py
from __future__ import annotations

import logging
# import os
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
