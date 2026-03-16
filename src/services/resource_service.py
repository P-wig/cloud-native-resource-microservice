from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.repositories.resource_repository import HardwareRepository

# DONE: Domain exceptions defined for all three gRPC error conditions
#   - InvalidHardwareRequestError  → maps to INVALID_ARGUMENT  in server.py
#   - HardwareNotFoundError        → maps to NOT_FOUND         in server.py
#   - InsufficientHardwareError    → maps to FAILED_PRECONDITION in server.py

class InvalidHardwareRequestError(Exception):
    pass

class HardwareNotFoundError(Exception):
    pass

class InsufficientHardwareError(Exception):
    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(f"requested {requested}, but only {available} available")


# DONE: HardwareService class defined and wired to repository
# DONE: request_hardware() implemented with full validation and error coverage
#   - INVALID_ARGUMENT:    missing hw_set_id, project_id, or quantity == 0
#   - NOT_FOUND:           hardware set does not exist in repository
#   - FAILED_PRECONDITION: requested quantity exceeds available inventory

# TODO (separate branch): Implement return_hardware()
#   - Same input validation as request_hardware (INVALID_ARGUMENT)
#   - Check hardware exists (NOT_FOUND)
#   - Check quantity <= hardware.checked_out — can't return more than was checked out (FAILED_PRECONDITION)
#   - Call repository.update_hardware_allocation() to release the units back

# TODO (separate branch): Add type annotations to HardwareService.__init__() once
#   HardwareRepository is implemented in src/repositories/resource_repository.py

class HardwareService:
    def __init__(self, repository: "HardwareRepository"):
        self.repository = repository

    async def request_hardware(self, hw_set_id: str, project_id: str, quantity: int):
        # Covers INVALID_ARGUMENT
        if not hw_set_id or not project_id or quantity == 0:
            raise InvalidHardwareRequestError(
                "hw_set_id, project_id, and quantity > 0 are all required"
            )

        # Covers NOT_FOUND
        hardware = await self.repository.get_hardware(hw_set_id)
        if hardware is None:
            raise HardwareNotFoundError(f"hardware set '{hw_set_id}' not found")

        # Covers FAILED_PRECONDITION
        if quantity > hardware.available:
            raise InsufficientHardwareError(quantity, hardware.available)

        return await self.repository.update_hardware_allocation(
            hw_set_id=hw_set_id,
            project_id=project_id,
            quantity=quantity,
        )

    # TODO (separate branch): implement return_hardware()
    async def return_hardware(self, hw_set_id: str, project_id: str, quantity: int):
        pass