import asyncio
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from swarm.api.services.run_state import RunStateManager


class TestRunStateManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runs_root = Path(self.temp_dir.name)
        self.manager = RunStateManager(self.runs_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_list_runs_async_calls_list_runs(self):
        """Test that list_runs_async calls list_runs."""
        with patch.object(self.manager, "list_runs", return_value=[]) as mock_list_runs:
            async def run_test():
                await self.manager.list_runs_async(limit=10)

            asyncio.run(run_test())
            mock_list_runs.assert_called_once_with(limit=10)

    def test_list_runs_async_returns_correct_data(self):
        """Test that list_runs_async returns data from list_runs."""
        expected_data = [{"run_id": "test-1"}]
        with patch.object(self.manager, "list_runs", return_value=expected_data):
            async def run_test():
                result = await self.manager.list_runs_async(limit=10)
                return result

            result = asyncio.run(run_test())
            self.assertEqual(result, expected_data)

if __name__ == "__main__":
    unittest.main()
