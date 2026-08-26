"""
Pytest Configuration and Session Teardown
Ensures backend/temp/ is automatically cleaned up after test sessions.
"""
import os
import pytest
from config import TEMP_DIR


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_dir_after_session():
    """Teardown fixture that purges all mock/ephemeral artifacts generated in TEMP_DIR."""
    yield
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass
