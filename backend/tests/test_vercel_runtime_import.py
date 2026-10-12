"""Test verifying backend module import and startup in Vercel's exact runtime context.

In Vercel Serverless Functions:
- The service root 'backend/' is deployed directly to '/var/task'.
- The Lambda runtime working directory is '/var/task'.
- sys.path[0] is '/var/task' (there is no parent 'bankim' or 'backend' directory).
- Entrypoint is 'main:app'.
"""

import os
import subprocess
import sys
from pathlib import Path


def test_vercel_isolated_runtime_import():
    """Verify that main:app loads and serves requests when isolated as /var/task."""
    backend_dir = Path(__file__).resolve().parent.parent
    repo_root = backend_dir.parent

    # Run Python in an isolated subprocess with CWD = backend_dir
    # and sys.path excluding repo_root, exactly mimicking Vercel's /var/task
    test_code = """
import os, sys
from pathlib import Path

# Verify CWD is backend/
cwd = Path.cwd()

# Strip repo root from sys.path if present
sys.path = [str(cwd)] + [p for p in sys.path if Path(p).resolve() != cwd.parent.resolve() and p != '']

# Import main directly, as Vercel does for entrypoint 'main:app'
import main
from fastapi.testclient import TestClient

assert main.app is not None, "main.app must be defined"
assert main.app.title == "BankSim: Blue-Team AI Firewall"

client = TestClient(main.app)
response = client.get("/health")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
data = response.json()
assert data.get("status") == "ok"

print("VERCEL_RUNTIME_TEST_PASSED")
"""

    result = subprocess.run(
        [sys.executable, "-c", test_code],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Vercel runtime import failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "VERCEL_RUNTIME_TEST_PASSED" in result.stdout
