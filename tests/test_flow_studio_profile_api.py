#!/usr/bin/env python3
"""
Tests for Flow Studio profile API endpoints.

This module tests the profile-related endpoints in Flow Studio FastAPI:
- /api/profile - Get currently loaded profile
- /api/profiles - List available profiles

The tests verify the API contract for profile integration, including
handling of missing profiles and error responses.

See also:
- swarm/config/profile_registry.py for the profile registry implementation
- tests/test_flow_profiles.py for unit tests of the registry
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def fastapi_client():
    """Create FastAPI test client."""
    from swarm.tools.flow_studio_fastapi import app

    return TestClient(app)


# ============================================================================
# /api/profile Endpoint Tests
# ============================================================================


class TestProfileEndpoint:
    """Tests for the /api/profile endpoint."""

    def test_profile_endpoint_returns_200_or_503(self, fastapi_client):
        """Test /api/profile returns 200 (with data) or 503 (module unavailable)."""
        resp = fastapi_client.get("/api/profile")

        # Either 200 with profile data or 503 if profile registry unavailable
        assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"

    def test_profile_endpoint_response_structure(self, fastapi_client):
        """Test /api/profile response has expected structure."""
        resp = fastapi_client.get("/api/profile")

        data = resp.json()

        if resp.status_code == 200:
            # Success response must have 'profile' key
            assert "profile" in data, "Response missing 'profile' key"
            # Profile can be null (no profile loaded) or an object
            if data["profile"] is not None:
                assert isinstance(data["profile"], dict), "'profile' should be dict or null"
            else:
                # When profile is null, should have message explaining why
                assert "message" in data, (
                    "Response with null profile should include 'message' explaining why"
                )

        elif resp.status_code == 503:
            # Error response must have 'error' key
            assert "error" in data, "503 response missing 'error' key"
            assert "profile" in data, "503 response should still include 'profile' key"
            assert data["profile"] is None, "503 response profile should be null"

    def test_profile_endpoint_null_profile_message(self, fastapi_client):
        """Test /api/profile includes message when no profile is loaded."""
        resp = fastapi_client.get("/api/profile")

        if resp.status_code == 200:
            data = resp.json()
            if data["profile"] is None:
                assert "message" in data, "Null profile response should include message"
                assert isinstance(data["message"], str), "message should be string"
                assert len(data["message"]) > 0, "message should not be empty"

    def test_profile_endpoint_loaded_profile_fields(self, fastapi_client):
        """Test /api/profile returns expected fields when profile is loaded."""
        resp = fastapi_client.get("/api/profile")

        if resp.status_code == 200:
            data = resp.json()
            profile = data.get("profile")

            if profile is not None:
                # When a profile is loaded, it should have these fields
                expected_fields = ["id", "label", "loaded_at", "source_branch"]
                for field in expected_fields:
                    assert field in profile, f"Profile missing expected field '{field}'"

                # Validate field types
                assert isinstance(profile["id"], str), "profile.id should be string"
                assert isinstance(profile["label"], str), "profile.label should be string"
                # loaded_at and source_branch can be None or string
                assert profile["loaded_at"] is None or isinstance(profile["loaded_at"], str), (
                    "profile.loaded_at should be string or null"
                )
                assert profile["source_branch"] is None or isinstance(
                    profile["source_branch"], str
                ), "profile.source_branch should be string or null"


# ============================================================================
# /api/profiles Endpoint Tests
# ============================================================================


class TestProfilesListEndpoint:
    """Tests for the /api/profiles endpoint."""

    def test_profiles_endpoint_returns_200_or_503(self, fastapi_client):
        """Test /api/profiles returns 200 (with list) or 503 (module unavailable)."""
        resp = fastapi_client.get("/api/profiles")

        # Either 200 with profiles list or 503 if profile registry unavailable
        assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"

    def test_profiles_endpoint_response_structure(self, fastapi_client):
        """Test /api/profiles response has expected structure."""
        resp = fastapi_client.get("/api/profiles")

        data = resp.json()

        if resp.status_code == 200:
            # Success response must have 'profiles' key with list
            assert "profiles" in data, "Response missing 'profiles' key"
            assert isinstance(data["profiles"], list), "'profiles' should be a list"

        elif resp.status_code == 503:
            # Error response must have 'error' key
            assert "error" in data, "503 response missing 'error' key"
            # Should still have profiles key with empty list
            assert "profiles" in data, "503 response should include 'profiles' key"
            assert data["profiles"] == [], "503 response profiles should be empty list"

    def test_profiles_list_item_structure(self, fastapi_client):
        """Test each profile in list has expected fields."""
        resp = fastapi_client.get("/api/profiles")

        if resp.status_code == 200:
            data = resp.json()
            profiles = data.get("profiles", [])

            for i, profile in enumerate(profiles):
                assert isinstance(profile, dict), f"Profile {i} should be dict"
                # Each profile summary should have these fields
                expected_fields = ["id", "label", "description"]
                for field in expected_fields:
                    assert field in profile, f"Profile {i} missing expected field '{field}'"
                # Validate types
                assert isinstance(profile["id"], str), f"Profile {i}.id should be string"
                assert isinstance(profile["label"], str), f"Profile {i}.label should be string"
                # description can be empty string but should be string
                assert isinstance(profile.get("description", ""), str), (
                    f"Profile {i}.description should be string"
                )

    def test_profiles_list_no_duplicates(self, fastapi_client):
        """Test /api/profiles returns unique profile IDs."""
        resp = fastapi_client.get("/api/profiles")

        if resp.status_code == 200:
            data = resp.json()
            profiles = data.get("profiles", [])

            profile_ids = [p["id"] for p in profiles]
            unique_ids = set(profile_ids)

            assert len(profile_ids) == len(unique_ids), (
                f"Duplicate profile IDs found: "
                f"{[id for id in profile_ids if profile_ids.count(id) > 1]}"
            )


# ============================================================================
# Integration Tests
# ============================================================================


class TestProfileApiIntegration:
    """Integration tests for profile API endpoints."""

    def test_profile_and_profiles_endpoints_consistent(self, fastapi_client):
        """Test /api/profile and /api/profiles are consistent."""
        profile_resp = fastapi_client.get("/api/profile")
        profiles_resp = fastapi_client.get("/api/profiles")

        # If one is 503, both should be 503 (registry unavailable)
        if profile_resp.status_code == 503:
            assert profiles_resp.status_code == 503, (
                "If /api/profile returns 503, /api/profiles should too"
            )
        if profiles_resp.status_code == 503:
            assert profile_resp.status_code == 503, (
                "If /api/profiles returns 503, /api/profile should too"
            )

    def test_profile_endpoint_not_error_500(self, fastapi_client):
        """Test /api/profile never returns 500 internal server error."""
        resp = fastapi_client.get("/api/profile")

        assert resp.status_code != 500, (
            f"/api/profile returned 500 internal server error: {resp.text}"
        )

    def test_profiles_endpoint_not_error_500(self, fastapi_client):
        """Test /api/profiles never returns 500 internal server error."""
        resp = fastapi_client.get("/api/profiles")

        assert resp.status_code != 500, (
            f"/api/profiles returned 500 internal server error: {resp.text}"
        )

    def test_endpoints_return_json(self, fastapi_client):
        """Test profile endpoints always return JSON."""
        for endpoint in ["/api/profile", "/api/profiles"]:
            resp = fastapi_client.get(endpoint)

            content_type = resp.headers.get("content-type", "")
            assert "application/json" in content_type, (
                f"{endpoint} should return JSON, got content-type: {content_type}"
            )

            # Should be parseable JSON
            try:
                resp.json()
            except Exception as e:
                pytest.fail(f"{endpoint} returned invalid JSON: {e}")
