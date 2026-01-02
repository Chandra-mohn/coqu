# tests/conftest.py - Pytest configuration
"""
Pytest configuration and shared fixtures.
"""
import pytest
from pathlib import Path


# Fixture directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def sample_cbl():
    """Return path to sample.cbl."""
    return FIXTURES_DIR / "sample.cbl"


@pytest.fixture
def caller_cbl():
    """Return path to caller.cbl."""
    return FIXTURES_DIR / "caller.cbl"


@pytest.fixture
def dateutil_cpy():
    """Return path to dateutil.cpy."""
    return FIXTURES_DIR / "dateutil.cpy"
