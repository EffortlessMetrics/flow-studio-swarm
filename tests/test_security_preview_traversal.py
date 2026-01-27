import pytest
@pytest.mark.anyio
async def test_preview_station_validation_logic():
    """Unit test for the preview_station function logic."""
    from swarm.api.routes.preview import preview_station
    from fastapi import HTTPException

    # Pass a traversal string directly to the function
    with pytest.raises(HTTPException) as excinfo:
        await preview_station(station_id="../etc/passwd")

    assert excinfo.value.status_code == 400
    assert "invalid_station_id" in str(excinfo.value.detail)

@pytest.mark.anyio
async def test_validate_flow_validation_logic():
    """Unit test for the validate_flow function logic."""
    from swarm.api.routes.preview import validate_flow
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        await validate_flow(flow_id="../etc/passwd")

    assert excinfo.value.status_code == 400
    assert "invalid_flow_id" in str(excinfo.value.detail)
