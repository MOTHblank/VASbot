import unittest
from unittest.mock import MagicMock
import sys

# Mock windows-specific modules before importing
mock_ctypes = MagicMock()
mock_wintypes = MagicMock()


# Using mock_ctypes instead of MagicMock as base class to avoid metaclass conflict
class MockStruct(object):
    pass


mock_ctypes.Structure = MockStruct

sys.modules["ctypes"] = mock_ctypes
sys.modules["ctypes.wintypes"] = mock_wintypes
sys.modules["win32gui"] = MagicMock()
sys.modules["win32con"] = MagicMock()
sys.modules["win32api"] = MagicMock()
sys.modules["win32process"] = MagicMock()

# Mock pywinauto as well since it has the metaclass conflict on Linux
sys.modules["pywinauto"] = MagicMock()

# Now we can import ScriptRunner
from core.script_runner import ScriptRunner


class TestScriptRunnerIsRunning(unittest.TestCase):
    def setUp(self):
        mock_gui = MagicMock()
        self.runner = ScriptRunner(mock_gui)

    def test_is_running_when_thread_is_none(self):
        """Test is_running when script_thread is None."""
        self.runner.script_thread = None
        self.assertFalse(self.runner.is_running())

    def test_is_running_when_thread_is_dead(self):
        """Test is_running when script_thread exists but is not alive."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        self.runner.script_thread = mock_thread

        self.assertFalse(self.runner.is_running())

    def test_is_running_when_thread_is_alive(self):
        """Test is_running when script_thread exists and is alive."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        self.runner.script_thread = mock_thread

        self.assertTrue(self.runner.is_running())


if __name__ == "__main__":
    unittest.main()
