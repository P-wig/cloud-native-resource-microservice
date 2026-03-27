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
import grpc  # import grpc to assert status codes
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

# request hardware success case # ReturnHardware 
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
            "assignedProjects": []
        }
    after = {
            "_id": "mongo-id-1",
            "hardwareName": "HWSet1",
            "capacity": 200,
            "available": 140, 
            "checkedOut": 60,
            "assignedProjects": ["Project1"]
        }
    # mock sanity check
    mock_collection.find_one.side_effect = [before, after] # ensure find was called once
    response = servicer.RequestHardware(request, fake_context)
    # verify response type
    assert fake_context.code is None # no error code set
    assert fake_context.details is None # no error message set
    # verify response data
    assert response.name == "HWSet1"
    assert response.available == 140
    assert response.checked_out == 60
    # verify database calls
    mock_collection.update_one.assert_called_once()
    update_filter, update_payload = mock_collection.update_one.call_args.args
    
    assert update_filter == {"_id": "mongo-id-1"} # correct document targeted
    assert update_payload["$inc"]["available"] == -10 # available decremented by 10
    assert update_payload["$inc"]["checkedOut"] == 10 # checkedOut incremented by
    
    assert update_payload["$addToSet"]["assignedProjects"] == "Project1" # project added to assignedProjects
    assert "updatedAt" in update_payload["$set"] # updatedAt field is set

# request hardware not found error case
# exceeds availability --> failed preconditon --> not found
# --> NOT_FOUND status code invalid input --> INVALID_ARGUMENT status code
def test_request_hardware_insufficient_avail_sets_failed_precondition(servicer, fake_context, mock_collection):
    request = hardware_pb2.HardwareRequest(
        hw_set_id= "HWSet1",
        project_id = "Project1",
        quantity = 10
    )
    
    mock_collection.find_one.return_value    = {
            "_id": "mongo-id-1",
            "hardwareName": "HWSet1",
            "capacity": 200,
            "available": 5, 
            "checkedOut": 195,
            "updatedAt": datetime.now(timezone.utc)
        }
    response = servicer.RequestHardware(request, fake_context)
    
    # verify error handling
    assert fake_context.code == grpc.StatusCode.FAILED_PRECONDITION #assert expected grpc code
    assert "Insufficient availability. Only 5 units available" in fake_context.details # assert expected grpc dtails text
    assert response == hardware_pb2.Hardware() # assert empty response on error
   
    # verify no database update attempted
    mock_collection.update_one.assert_not_called() # assert no update attempted on failure

def test_request_hardware_not_found_sets_not_found(servicer, fake_context, mock_collection):  # test hardware not found branch
    request = hardware_pb2.HardwareRequest(hw_set_id="UNKNOWN", project_id="proj-1", quantity=10)  # build request with unknown set id
    mock_collection.find_one.return_value = None  # make lookup return no document

    response = servicer.RequestHardware(request, fake_context)  # call RequestHardware

    assert fake_context.code == grpc.StatusCode.NOT_FOUND  # assert expected grpc code
    assert "UNKNOWN" in fake_context.details  # assert not-found message includes requested id
    assert response == hardware_pb2.Hardware()  # assert empty hardware returned on failure
    mock_collection.update_one.assert_not_called()  # assert no update executed


def test_request_hardware_invalid_argument_empty_hw_set_id(servicer, fake_context, mock_collection):  # test invalid request with empty hw_set_id
    request = hardware_pb2.HardwareRequest(hw_set_id="", project_id="proj-1", quantity=10)  # build invalid request

    response = servicer.RequestHardware(request, fake_context)  # call RequestHardware

    assert fake_context.code == grpc.StatusCode.INVALID_ARGUMENT  # assert invalid argument code
    assert "required" in fake_context.details  # assert validation details message
    assert response == hardware_pb2.Hardware()  # assert empty response on validation failure
    mock_collection.find_one.assert_not_called()  # assert DB lookup skipped
    mock_collection.update_one.assert_not_called()  # assert DB update skipped


def test_request_hardware_invalid_argument_quantity_zero(servicer, fake_context, mock_collection):  # test invalid request with zero quantity
    request = hardware_pb2.HardwareRequest(hw_set_id="HWSet1", project_id="proj-1", quantity=0)  # build invalid request

    response = servicer.RequestHardware(request, fake_context)  # call RequestHardware

    assert fake_context.code == grpc.StatusCode.INVALID_ARGUMENT  # assert invalid argument code
    assert "required" in fake_context.details  # assert validation details message
    assert response == hardware_pb2.Hardware()  # assert empty response on validation failure
    mock_collection.find_one.assert_not_called()  # assert DB lookup skipped
    mock_collection.update_one.assert_not_called()  # assert DB update skipped


