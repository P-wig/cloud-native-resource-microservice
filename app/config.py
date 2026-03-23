from __future__ import annotations

import os


class Config:
    # Mongo
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "hardware_service")

    # gRPC
    GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
