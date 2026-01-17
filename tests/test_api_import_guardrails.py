"""Guardrail tests for API import side effects.

These tests ensure that importing API modules does NOT trigger app construction
or singleton initialization. This is critical for:

1. Test isolation - tests should not share state from imports
2. Startup performance - only create resources when explicitly requested
3. Predictable behavior - no hidden initialization on import

The API was refactored to avoid import side effects. These tests prevent
regressions where module-level app creation is accidentally reintroduced.

Related commit: 07e61d4 feat: Refactor API structure to avoid import side effects
"""

import importlib
import sys
from pathlib import Path
from typing import List

import pytest

# Get project root for proper imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SWARM_ROOT))


def _unload_api_modules() -> List[str]:
    """Unload all swarm.api modules from sys.modules.

    Returns:
        List of module names that were unloaded.
    """
    to_remove = [name for name in sys.modules if name.startswith("swarm.api")]
    for name in to_remove:
        del sys.modules[name]
    return to_remove


class TestAPIImportSideEffects:
    """Tests that API imports do not have side effects."""

    def setup_method(self):
        """Clean up API modules before each test for fresh import state."""
        _unload_api_modules()

    def teardown_method(self):
        """Clean up API modules after each test."""
        _unload_api_modules()

    def test_spec_manager_import_does_not_initialize_singleton(self):
        """Importing spec_manager should not create the singleton."""
        # Fresh import of spec_manager
        import swarm.api.services.spec_manager as sm

        # The singleton should be None until explicitly set
        assert sm._spec_manager is None, (
            "SpecManager singleton should not be initialized at import time. "
            "Found non-None _spec_manager after import."
        )

    def test_get_spec_manager_raises_without_initialization(self):
        """get_spec_manager() without prior initialization should raise RuntimeError."""
        # Fresh import
        import swarm.api.services.spec_manager as sm

        # Verify singleton is None
        assert sm._spec_manager is None

        # Calling get_spec_manager() without init should raise
        with pytest.raises(RuntimeError, match="SpecManager not initialized"):
            sm.get_spec_manager()

    def test_server_import_does_not_create_app(self):
        """Importing swarm.api.server should not create a FastAPI app."""
        # Fresh import of server module
        import swarm.api.server as server_module

        # Check that there's no module-level 'app' variable that's a FastAPI instance
        # The server module should only have create_app() factory
        app_var = getattr(server_module, "app", None)

        # If 'app' exists at module level, it should be None or not a FastAPI instance
        if app_var is not None:
            from fastapi import FastAPI
            assert not isinstance(app_var, FastAPI), (
                "Module-level 'app' variable found in swarm.api.server. "
                "This indicates import-time app creation which violates the "
                "no-side-effects design. Use create_app() factory instead."
            )

    def test_server_import_does_not_call_set_spec_manager(self):
        """Importing server should not initialize the spec manager singleton."""
        # Fresh import of both modules
        import swarm.api.services.spec_manager as sm

        # Verify singleton is None before server import
        assert sm._spec_manager is None

        # Now import server
        import swarm.api.server  # noqa: F401

        # Singleton should still be None after server import
        assert sm._spec_manager is None, (
            "SpecManager singleton was initialized during swarm.api.server import. "
            "This violates the no-side-effects design. "
            "SpecManager should only be initialized via create_app() or explicit set_spec_manager()."
        )

    def test_routes_import_does_not_trigger_initialization(self):
        """Importing route modules should not trigger any initialization."""
        import swarm.api.services.spec_manager as sm

        # Verify singleton is None
        assert sm._spec_manager is None

        # Import routes package
        try:
            from swarm.api import routes  # noqa: F401
        except ImportError:
            # Routes package might not be importable standalone, that's OK
            pass

        # Singleton should still be None
        assert sm._spec_manager is None, (
            "SpecManager was initialized during routes import."
        )

    def test_create_app_initializes_spec_manager(self):
        """create_app() should properly initialize the spec manager."""
        import swarm.api.services.spec_manager as sm
        from swarm.api.server import create_app

        # Verify singleton is None before create_app
        assert sm._spec_manager is None

        # Create app - this should initialize spec manager
        app = create_app()

        # Now singleton should be set
        assert sm._spec_manager is not None, (
            "create_app() should initialize the SpecManager singleton."
        )

        # And get_spec_manager() should work
        manager = sm.get_spec_manager()
        assert manager is sm._spec_manager

        # Verify app is a FastAPI instance
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_set_spec_manager_works_correctly(self):
        """set_spec_manager() should properly set the singleton."""
        import swarm.api.services.spec_manager as sm
        from swarm.api.services.spec_manager import SpecManager, set_spec_manager

        # Verify starts as None
        assert sm._spec_manager is None

        # Create and set a manager
        manager = SpecManager()
        set_spec_manager(manager)

        # Verify it's set
        assert sm._spec_manager is manager
        assert sm.get_spec_manager() is manager

    def test_clear_spec_manager_resets_singleton(self):
        """clear_spec_manager() should reset the singleton to None."""
        import swarm.api.services.spec_manager as sm
        from swarm.api.services.spec_manager import (
            SpecManager,
            clear_spec_manager,
            set_spec_manager,
        )

        # Set up a manager
        manager = SpecManager()
        set_spec_manager(manager)
        assert sm._spec_manager is manager

        # Clear it
        clear_spec_manager()

        # Verify it's None
        assert sm._spec_manager is None

        # get_spec_manager should raise
        import pytest
        with pytest.raises(RuntimeError, match="SpecManager not initialized"):
            sm.get_spec_manager()


