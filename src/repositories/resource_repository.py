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

# DONE: HardwareRepository class defined and wired to HardwareService
# DONE: get_hardware() stub in place — called by request_hardware() and return_hardware() in service layer
# DONE: update_hardware_allocation() stub in place — called after validation passes in service layer

# TODO (separate branch): Implement get_hardware()
#   - Query database by hw_set_id
#   - Return None if no record found (service layer converts this to NOT_FOUND)
#   - Return a Hardware proto message or internal dataclass on success

# TODO (separate branch): Implement update_hardware_allocation()
#   - For RequestHardware:  decrement available, increment checked_out by quantity
#   - For ReturnHardware:   increment available, decrement checked_out by quantity
#   - Return the updated Hardware proto message

# TODO (separate branch): Add get_all_hardware()
#   - Required by GetHardwareResources RPC in hardware.proto
#   - Returns a list of all Hardware records for HardwareListResponse

# TODO (separate branch): Choose and wire up a real database
#   - Replace the untyped `db` parameter with a real session type once the DB is chosen
#   - e.g. AsyncSession (SQLAlchemy), Firestore client, Mongo collection, etc.
#   - Add connection management / dependency injection in server.py


class HardwareRepository:
    def __init__(self, db):
        self.db = db

    async def get_hardware(self, hw_set_id: str):
        # query your database — return None if not found
        ...

    async def update_hardware_allocation(self, hw_set_id, project_id, quantity):
        # update available/checked_out counts, return updated Hardware proto message
        ...