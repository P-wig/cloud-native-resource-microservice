from unittest.mock import MagicMock
import pytest
from app import db as db_module

@pytest.fixture(autouse=True)
def restore_client_state(): # isolate module level client between tests
    orig_client = db_module._client # save original global client
    yield # run test body
    db_module._client = orig_client # restore original global client after test
    
def test_seed_hw_interst_initial_hw_empty(monkeypatch):
    # mock db client and collection
    mock_collection = MagicMock() # fake collection object
    mock_collection.count_documents.return_value = 0 # simulate empty collection
    
    mock_db = MagicMock() # fake db object
    mock_db.__getitem__.return_value = mock_collection # db['collection'] returns mock_collection
    
    monkeypatch.setattr(db_module, "get_db", lambda: mock_db) # patch get_db to return mock_db
    
    db_module.seed_hardware() # execute function under test
    
    mock_collection.count_documents.assert_called_once_with({}) # verify count_documents called with empty filter
    mock_collection.insert_many.assert_called_once_with(db_module.INITIAL_HARDWARE) # verify insert_many called to seed data

def test_seed_hw_not_insert_when_not_empty(monkeypatch):
    # mock db client and collection
    mock_collection = MagicMock() # fake collection object
    mock_collection.count_documents.return_value = 3 # simulate existing collection
    
    mock_db = MagicMock() # fake db object
    mock_db.__getitem__.return_value = mock_collection # db['collection'] returns mock_collection
    
    monkeypatch.setattr(db_module, "get_db", lambda: mock_db) # patch get_db to return mock_db
    
    db_module.seed_hardware() # execute function under test
    
    mock_collection.count_documents.assert_called_once_with({}) # assert empty check executed
    mock_collection.insert_many.assert_not_called() # assert no insertion performed 

def test_get_db_raises_runtime_error_before_init():
    db_module._client = None # ensure client is not initialized
    # need to manually escape parenthese in regex pattern for mathching the error message
    with pytest.raises(RuntimeError, match="MongoDB not initialised – call init_mongo\\(\\) first"):
        db_module.get_db() # should raise RuntimeError if client is not initialized
    
