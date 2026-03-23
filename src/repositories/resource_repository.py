"""
Data access layer implementation.

This file should contain:
- Database query logic
- Data models/schemas
- CRUD operations
- Database connection management
- Data validation and transformation
- Repository pattern implementations
"""

# TODO (separate branch): Implement update_hardware_allocation()
#   - For RequestHardware:  decrement available, increment checked_out by quantity
#   - For ReturnHardware:   increment available, decrement checked_out by quantity
#   - Return the updated Hardware proto message

# TODO (separate branch): Add get_all_hardware()
#   - Required by GetHardwareResources RPC in hardware.proto
#   - Returns a list of all Hardware records for HardwareListResponse


from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pymongo import MongoClient

from src.config.settings import get_settings
from src.generated import hardware_pb2


@dataclass
class HardwareRecord:
    hw_set_id: str
    name: str
    capacity: int
    available: int
    checked_out: int


class HardwareRepository:
    def __init__(self, db: Any | None = None):
        settings = get_settings()
        self.client: MongoClient | None = None

        if db is not None:
            self.db = db
        else:
            self.client = MongoClient(
                settings.mongo_client_uri,
                **settings.mongo_client_options,
            )
            # single database name from settings (MONGODB_DATABASE)
            self.db = self.client.get_database(settings.mongo_database_name)

    def close(self) -> None:
        if self.client is not None:
            self.client.close()

    async def get_hardware(self, hw_set_id: str):
        if not hw_set_id:
            return None

        collection = self.db.get_collection(hw_set_id)
        doc = collection.find_one({})

        if doc is None:
            return None

        available = doc.get("Availability", doc.get("available", 0))
        checked_out = doc.get("CheckedOut", doc.get("checked_out", 0))
        capacity = doc.get("Capacity", doc.get("capacity", available + checked_out))
        name = doc.get("Name", doc.get("name", hw_set_id))

        return HardwareRecord(
            hw_set_id=hw_set_id,
            name=str(name),
            capacity=int(capacity),
            available=int(available),
            checked_out=int(checked_out),
        )

    async def create_hardware(
        self,
        hw_set_id: str,
        name: str,
        capacity: int,
        available: int | None = None,
        checked_out: int = 0,
    ) -> HardwareRecord:
        if not hw_set_id:
            raise ValueError("hw_set_id is required")

        if not name:
            raise ValueError("name is required")

        if capacity < 0:
            raise ValueError("capacity must be >= 0")

        if checked_out < 0:
            raise ValueError("checked_out must be >= 0")

        normalized_available = capacity if available is None else available
        if normalized_available < 0:
            raise ValueError("available must be >= 0")

        document = {
            "Name": name,
            "Capacity": int(capacity),
            "Availability": int(normalized_available),
            "CheckedOut": int(checked_out),
        }

        collection = self.db.get_collection(hw_set_id)
        collection.insert_one(document)

        return HardwareRecord(
            hw_set_id=hw_set_id,
            name=name,
            capacity=int(capacity),
            available=int(normalized_available),
            checked_out=int(checked_out),
        )

    async def update_hardware_allocation(self, hw_set_id, project_id, quantity):
        if not hw_set_id:
            raise ValueError("hw_set_id is required")

        if quantity <= 0:
            raise ValueError("quantity must be > 0")

        _ = project_id

        current = await self.get_hardware(hw_set_id)
        if current is None:
            return None

        new_available = current.available - int(quantity)
        new_checked_out = current.checked_out + int(quantity)

        collection = self.db.get_collection(hw_set_id)
        collection.update_one(
            {},
            {
                "$set": {
                    "Name": current.name,
                    "Capacity": int(current.capacity),
                    "Availability": int(new_available),
                    "CheckedOut": int(new_checked_out),
                }
            },
            upsert=False,
        )

        hardware_cls = getattr(hardware_pb2, "Hardware")
        return hardware_cls(
            hw_set_id=current.hw_set_id,
            name=current.name,
            capacity=int(current.capacity),
            available=int(new_available),
            checked_out=int(new_checked_out),
        )