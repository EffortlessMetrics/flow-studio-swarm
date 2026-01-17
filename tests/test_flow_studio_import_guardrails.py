"""Guardrail tests for Flow Studio import side effects."""

import importlib
import sys

from fastapi import FastAPI


def test_flow_studio_app_import_has_no_app_singleton(monkeypatch):
    """flow_studio.app should only define create_app, not create it at import."""
    import swarm.tools.flow_studio.state as state

    called = {"create_state": False}

    def fake_create_state(*_args, **_kwargs):
        called["create_state"] = True
        return None

    monkeypatch.setattr(state, "create_state", fake_create_state)

    sys.modules.pop("swarm.tools.flow_studio.app", None)
    module = importlib.import_module("swarm.tools.flow_studio.app")

    assert hasattr(module, "create_app"), "flow_studio.app should expose create_app()"

    app_var = getattr(module, "app", None)
    if app_var is not None:
        assert not isinstance(app_var, FastAPI), (
            "flow_studio.app should not instantiate a FastAPI app at import time."
        )

    assert not called["create_state"], (
        "Importing flow_studio.app should not call create_state()."
    )
