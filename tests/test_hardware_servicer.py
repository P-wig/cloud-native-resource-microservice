"""
TEST FILE: tests/test_hardware_servicer.py
GOAL:
Test all business logic inside of HardwareServicer, 
without using a real database. 

STRATEGY:
- Mock MongoDB collection using MagicMock
- Inject mock int _hw_col()
- Validate: 
    - return values
    - database calls
    - gRPC error codes
"""
from datetime import datetime, timezone # simulate timestamps
from unittest.mock import MagicMock # magicmock for mocking, Any flexibile matching
import pytest
from app.servicers.hardware_servicer import HardwareServicer # class under test
from gen.hardware.v1 import hardware_pb2 # import protobuf message

# Fake gRPC Context for testing error handling
class FakeContext:
    """
    Simulate the real gRPC context object,
    Services used:
    context.set_cod(...)
    context.set_details(...)
    
    Capture the valuse to test the behavior
    """
    
    def __init__(self):
        self.code = None # store status code
        self.details = None # store error message
    
    def set_code(self,code):
        self.code = code # capture status code
    
    def set_details(self, details):
        self.details = details # capture error message

# fixture creates servicer 
# a fixture is a reusable setup block that prepares test data this 
# allows pytest to inject the service into each test function
# ensuring a clean instance for each test 

@pytest.fixture 
def servicer():
    return HardwareServicer()

# fixture crate a fake context
@pytest.fixture
def fake_context():
    """
    Provide fake gRPC context. 
    """
    return FakeContext()

# add mock for mongodb collection
@pytest.fixture
def mock_collection(mocker):
    """
    Mock the _hw_col() function in hardware_servicer.
    - _hw_col() is the boundary between business logic and MongoDB
    - By mocking it, we isolate business logic completely
    - No real database is used
    """
    mocked_col= MagicMock() # fake mongodb collection
    # patch replaces -hw_col() in hardware_servicer
    mocker.patch(
        "app.servicers.hardware_servicer._hw_col",
        return_value= mocked_col
        )
    return mocked_col # provides a mock to test
 
def test_get_hardware_resources_returns_all(servicer, fake_context, mock_collection):
    now = datetime.now(timezone.utc)
    docs = [
        {
            "_id": "id-1",
            "hardwareName": "HWSet1",
            "capacity": 200,
            "available": 150, 
            "checkedOut": 50,
        "updatedAt": now
        },
        {
            "_id": "id-2",
            "hardwareName": "HWSet2",
            "capacity": 100,
            "available": 80, 
            "checkedOut": 20,
        "updatedAt": now
        }
    ]
    # simulate mondgodb cursor behavior
    cursor = MagicMock()
    cursor.limit.return_value = docs # return our fake data
    # connect mock to collection
    mock_collection.find.return_value = cursor
    
    # call function
    response = servicer.GetHardwareResources(None, fake_context)
    # verify response type
    assert isinstance(response, hardware_pb2.HardwareListResponse)
    # verify result
    assert len(response.hardware_sets) == 2
    
    # verif data mapping 
    assert response.hardware_sets[0].name == "HWSet1"
    assert response.hardware_sets[0].capacity == 200
    assert response.hardware_sets[0].available == 150
    assert response.hardware_sets[0].checked_out == 50
    
    assert response.hardware_sets[1].name == "HWSet2"
    assert response.hardware_sets[1].capacity == 100
    assert response.hardware_sets[1].available == 80
    assert response.hardware_sets[1].checked_out == 20
    # verify database call / sanity check 
    mock_collection.find.assert_called_once() # ensure find was called once
    cursor.limit.assert_called_once_with(200)
  
# request hardware success case 
# valid request --> update db --> return updated hardware
def test_request_hardware_success_updates_returns_updated_hw(servicer, fake_context, mock_collection):
    request = hardware_pb2.HardwareRequest(
        hw_set_id= "HWSet1",
        project_id = "Project1",
        quantity = 10
    )
    
    before = {
            "_id": "mongo-id-1",
            "hardwareName": "HWSet1",
            "capacity": 200,
            "available": 150, 
            "checkedOut": 50,
        "updatedAt": datetime.now(timezone.utc)
        },
    after = {
            "_id": "id-2",
            "hardwareName": "HWSet1",
            "capacity": 200,
            "available": 140, 
            "checkedOut": 60,
        "updatedAt": datetime.now(timezone.utc)
        }
    # mock sanity check
    mock_collection.find_one.side_effect = [before, after] # ensure find was called once
    response = servicer.RequestHardware(request, fake_context)
    # verify response type
    assert fake_context.code is None # no error code set
    assert fake_context.details is None # no error message set
    assert response.name == "HWSet1"
    assert response.available == 140
    assert response.checked_out == 60
    # verify database calls
    mock_collection.update_one.assert_called_once()
    update_filter, update_payload = mock_collection.update_one.call_args.args
    
    assert update_filter == {"_id": "mongo-id-1"} # correct document targeted
    assert update_payload["inc"]["available"] == -10 # available decremented by 10
    assert update_payload["inc"]["checkedOut"] == 10 # checkedOut incremented by
    assert update_payload["addToSet"]["assignedProjects"] == "Project1" # project added to assignedProjects
    assert "updatedAt" in update_payload["set"] # updatedAt field is set

# request hardware not found error case
# exceeds availability --> failed preconditon --> not found
# --> NOT_FOUND status code invalid input --> INVALID_ARGUMENT status code


# ReturnHardware 
# valid return, to many returned, and full return
# removes project 

  
    