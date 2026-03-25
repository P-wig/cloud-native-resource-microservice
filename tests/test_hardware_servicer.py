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
from unittest.mock import MagicMock, ANY # magicmock for mocking, Any flexibile matching
import grpc # to check gRPC status codes
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
 
# fake db data
def test_get_hardware_resources(servicer, fake_context, mock_collection):
    now = datetime.now(timezone.utc)
    docs = [
        {
            "_id": "id-1",
            "hardwareName": "HWSet1",
            "capacity": 200,
            "available": 150, 
            "checkedOut": 50,
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
    # verify result
    assert len(response.hardware_sets) == 1
    
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
    cursor.limit.assert_called_once()
  
# request hardware success case 
# valid request --> update db --> return updated hardware


# request hardware not found error case
# exceeds availability --> failed preconditon --> not found
# --> NOT_FOUND status code invalid input --> INVALID_ARGUMENT status code


# ReturnHardware 
# valid return, to many returned, and full return
# removes project 

  
    