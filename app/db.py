from __future__ import annotations

import logging

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from app.config import Config

logger = logging.getLogger(__name__)

_client: MongoClient | None = None


def init_mongo() -> None:
    global _client
    try:
        _client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
        logger.info("MongoDB connected successfully")
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


def get_db() -> Database:
    if _client is None:
        raise RuntimeError("MongoDB not initialised – call init_mongo() first")
    return _client[Config.MONGO_DB]


def close_mongo() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


INITIAL_HARDWARE = [
    {
        "hardwareName": "HWSet1",
        "capacity": 200,
        "available": 200,
        "checkedOut": 0,
        "assignedProjects": [],
    },
    {
        "hardwareName": "HWSet2",
        "capacity": 200,
        "available": 200,
        "checkedOut": 0,
        "assignedProjects": [],
    },
    {
        "hardwareName": "HWSet3",
        "capacity": 100,
        "available": 100,
        "checkedOut": 0,
        "assignedProjects": [],
    },
    {
        "hardwareName": "HWSet4",
        "capacity": 100,
        "available": 100,
        "checkedOut": 0,
        "assignedProjects": [],
    },
]


def seed_hardware() -> None:
    db = get_db()
    col = db["hardware"]
    if col.count_documents({}) == 0:
        col.insert_many(INITIAL_HARDWARE)
        logger.info("Seeded %d hardware sets", len(INITIAL_HARDWARE))
