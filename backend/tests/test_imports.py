import subprocess
import sys

import pytest

# conftest.py imports manifest_builder first, which hides circular imports that
# only appear when a module is the first thing loaded (as uvicorn does with main).
# Each module is imported in a fresh interpreter to catch that.
MODULES = [
    "backend.app.main",
    "backend.app.services.ai.listing_generator",
    "backend.app.services.discovery",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports_cleanly_in_fresh_interpreter(module):
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
