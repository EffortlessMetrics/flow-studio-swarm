"""
Tests for selftest multi-command step execution.

A selftest step declares its commands as a list. They were joined with " && "
into one string and handed to shlex.split() with shell=False, so the "&&" and
every token after it arrived as *arguments to the first command* rather than as
a shell operator. Every multi-command step therefore failed, including the
KERNEL step that blocks all merges - `ruff` was being handed `-m` from the
following `python -m compileall`.

_run_command_sequence reproduces "&&" semantics without a shell: each command
runs as its own argv, and a non-zero exit stops the sequence.
"""

import importlib
import sys
from pathlib import Path

import pytest

# selftest.py imports its config as a top-level module (`import selftest_config`),
# which only resolves with swarm/tools on sys.path - the layout it runs under
# when invoked by path. Load it the same way rather than as a package.
_TOOLS_DIR = Path(__file__).resolve().parents[1] / "swarm" / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

_selftest = importlib.import_module("selftest")
_selftest_config = importlib.import_module("selftest_config")

_run_command_sequence = _selftest._run_command_sequence
SELFTEST_STEPS = _selftest_config.SELFTEST_STEPS


def python(code: str) -> str:
    """A shell-style command string running one line of Python."""
    return f'{sys.executable} -c "{code}"'


class TestSequencing:
    """Tests for && semantics without a shell."""

    def test_single_successful_command(self):
        """One passing command yields exit 0 and its output."""
        exit_code, stdout, _, timed_out = _run_command_sequence(
            [python("print('one')")], timeout=30
        )

        assert exit_code == 0
        assert "one" in stdout
        assert not timed_out

    def test_all_commands_run_in_order(self):
        """Every command runs, and output is concatenated in order."""
        exit_code, stdout, _, _ = _run_command_sequence(
            [python("print('first')"), python("print('second')")], timeout=30
        )

        assert exit_code == 0
        assert stdout.index("first") < stdout.index("second")

    def test_failure_stops_the_sequence(self):
        """A non-zero exit short-circuits the rest, like &&."""
        exit_code, stdout, _, _ = _run_command_sequence(
            [
                python("import sys; print('ran'); sys.exit(3)"),
                python("print('should not run')"),
            ],
            timeout=30,
        )

        assert exit_code == 3
        assert "ran" in stdout
        assert "should not run" not in stdout

    def test_first_failure_exit_code_is_reported(self):
        """The reported exit code is the one that failed, not the last."""
        exit_code, _, _, _ = _run_command_sequence(
            [python("import sys; sys.exit(7)"), python("import sys; sys.exit(1)")],
            timeout=30,
        )

        assert exit_code == 7

    def test_stderr_is_captured(self):
        """Failing output on stderr is preserved for the report."""
        _, _, stderr, _ = _run_command_sequence(
            [python("import sys; print('boom', file=sys.stderr); sys.exit(1)")],
            timeout=30,
        )

        assert "boom" in stderr

    def test_empty_sequence_passes(self):
        """A step with no commands is vacuously successful."""
        exit_code, _, _, timed_out = _run_command_sequence([], timeout=30)

        assert exit_code == 0
        assert not timed_out


class TestNoShellOperatorLeakage:
    """Regression guards for the original defect.

    The bug was not that && failed to work - it was that && and everything
    after it were silently passed as arguments to the first command, which
    then failed on flags meant for the second.
    """

    def test_operator_is_never_passed_as_an_argument(self):
        """No command receives '&&' or a following command's tokens as argv."""
        exit_code, stdout, _, _ = _run_command_sequence(
            [
                python("import sys; print(len(sys.argv))"),
                python("print('second')"),
            ],
            timeout=30,
        )

        assert exit_code == 0
        # argv is [-c] only: the second command contributed no arguments.
        assert stdout.splitlines()[0] == "1"

    def test_second_command_flags_do_not_reach_the_first(self):
        """A -m in a later command is not handed to an earlier one.

        This is the exact shape of the KERNEL failure: `ruff check ...` was
        handed the `-m` belonging to `python -m compileall`.
        """
        exit_code, _, stderr, _ = _run_command_sequence(
            [
                python("import sys; sys.exit(0 if '-m' not in sys.argv else 1)"),
                f"{sys.executable} -m this",
            ],
            timeout=30,
        )

        assert exit_code == 0, f"first command saw -m from the second: {stderr}"


class TestTimeout:
    """Tests for the step-wide timeout budget."""

    def test_timeout_is_reported(self):
        """A command exceeding the budget is reported as timed out."""
        exit_code, _, stderr, timed_out = _run_command_sequence(
            [python("import time; time.sleep(30)")], timeout=1
        )

        assert timed_out
        assert exit_code == -1
        assert "timed out" in stderr.lower()

    def test_timeout_is_a_budget_for_the_whole_step(self):
        """The budget spans all commands, not each one.

        A per-command timeout would let a step exceed its declared limit by
        splitting the work across commands.
        """
        _, _, _, timed_out = _run_command_sequence(
            [python("import time; time.sleep(2)"), python("import time; time.sleep(30)")],
            timeout=3,
        )

        assert timed_out


class TestStepConfig:
    """Tests for the step command accessors."""

    def test_commands_returns_a_list(self):
        """Every configured step exposes its commands as a list."""
        for step in SELFTEST_STEPS:
            assert isinstance(step.commands(), list), step.id
            assert step.commands(), f"{step.id} has no commands"

    def test_full_command_is_display_only(self):
        """full_command joins with && for reporting."""
        step = next(s for s in SELFTEST_STEPS if len(s.commands()) > 1)

        assert " && " in step.full_command()

    @pytest.mark.parametrize(
        "step_id", [s.id for s in SELFTEST_STEPS if len(s.commands()) > 1]
    )
    def test_multi_command_steps_keep_their_commands_separate(self, step_id):
        """No step's individual command contains a shell operator.

        If one did, it would need a shell to run correctly and would fail the
        same way the joined string did.
        """
        step = next(s for s in SELFTEST_STEPS if s.id == step_id)

        for command in step.commands():
            assert "&&" not in command, f"{step_id}: {command!r} needs a shell"
            assert "||" not in command, f"{step_id}: {command!r} needs a shell"
            assert "|" not in command, f"{step_id}: {command!r} needs a shell"
