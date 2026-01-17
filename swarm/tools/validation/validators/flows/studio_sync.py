# swarm/tools/validation/validators/flows/studio_sync.py
"""Flow Studio synchronization validation.

Optional validation that verifies Flow Studio API is running and serving
correct data. This is a non-blocking check that produces warnings only.
"""

from swarm.validator import ValidationResult


def validate_flow_studio_sync() -> ValidationResult:
    """
    Optional: Try to connect to Flow Studio API to verify flow sync.

    Invariant 5 (optional): Flow Studio sanity check
    Returns warning only (not error) if server unavailable.
    """
    result = ValidationResult()

    # Try to connect to Flow Studio API
    try:
        import json
        import urllib.error
        import urllib.request

        url = "http://localhost:5000/api/flows"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))

                # Verify response structure
                if isinstance(data, dict) and "flows" in data:
                    return result  # Success

                result.add_warning(
                    "FLOW",
                    "http://localhost:5000/api/flows",
                    "Flow Studio API response format unexpected",
                    "Verify Flow Studio is running and serving correct data"
                )
        except (urllib.error.URLError, urllib.error.HTTPError):
            # Server not available, don't warn (optional check)
            pass
        except json.JSONDecodeError:
            result.add_warning(
                "FLOW",
                "http://localhost:5000/api/flows",
                "Flow Studio API returned invalid JSON",
                "Verify Flow Studio is running correctly"
            )
    except (ImportError, Exception):
        # If we can't import urllib or connect, just skip the check
        pass

    return result
