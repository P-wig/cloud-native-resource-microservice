from __future__ import annotations

import logging
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from app.db import get_db
from gen.hardware.v1 import hardware_pb2, hardware_pb2_grpc

logger = logging.getLogger(__name__)


def _hw_col():
    return get_db()["hardware"]


def _doc_to_proto(doc: dict) -> hardware_pb2.Hardware:
    """Convert a Mongo hardware document into a Hardware protobuf message."""
    ts = Timestamp()
    updated = doc.get("updatedAt") or datetime.now(timezone.utc)
    ts.FromDatetime(
        updated if isinstance(updated, datetime) else datetime.now(timezone.utc)
    )

    return hardware_pb2.Hardware(
        hw_set_id=str(doc["_id"]),
        name=doc["hardwareName"],
        capacity=doc["capacity"],
        available=doc["available"],
        checked_out=doc.get("checkedOut", doc["capacity"] - doc["available"]),
        updated_at=ts,
    )


class HardwareServicer(hardware_pb2_grpc.HardwareServiceServicer):
    """Implements the HardwareService gRPC interface."""

    def GetHardwareResources(self, request, context):
        """Return all hardware sets."""
        docs = list(_hw_col().find().limit(200))
        hw_list = [_doc_to_proto(d) for d in docs]
        return hardware_pb2.HardwareListResponse(hardware_sets=hw_list)

    def RequestHardware(self, request, context):
        """Check out hardware for a project."""
        hw_set_id = request.hw_set_id
        project_id = request.project_id
        quantity = request.quantity

        if not hw_set_id or not project_id or quantity == 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("hw_set_id, project_id, and quantity > 0 are required")
            return hardware_pb2.Hardware()

        hw = _hw_col().find_one({"hardwareName": hw_set_id})
        if not hw:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Hardware set '{hw_set_id}' not found")
            return hardware_pb2.Hardware()

        if hw["available"] < quantity:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(
                f"Insufficient availability. Only {hw['available']} units available"
            )
            return hardware_pb2.Hardware()

        now = datetime.now(timezone.utc)
        _hw_col().update_one(
            {"_id": hw["_id"]},
            {
                "$inc": {"available": -quantity, "checkedOut": quantity},
                "$addToSet": {"assignedProjects": project_id},
                "$set": {"updatedAt": now},
            },
        )

        updated = _hw_col().find_one({"_id": hw["_id"]})
        if not updated:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to retrieve updated hardware")
            return hardware_pb2.Hardware()

        logger.info(
            "Checked out %d units of %s for project %s",
            quantity,
            hw_set_id,
            project_id,
        )
        return _doc_to_proto(updated)

    def ReturnHardware(self, request, context):
        """Check in hardware from a project."""
        hw_set_id = request.hw_set_id
        project_id = request.project_id
        quantity = request.quantity

        if not hw_set_id or not project_id or quantity == 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("hw_set_id, project_id, and quantity > 0 are required")
            return hardware_pb2.Hardware()

        hw = _hw_col().find_one({"hardwareName": hw_set_id})
        if not hw:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Hardware set '{hw_set_id}' not found")
            return hardware_pb2.Hardware()

        checked_out = hw.get("checkedOut", hw["capacity"] - hw["available"])
        if checked_out < quantity:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(
                f"Cannot return {quantity} units – only {checked_out} checked out"
            )
            return hardware_pb2.Hardware()

        now = datetime.now(timezone.utc)
        new_available = hw["available"] + quantity
        new_checked_out = checked_out - quantity

        update_ops: dict = {
            "$inc": {"available": quantity, "checkedOut": -quantity},
            "$set": {"updatedAt": now},
        }

        # If nothing remains checked out for this project, remove it from
        # the assignedProjects list.
        if new_checked_out == 0:
            update_ops["$pull"] = {"assignedProjects": project_id}

        _hw_col().update_one({"_id": hw["_id"]}, update_ops)

        updated = _hw_col().find_one({"_id": hw["_id"]})
        if not updated:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to retrieve updated hardware")
            return hardware_pb2.Hardware()

        logger.info(
            "Returned %d units of %s from project %s",
            quantity,
            hw_set_id,
            project_id,
        )
        return _doc_to_proto(updated)
