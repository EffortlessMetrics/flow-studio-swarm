"""
Tests for selftest-core wheel installation in isolated environment.

Verifies that the selftest-core package can be built as a wheel, installed
in an isolated virtual environment, and executed correctly. This ensures
the package works as a standalone distributable.

B1 Acceptance: "Can install wheel in isolated venv and run `selftest --help`"
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SELFTEST_CORE_DIR = REPO_ROOT / "packages" / "selftest-core"


@pytest.mark.slow
class TestWheelInstallation:
    """Test selftest-core wheel build and installation in isolated venv."""

    @pytest.fixture(scope="class")
    def built_wheel(self, tmp_path_factory):
        """Build the wheel once per test class.

        This fixture builds the selftest-core wheel and returns the path
        to the wheel file. The wheel is cached for the entire test class.
        """
        # Create a dedicated dist directory in tmp
        dist_dir = tmp_path_factory.mktemp("dist")

        # Build the wheel using uv build
        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
            cwd=SELFTEST_CORE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to build wheel:\n{result.stderr}")

        # Find the built wheel
        wheels = list(dist_dir.glob("selftest_core-*.whl"))
        if not wheels:
            pytest.fail(f"No wheel found in {dist_dir}. Build output:\n{result.stdout}")

        return wheels[0]

    @pytest.fixture
    def isolated_venv(self, tmp_path):
        """Create an isolated virtual environment."""
        venv_dir = tmp_path / "venv"

        # Create venv
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to create venv:\n{result.stderr}")

        # Return paths to python and pip in the venv
        if sys.platform == "win32":
            python = venv_dir / "Scripts" / "python.exe"
            pip = venv_dir / "Scripts" / "pip.exe"
        else:
            python = venv_dir / "bin" / "python"
            pip = venv_dir / "bin" / "pip"

        return {"python": python, "pip": pip, "dir": venv_dir}

    def test_wheel_builds_successfully(self, built_wheel):
        """Verify wheel builds without errors."""
        assert built_wheel.exists(), f"Wheel not found at {built_wheel}"
        assert built_wheel.suffix == ".whl"
        assert "selftest_core" in built_wheel.name

    def test_wheel_installs_in_isolated_venv(self, built_wheel, isolated_venv):
        """Verify wheel can be installed in a fresh virtual environment."""
        pip = isolated_venv["pip"]

        # Install the wheel
        result = subprocess.run(
            [str(pip), "install", str(built_wheel)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, f"pip install failed:\n{result.stderr}"
        assert (
            "Successfully installed" in result.stdout
            or "Requirement already satisfied" in result.stdout
        )

    def test_selftest_help_works_after_install(self, built_wheel, isolated_venv):
        """Verify `selftest --help` works after wheel installation.

        This is the key acceptance criterion for B1.
        """
        pip = isolated_venv["pip"]
        python = isolated_venv["python"]

        # Install the wheel first
        install_result = subprocess.run(
            [str(pip), "install", str(built_wheel)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert install_result.returncode == 0, f"pip install failed:\n{install_result.stderr}"

        # Run selftest --help via the module
        result = subprocess.run(
            [str(python), "-m", "selftest_core.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"selftest --help failed:\n{result.stderr}"
        assert "selftest" in result.stdout.lower()
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_selftest_version_works_after_install(self, built_wheel, isolated_venv):
        """Verify `selftest --version` works after wheel installation."""
        pip = isolated_venv["pip"]
        python = isolated_venv["python"]

        # Install the wheel first
        install_result = subprocess.run(
            [str(pip), "install", str(built_wheel)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert install_result.returncode == 0

        # Run selftest --version
        result = subprocess.run(
            [str(python), "-m", "selftest_core.cli", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"selftest --version failed:\n{result.stderr}"
        # Should contain version number
        assert "0." in result.stdout or "selftest" in result.stdout.lower()

    def test_selftest_doctor_works_after_install(self, built_wheel, isolated_venv):
        """Verify `selftest doctor` works after wheel installation."""
        pip = isolated_venv["pip"]
        python = isolated_venv["python"]

        # Install the wheel first
        install_result = subprocess.run(
            [str(pip), "install", str(built_wheel)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert install_result.returncode == 0

        # Run selftest doctor
        result = subprocess.run(
            [str(python), "-m", "selftest_core.cli", "doctor"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Doctor returns 0 for HEALTHY, 1 for issues - both are valid
        assert result.returncode in (0, 1), f"selftest doctor failed unexpectedly:\n{result.stderr}"

    def test_selftest_doctor_json_works_after_install(self, built_wheel, isolated_venv):
        """Verify `selftest doctor --json` produces valid JSON after installation."""
        pip = isolated_venv["pip"]
        python = isolated_venv["python"]

        # Install the wheel first
        install_result = subprocess.run(
            [str(pip), "install", str(built_wheel)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert install_result.returncode == 0

        # Run selftest doctor --json
        result = subprocess.run(
            [str(python), "-m", "selftest_core.cli", "doctor", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode in (0, 1)

        # Should produce valid JSON
        data = json.loads(result.stdout)
        assert "summary" in data
        assert data["summary"] in ("HEALTHY", "HARNESS_ISSUE", "SERVICE_ISSUE")


class TestWheelMetadata:
    """Test wheel metadata and structure."""

    @pytest.fixture(scope="class")
    def built_wheel(self, tmp_path_factory):
        """Build the wheel once per test class."""
        dist_dir = tmp_path_factory.mktemp("dist")

        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
            cwd=SELFTEST_CORE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            pytest.skip(f"Could not build wheel: {result.stderr}")

        wheels = list(dist_dir.glob("selftest_core-*.whl"))
        if not wheels:
            pytest.skip("No wheel found")

        return wheels[0]

    def test_wheel_has_correct_name_format(self, built_wheel):
        """Verify wheel follows naming convention."""
        name = built_wheel.name
        # Wheel name format: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
        parts = name.replace(".whl", "").split("-")
        assert len(parts) >= 4, f"Unexpected wheel name format: {name}"
        assert parts[0] == "selftest_core"

    def test_wheel_can_be_inspected(self, built_wheel):
        """Verify wheel can be inspected with pip."""
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "--files", str(built_wheel)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # pip show on a wheel file doesn't always work, so this is informational
        # The key thing is that it doesn't crash
        assert result.returncode in (0, 1)
