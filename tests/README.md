# Testing Guide

This directory contains the test suite for the cloud-native hardware microservice. The tests cover the gRPC service layer (`HardwareServicer`) and database utilities.

For full project setup and running the service, see the [root README](../README.md).

## Prerequisites

- Python 3.12+
- Virtual environment (`venv`)
- Protocol Buffers compiled (see setup below)

Note: Always run test commands from the repository root directory.

## Setup

### 1. Create and Activate Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs the project and development dependencies including:
- `pytest>=8.0.0` — Test framework
- `pytest-mock>=3.12.0` — Mocking utilities
- `pytest-cov` — Code coverage reporting
- `grpcio>=1.68.1` — gRPC framework
- `pymongo>=4.16.0` — MongoDB driver

### 3. Compile Protocol Buffers

Before running tests, ensure proto files are generated.

**Note:** Proto files are already generated in this repository, so this step may not be required unless `.proto` files are modified. If you see `Nothing to be done for \`proto'` when running `make proto`, the files are already compiled.

Recommended (project standard):

```bash
make proto
```

Fallback 1 (if `make proto` is unavailable in your environment):

```bash
bash scripts/compile_protos.sh
```

Fallback 2 (manual command):

```bash
python -m grpc_tools.protoc \
  -I proto \
  --python_out=gen \
  --grpc_python_out=gen \
  --pyi_out=gen \
  proto/hardware/v1/hardware.proto
```

The generated modules are written to `gen/hardware/v1/`.

## Running Tests

### Run All Tests

```bash
python -m pytest tests/ -v
```

Note: Always run tests from the repository root directory.

Expected result: All tests should pass with no errors.

**Example output:**
```
12 passed in 0.13s
```

### Run Specific Test File

```bash
# Test HardwareServicer business logic
python -m pytest tests/test_hardware_servicer.py -v

# Test database utilities
python -m pytest tests/test_db.py -v
```

### Run Specific Test

```bash
python -m pytest tests/test_hardware_servicer.py::test_request_hardware_success_updates_returns_updated_hw -v
```

### Run with Coverage Report

```bash
python -m pytest tests/ --cov=app --cov-report=term-missing
```

This shows which lines of code in `app/` are tested.

Optional (only if your code package is under `src/` in another branch/template):

```bash
python -m pytest tests/ --cov=src
```

## Test Organization

### `test_hardware_servicer.py`

Tests the gRPC service layer (`HardwareServicer`) with mocked MongoDB collection. All database calls are mocked at the service boundary (`_hw_col` function).

**9 tests total:**

| Test | Coverage |
|------|----------|
| `test_get_hardware_resources_returns_all` | Returns list of all hardware sets with limit of 200 |
| `test_request_hardware_success_updates_returns_updated_hw` | Valid request updates available/checkedOut/assignedProjects, returns modified hardware |
| `test_request_hardware_insufficient_avail_sets_failed_precondition` | Insufficient availability returns `FAILED_PRECONDITION` status, no DB update |
| `test_request_hardware_not_found_sets_not_found` | Missing hardware set returns `NOT_FOUND` status, no DB update |
| `test_request_hardware_invalid_argument_empty_hw_set_id` | Empty hw_set_id returns `INVALID_ARGUMENT` status, no DB call |
| `test_request_hardware_invalid_argument_quantity_zero` | Zero quantity returns `INVALID_ARGUMENT` status, no DB call |
| `test_return_hardware_success_partial_return` | Partial return increments available, decrements checkedOut |
| `test_return_hardware_over_return_sets_failed_precondition` | Over-return (quantity > checkedOut) returns `FAILED_PRECONDITION`, no DB update |
| `test_return_hardware_full_return_includes_pull_project` | Full return includes `$pull` operation to remove project from assignedProjects |

### `test_db.py`

Tests database initialization and seeding utilities (`app/db.py`).

**3 tests total:**

| Test | Coverage |
|------|----------|
| `test_seed_hw_insert_initial_hw_empty` | When collection is empty, seeds initial hardware |
| `test_seed_hw_not_insert_when_not_empty` | When collection has documents, skips seeding |
| `test_get_db_raises_runtime_error_before_init` | Raises `RuntimeError` if called before `init_mongo()` |

## Test Architecture

### Mocking Strategy

Tests mock at the **service boundary** (`_hw_col` function) rather than deep in the DB layer:
-  **Faster:** No MongoDB connection needed
-  **Isolated:** Each test controls only the data it needs
-  **Focused:** Service business logic tested independently

### Fixtures

**`mock_collection`** (in `test_hardware_servicer.py`)
- Patches `app.servicers.hardware_servicer._hw_col` to return a `MagicMock`
- Used in all `HardwareServicer` tests

**`restore_client_state`** (in `test_db.py`, autouse)
- Auto-runs before and after each test
- Restores global `db_module._client` state
- Prevents cross-test pollution

### Helper Classes

**`FakeContext`** (in `test_hardware_servicer.py`)
- Captures gRPC context for asserting status codes and error messages
- Mimics `grpc.ServicerContext` interface

## Common Issues & Solutions

### Issue: `ImportError: No module named 'hardware_pb2'`
**Solution:** Run `bash scripts/compile_protos.sh` to generate proto files.

### Issue: `ModuleNotFoundError: No module named 'app'`
**Solution:** Ensure you're in the venv and installed with `pip install -e ".[dev]"`.

### Issue: Tests don't work outside venv
**Solution:** Always activate the venv before running tests:
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## CI/CD Integration

This test suite is designed for CI/CD integration and satisfies assignment requirements for automated validation:
- No external services required (all mocked)
- Runs in <1 second
- Exit code 0 on success, non-zero on failure
- Works with any CI/CD system (GitHub Actions, GitLab CI, Jenkins, etc.)
- Ensures the test suite runs automatically on every push or pull request as required by the project CI/CD pipeline

**Example GitHub Actions workflow:**
```yaml
- name: Run tests
  run: |
    make proto
    python -m pytest tests/ -v --tb=short
```

## Adding New Tests

When adding tests for new functionality:

1. **Create test function** with `test_` prefix in appropriate file
2. **Use fixtures** (e.g., `mock_collection`) to maintain consistency
3. **Mock external dependencies** (MongoDB, gRPC context)
4. **Verify behavior** with assertions and call counts
5. **Run tests** to ensure they pass

Example:
```python
def test_new_feature_happy_path(mock_collection):
    # Setup
    mock_collection.find.return_value = MagicMock()
    
    # Execute
    result = hardware_servicer.some_method()
    
    # Assert
    assert result.success == True
    mock_collection.find.assert_called_once()
```

## Performance

- **Total runtime:** < 0.15 seconds
- **Per test:** ~12ms average
- **No network overhead:** All services mocked locally

## Questions?

Refer to the inline comments in test files for detailed explanations of each test's logic and assertions.
