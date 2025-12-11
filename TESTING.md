# Testing Guide

This document provides instructions for running the test suite for immich-face-to-album.

## Prerequisites

Install the package with test dependencies:

```bash
pip install -e ".[test]"
```

Or install test dependencies separately:

```bash
pip install pytest pytest-cov pytest-mock requests-mock
```

## Running Tests

### Run all tests

```bash
pytest
```

### Run with verbose output

```bash
pytest -v
```

### Run specific test file

```bash
pytest tests/test_helpers.py
pytest tests/test_api_functions.py
pytest tests/test_cli.py
```

### Run specific test class or function

```bash
pytest tests/test_helpers.py::TestChunker
pytest tests/test_cli.py::TestMultipleFacesAND::test_require_all_faces_intersection
```

### Run tests with coverage report

```bash
pytest --cov=immich_face_to_album --cov-report=term-missing
```

### Generate HTML coverage report

```bash
pytest --cov=immich_face_to_album --cov-report=html
```

The HTML report will be available in `htmlcov/index.html`.

### Run tests without coverage (faster)

```bash
pytest --no-cov
```

## Test Structure

The test suite is organized into three main files:

### 1. `tests/test_helpers.py`
Unit tests for helper functions:
- `chunker()` - Tests for asset list chunking

### 2. `tests/test_api_functions.py`
Tests for API interaction functions with mocked HTTP requests:
- `get_time_buckets()` - Fetching time buckets from Immich API
- `get_assets_for_time_bucket()` - Fetching assets for specific time buckets
- `add_assets_to_album()` - Adding assets to albums

### 3. `tests/test_cli.py`
Integration tests for the CLI interface:
- Basic CLI functionality and argument validation
- Single face synchronization
- Multiple faces with OR logic (default)
- Multiple faces with AND logic (`--require-all-faces`)
- Face exclusion with `--skip-face`
- Asset chunking for large batches
- Verbose output
- Different time bucket sizes
- Error handling

## Coverage Goals

The test suite aims for high coverage of critical paths:
- Core logic (face selection, chunking)
- API integration
- CLI interface
- Error handling

To view current coverage:

```bash
pytest --cov=immich_face_to_album --cov-report=term-missing
```

## Writing New Tests

When adding new features, please include tests that cover:
1. Happy path scenarios
2. Edge cases (empty inputs, large datasets, etc.)
3. Error handling
4. Verbose output (if applicable)

Example test structure:

```python
import pytest
from click.testing import CliRunner
from immich_face_to_album.__main__ import your_function


def test_your_feature():
    """Test description."""
    # Arrange
    # ... setup test data

    # Act
    # ... call function

    # Assert
    # ... verify results
```

## Continuous Integration

### Automated Testing

Tests run automatically on:
- Every push to the `main` branch
- Every pull request targeting `main`

The CI workflow tests against multiple Python versions (3.8, 3.9, 3.10, 3.11, 3.12) to ensure compatibility.

### GitHub Actions Workflow

The test workflow (`.github/workflows/test.yml`) performs:
1. Sets up Python environment for each version
2. Installs dependencies with `pip install -e ".[test]"`
3. Runs the full test suite with coverage
4. Uploads coverage reports to Codecov (Python 3.12 only)

### Viewing Test Results

You can view test results for any PR or commit:
1. Go to the PR or commit on GitHub
2. Click on the "Checks" tab
3. Expand the "Run Tests" workflow to see results for each Python version

### Making Tests Pass Mandatory

To require passing tests before merging PRs:
1. Go to repository Settings → Branches
2. Add a branch protection rule for `main`
3. Enable "Require status checks to pass before merging"
4. Select "Test on Python 3.12" (or all Python versions if desired)
5. Enable "Require branches to be up to date before merging"

### Running Tests Locally Before Pushing

It's recommended to run tests locally before pushing:

```bash
# Run full test suite with coverage
pytest --cov=immich_face_to_album --cov-report=term-missing

# Ensure no tests fail
pytest -v
```

## Troubleshooting

### Import errors

If you encounter import errors, ensure the package is installed in development mode:

```bash
pip install -e .
```

### Missing dependencies

If tests fail due to missing dependencies, reinstall with test extras:

```bash
pip install -e ".[test]"
```

### Pytest not found

Ensure pytest is installed:

```bash
pip install pytest
```

## Test Markers

Tests can be marked with custom markers for selective execution:

```python
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_integration():
    pass
```

Run tests by marker:

```bash
pytest -m unit
pytest -m integration
```
