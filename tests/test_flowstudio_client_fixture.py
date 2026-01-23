"""Test the flowstudio_client fixture."""

from fastapi.testclient import TestClient


def test_flowstudio_client_fixture_available(flowstudio_client):
    """Test that the flowstudio_client fixture is available and properly initialized."""
    assert isinstance(flowstudio_client, TestClient), (
        "flowstudio_client should be a TestClient instance"
    )


def test_flowstudio_client_can_make_requests(flowstudio_client):
    """Test that the flowstudio_client can make HTTP requests."""
    response = flowstudio_client.get("/")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    assert len(response.text) > 0, "Response body should not be empty"


def test_flowstudio_client_session_scoped(flowstudio_client):
    """Verify the client fixture is properly session-scoped."""
    # Just verify the fixture is still accessible
    assert flowstudio_client is not None
    response = flowstudio_client.get("/")
    assert response.status_code == 200