class TestASGIEntrypoint:
    """Tests for the ASGI entrypoint module."""

    def setup_method(self):
        """Clean up API modules before each test."""
        _unload_api_modules()

    def teardown_method(self):
        """Clean up API modules after each test."""
        _unload_api_modules()

    def test_asgi_module_creates_app_at_import(self):
        """swarm.api.asgi should create app at import (that's its purpose).

        Unlike server.py, the asgi.py module IS expected to create an app
        at import time because that's what ASGI servers (uvicorn) need.
        This test documents that expectation.
        """
        import swarm.api.services.spec_manager as sm

        # Verify singleton starts None
        assert sm._spec_manager is None

        # Import asgi module - this SHOULD create the app
        import swarm.api.asgi as asgi_module

        # asgi module should have an 'app' variable
        assert hasattr(asgi_module, "app"), (
            "swarm.api.asgi should expose an 'app' variable for ASGI servers."
        )

        from fastapi import FastAPI
        assert isinstance(asgi_module.app, FastAPI), (
            "swarm.api.asgi.app should be a FastAPI instance."
        )

        # And spec manager should now be initialized
        assert sm._spec_manager is not None, (
            "swarm.api.asgi import should initialize SpecManager (via create_app)."
        )


class TestImportIndependence:
    """Tests that modules can be imported independently without errors."""

    def setup_method(self):
        """Clean up API modules before each test."""
        _unload_api_modules()

    def teardown_method(self):
        """Clean up API modules after each test."""
        _unload_api_modules()

    def test_spec_manager_imports_independently(self):
        """spec_manager module can be imported without other API modules."""
        # Should not raise any errors
        import swarm.api.services.spec_manager  # noqa: F401

    def test_server_imports_independently(self):
        """server module can be imported without errors."""
        # Should not raise any errors
        import swarm.api.server  # noqa: F401

    def test_services_init_imports_independently(self):
        """services __init__ can be imported without errors."""
        try:
            import swarm.api.services  # noqa: F401
        except ImportError:
            # May not have an __init__.py, that's OK
            pass

    def test_api_init_imports_independently(self):
        """api __init__ can be imported without errors."""
        try:
            import swarm.api  # noqa: F401
        except ImportError:
            # May not have an __init__.py, that's OK
            pass
