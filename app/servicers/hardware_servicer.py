# hardware_servicer.py — gRPC service implementation
#
# This file contains the actual business logic for the HardwareService.
# It subclasses the auto-generated HardwareServiceServicer (from the proto stubs)
# and overrides each RPC method with real logic backed by MongoDB.
#
# The three RPCs implemented here are:
#
#   GetHardwareResources — fetches all hardware sets from the database and
#       returns them as a list. No input required.
#
#   RequestHardware — checks out a quantity of a hardware set for a project.
#       Validates that the set exists and has enough availability, then
#       decrements the available count and records the project as a borrower.
#
#   ReturnHardware — checks in a quantity of a hardware set from a project.
#       Validates that enough units are actually checked out, then increments
#       the available count. If the project has returned everything it borrowed,
#       it is removed from the set's borrower list.
#
# Helper functions:
#   _hw_col()       — returns the MongoDB "hardware" collection.
#   _doc_to_proto() — converts a raw MongoDB document into a Hardware proto
#                     message suitable for sending back to the client.

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
        allocations = hw.get("allocations", [])#add allocations
        has_allocations = any(a.get("project_id") == project_id for a in allocations)
        
        if has_allocations:
            _hw_col().update_one(
                {"_id": hw["_id"]},
                { 
                 "$inc": {
                        "available": -quantity, 
                        "checkedOut": quantity,
                        "allocations.$[alloc].quantity": quantity,
                },
                "$addToSet": {"assignedProjects": project_id},
                "$set": {"updatedAt": now},
            },
            array_filters=[{"alloc.project_id": project_id}],   
        )
        else:
            _hw_col().update_one(
            {"_id": hw["_id"]},
            {
                "$inc": {"available": -quantity, "checkedOut": quantity},
                "$addToSet": {"assignedProjects": project_id},
                "$push": {"allocations": {"project_id": project_id, "quantity": quantity}},
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
        
        allocations = hw.get("allocations", [])
        project_alloc = next((a for a in allocations if a.get("project_id") == project_id), None)
        if not project_alloc:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(f"Project '{project_id}' has no allocations for '{hw_set_id}'")
            return hardware_pb2.Hardware()
        
        allocated_qty = project_alloc.get("quantity", 0)
        if allocated_qty < quantity:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(
                f"Cannot return {quantity} units – project only has {allocated_qty} allocated"
            )
            return hardware_pb2.Hardware()
        
        now = datetime.now(timezone.utc)
        
        if allocated_qty == quantity:
            _hw_col().update_one(
                {"_id": hw["_id"]},
                {
                    "$inc": {"available": quantity, "checkedOut": -quantity},
                    "$pull": {
                        "allocations": {"project_id": project_id},
                        "assignedProjects": project_id,
                },
                "$set": {"updatedAt": now},
                }, #"$pull": {"assignedProjects": project_id},#},
            )
        else:
            _hw_col().update_one(
                {"_id": hw["_id"]},
                {
                    "$inc": {
                        "available": quantity,
                        "checkedOut": -quantity,
                        "allocations.$[alloc].quantity": -quantity
                    },
                    #"$inc": {"allocations.$[alloc].quantity": -quantity},
                    "$set": {"updatedAt": now},
                },
                array_filters=[{"alloc.project_id": project_id}],
            )
        
        #checked_out = hw.get("checkedOut", hw["capacity"] - hw["available"])    
            

        
        #if checked_out < quantity:
         #   context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
          #  context.set_details(
           #     f"Cannot return {quantity} units – only {checked_out} checked out"
            #)
            #return hardware_pb2.Hardware()

        now = datetime.now(timezone.utc)
        # We could calculate the new available count here, but since we're doing an atomic update
        # in the database, we can just specify the increments and let MongoDB handle it. The important
        # part is to ensure we don't allow returning more than what's checked out, which we validate above.
        # new_available = hw["available"] + quantity
        """ new_checked_out = checked_out - quantity

        update_ops: dict = {
            "$inc": {"available": quantity, "checkedOut": -quantity},
            "$set": {"updatedAt": now},
        }

        # If nothing remains checked out for this project, remove it from
        # the assignedProjects list.
        if new_checked_out == 0:
            update_ops["$pull"] = {"assignedProjects": project_id}

        _hw_col().update_one({"_id": hw["_id"]}, update_ops)"""

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
    
    def GetProjectHardware(self, request, context):# define new gRPC method
        """ Return all hardware sets assigned to a specific project. 
        This allows clients to query which hardware resources they currently 
        have checked out. """
        project_id = request.project_id # extract id from request
        
        if not project_id: # validate input
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("project_id is required")
            return hardware_pb2.HardwareListResponse(hardware_sets=[]) # returns empty response
        
        # query MongoDB collection
        #docs = list(_hw_col().find({"assignedProjects": project_id}))
        docs = list(_hw_col().find({"allocations.project_id": project_id}))
        hw_list = [_doc_to_proto(d) for d in docs] # convert to proto messages
        return hardware_pb2.HardwareListResponse(
            hardware_sets=hw_list
        )
    
    def GetProjectResourceStatus(self, request, context): # define new gRPC method
        """ Return the status of a specific hardware set for a project. 
        This allows clients to check how many units of a hardware set they 
        currently have checked out. """
        project_id = request.project_id # get the project id from the request
        
        if not project_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("project_id is required")
            return hardware_pb2.ProjectResourceStatusResponse(resources= []) 
        
        #docs = list(_hw_col().find({"assignedProjects": project_id}))
        docs = list(_hw_col().find({"allocations.project_id": project_id}))
        resources = []
        for d in docs:
            alloc = next (
                (a for a in d.get("allocations", []) if a.get("project_id") == project_id),
                None
            )
            if not alloc:
                continue
            resources.append(
                hardware_pb2.ProjectResourceStatus(
                    hw_set_id=str(d["_id"]),
                    name=d["hardwareName"],
                    quantity_checked_out=alloc.get("quantity", 0),
                    available=d["available"],
                    capacity=d["capacity"],
                )
            )
        return hardware_pb2.ProjectResourceStatusResponse(resources=resources)
        
            
        
