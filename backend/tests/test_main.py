"""Automated tests for BankSim backend foundation (Phase 1)."""

import os
import pytest
from fastapi.testclient import TestClient

from main import app
from config import get_settings


@pytest.fixture(scope="module")
def client():
    """Create a test client instance for FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_check_status_code(client):
    """Test 1: GET /health returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_payload(client):
    """Test 2: Health response contains expected status and service identity."""
    response = client.get("/health")
    data = response.json()
    assert data.get("status") == "ok"
    assert "BankSim" in data.get("service", "")
    assert "environment" in data


def test_root_endpoint_metadata(client):
    """Test 3: GET / returns HTTP 200 and basic API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "online"
    assert "name" in data
    assert "version" in data
    assert data.get("docs_url") == "/docs"
    assert data.get("health_url") == "/health"
    assert data.get("api_v1_prefix") == "/api/v1"


def test_unknown_endpoint_returns_404(client):
    """Test 4: Unknown endpoints return HTTP 404."""
    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "Not Found" in data.get("detail", "")


def test_responses_do_not_expose_secrets(client, monkeypatch):
    """Test 5: Responses do not expose environment secrets or internal details."""
    # Set a canary secret in environment to verify it never appears in client output
    secret_canary = "CANARY_SECRET_SUPER_CONFIDENTIAL_KEY_998877"
    monkeypatch.setenv("SUPER_SECRET_KEY", secret_canary)

    # Test all public endpoints
    endpoints_to_check = ["/", "/health", "/non-existent-endpoint"]
    for endpoint in endpoints_to_check:
        response = client.get(endpoint)
        response_text = response.text
        # Ensure secret canary is not exposed
        assert secret_canary not in response_text
        # Ensure no tracebacks or internal file paths leaked
        assert "Traceback" not in response_text
        assert "File \"" not in response_text

    # Test that unhandled errors do not expose internal stack traces or secrets
    # TestClient raises server exceptions by default; set raise_server_exceptions=False
    # to test client-facing sanitized error responses.
    @app.get("/test-error-endpoint-internal-simulation")
    def error_route():
        raise RuntimeError(f"Unexpected database fault with token {secret_canary}")

    client_safe = TestClient(app, raise_server_exceptions=False)
    err_response = client_safe.get("/test-error-endpoint-internal-simulation")
    assert err_response.status_code == 500
    assert secret_canary not in err_response.text
    assert "Traceback" not in err_response.text
    assert err_response.json() == {"detail": "An internal server error occurred."}


def test_cors_configuration():
    """Verify that CORS settings load correctly with restrictive defaults."""
    settings = get_settings()
    assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
    # Ensure wildcard "*" is NOT permitted by default
    assert "*" not in settings.CORS_ALLOWED_ORIGINS
    assert "http://localhost:3000" in settings.CORS_ALLOWED_ORIGINS


def test_settings_reliable_env_loading_across_cwds(tmp_path, monkeypatch):
    """Test 7: Settings load reliably from project root regardless of process CWD."""
    from config import Settings, PROJECT_ROOT

    # Switch working directory to an arbitrary temporary directory
    monkeypatch.chdir(tmp_path)

    # Instantiate Settings from within the foreign working directory
    isolated_settings = Settings()
    # Confirm it still resolves project root settings
    assert isolated_settings.APP_NAME == "BankSim: Blue-Team AI Firewall"
    assert isolated_settings.AI_PROVIDER in ("gemini", "openai", "mock")


def test_settings_gemini_and_google_alias_support(monkeypatch):
    """Test 8: Settings accept both GEMINI_API_KEY and GOOGLE_API_KEY aliases."""
    from config import Settings

    # Test GOOGLE_API_KEY alias
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key-alias-123")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings_alias = Settings()
    assert settings_alias.GEMINI_API_KEY == "test-google-key-alias-123"

    # Test GEMINI_API_KEY directly
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-direct-456")
    settings_direct = Settings()
    assert settings_direct.GEMINI_API_KEY == "test-gemini-key-direct-456"

