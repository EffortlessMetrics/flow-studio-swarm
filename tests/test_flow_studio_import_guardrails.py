"""Guardrail tests for Flow Studio import side effects."""

import importlib
import sys


def test_flow_studio_app_import_has_no_app_singleton(monkeypatch):
    """flow_studio.app should only define create_app, not create it at import."""
    from fastapi import FastAPI

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


def test_shim_imports_do_not_pull_heavy_deps(monkeypatch):
    """Shim modules should stay light and avoid global instantiation."""
    import swarm.config.packs.registry as registry
    import swarm.runtime.routing.step_router as step_router

    called = {"pack_registry": False, "step_router": False}

    original_pack_init = registry.PackRegistry.__init__
    original_step_init = step_router.StepRouter.__init__

    def pack_init(self, *args, **kwargs):
        called["pack_registry"] = True
        return original_pack_init(self, *args, **kwargs)

    def step_init(self, *args, **kwargs):
        called["step_router"] = True
        return original_step_init(self, *args, **kwargs)

    monkeypatch.setattr(registry.PackRegistry, "__init__", pack_init)
    monkeypatch.setattr(step_router.StepRouter, "__init__", step_init)

    for module_name in ("swarm.config.pack_registry", "swarm.runtime.router"):
        sys.modules.pop(module_name, None)

    before = set(sys.modules)
    importlib.import_module("swarm.config.pack_registry")
    importlib.import_module("swarm.runtime.router")
    new_modules = set(sys.modules) - before

    heavy_prefixes = ("fastapi", "uvicorn", "playwright", "duckdb")
    heavy_loaded = sorted(
        name
        for name in new_modules
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in heavy_prefixes
        )
    )

    assert not heavy_loaded, f"Shim imports pulled heavy deps: {heavy_loaded}"
    assert not called["pack_registry"], "Shim import should not instantiate PackRegistry."
    assert not called["step_router"], "Shim import should not instantiate StepRouter."