def test_return_hardware_success_partial_return(servicer, fake_context, mock_collection):  # test successful partial return branch
    request = hardware_pb2.HardwareRequest(hw_set_id="HWSet1", project_id="proj-1", quantity=5)  # build valid return request

    before = {  # fake pre-return DB document
        "_id": "mongo-id-1",  # fake id field
        "hardwareName": "HWSet1",  # matching hardware set
        "capacity": 200,  # capacity value
        "available": 140,  # available before return
        "checkedOut": 60,  # checkedOut before return
        "assignedProjects": ["proj-1"],  # assigned project list
        "updatedAt": datetime.now(timezone.utc),  # timestamp
    }  # end pre-return doc
    after = {  # fake post-return DB document
        "_id": "mongo-id-1",  # same id after update
        "hardwareName": "HWSet1",  # same set name
        "capacity": 200,  # same capacity
        "available": 145,  # available increased by 5
        "checkedOut": 55,  # checkedOut decreased by 5
        "assignedProjects": ["proj-1"],  # project still present after partial return
        "updatedAt": datetime.now(timezone.utc),  # timestamp
    }  # end post-return doc

    mock_collection.find_one.side_effect = [before, after]  # first lookup before update, second after update

    response = servicer.ReturnHardware(request, fake_context)  # call ReturnHardware

    assert fake_context.code is None  # assert success path set no error code
    assert response.available == 145  # assert updated available value
    assert response.checked_out == 55  # assert updated checked_out value

    mock_collection.update_one.assert_called_once()  # assert update executed once
    update_filter, update_payload = mock_collection.update_one.call_args.args  # capture update call args
    assert update_filter == {"_id": "mongo-id-1"}  # assert update targeted correct doc
    assert update_payload["$inc"]["available"] == 5  # assert available increment
    assert update_payload["$inc"]["checkedOut"] == -5  # assert checkedOut decrement
    assert "$pull" not in update_payload  # assert no project removal on partial return


def test_return_hardware_over_return_sets_failed_precondition(servicer, fake_context, mock_collection):  # test over-return failure branch
    request = hardware_pb2.HardwareRequest(hw_set_id="HWSet1", project_id="proj-1", quantity=15)  # request returns too many units
    mock_collection.find_one.return_value = {  # mock current state with only 10 checked out
        "_id": "mongo-id-1",  # fake id field
        "hardwareName": "HWSet1",  # matching set name
        "capacity": 200,  # capacity field
        "available": 190,  # currently available
        "checkedOut": 10,  # only 10 checked out
        "assignedProjects": ["proj-1"],  # project assigned
        "updatedAt": datetime.now(timezone.utc),  # timestamp
    }  # end mocked

    response = servicer.ReturnHardware(request, fake_context)  # call ReturnHardware

    assert fake_context.code == grpc.StatusCode.FAILED_PRECONDITION  # assert expected grpc code
    assert "only 10 checked out" in fake_context.details  # assert expected details content
    assert response == hardware_pb2.Hardware()  # assert empty response on failure
    mock_collection.update_one.assert_not_called()  # assert no update attempted


def test_return_hardware_full_return_includes_pull_project(servicer, fake_context, mock_collection):  # test full return removes project branch
    request = hardware_pb2.HardwareRequest(hw_set_id="HWSet1", project_id="proj-1", quantity=10)  # request returns all checked-out units

    before = {  # fake pre-return state
        "_id": "mongo-id-1",  # fake id field
        "hardwareName": "HWSet1",  # matching set name
        "capacity": 200,  # capacity field
        "available": 140,  # available before return
        "checkedOut": 10,  # checkedOut before return
        "assignedProjects": ["proj-1"],  # project currently assigned
        "updatedAt": datetime.now(timezone.utc),  # timestamp
    }  # end pre-return state
    after = {  # fake post-return state
        "_id": "mongo-id-1",  # same id after update
        "hardwareName": "HWSet1",  # same set name
        "capacity": 200,  # same capacity
        "available": 150,  # available increased by 10
        "checkedOut": 0,  # checkedOut reduced to zero
        "assignedProjects": [],  # project removed
        "updatedAt": datetime.now(timezone.utc),  # timestamp
    }  # end post-return

    mock_collection.find_one.side_effect = [before, after]  # two-stage lookup around update

    response = servicer.ReturnHardware(request, fake_context)  # call ReturnHardware

    assert fake_context.code is None  # assert success path has no grpc error
    assert response.available == 150  # assert final available value
    assert response.checked_out == 0  # assert final checked_out value

    mock_collection.update_one.assert_called_once()  # assert update executed once
    _, update_payload = mock_collection.update_one.call_args.args  # capture update payload
    assert update_payload["$inc"]["available"] == 10  # assert available increment
    assert update_payload["$inc"]["checkedOut"] == -10  # assert checkedOut decrement
    assert update_payload["$pull"]["assignedProjects"] == "proj-1"  # assert project pull applied on full return
