import unittest
from unittest.mock import patch, MagicMock
import sys
from core.recorder import ActionRecorder


class TestRecorderGenerateScript(unittest.TestCase):
    def setUp(self):
        self.recorder = ActionRecorder()

    def test_generate_script_empty_events(self):
        self.assertEqual(self.recorder.generate_script(), "")

    def test_generate_script_basic_events(self):
        self.recorder._events = [
            {"type": "mouse_move", "x": 100, "y": 200, "timestamp": 1.0},
            {
                "type": "mouse_click",
                "x": 100,
                "y": 200,
                "button": "left",
                "timestamp": 1.1,
            },
            {
                "type": "mouse_click",
                "x": 100,
                "y": 200,
                "button": "right",
                "timestamp": 1.2,
            },
            {
                "type": "mouse_scroll",
                "x": 100,
                "y": 200,
                "dx": 0,
                "dy": 1,
                "timestamp": 1.3,
            },
            {"type": "key_press", "key": "a", "timestamp": 1.4},
            {"type": "key_release", "key": "a", "timestamp": 1.5},
        ]

        script = self.recorder.generate_script()
        expected = (
            "bot.wait(0.10)\n"
            "bot.click(100, 200)\n"
            "bot.wait(0.10)\n"
            "bot.click(100, 200, 'right')\n"
            "bot.wait(0.10)\n"
            "bot.move_to(100, 200)\n"
            "bot.wait(0.10)\n"
            "bot.press_key('a')\n"
            "bot.wait(0.10)"
        )
        self.assertEqual(script, expected)

    def test_generate_script_small_delays(self):
        self.recorder._events = [
            {
                "type": "mouse_click",
                "x": 100,
                "y": 200,
                "button": "left",
                "timestamp": 1.0,
            },
            {
                "type": "key_press",
                "key": "a",
                "timestamp": 1.01,
            },  # Delay is 0.01 (<= 0.05), so no wait
        ]

        script = self.recorder.generate_script()
        expected = "bot.click(100, 200)\n" "bot.press_key('a')"
        self.assertEqual(script, expected)

    def test_generate_script_with_regions(self):
        # Create a mock module for windows_utils
        mock_windows_utils = MagicMock()
        mock_windows_utils._get_true_hwnd_rect.return_value = (
            10,
            20,
            100,
            200,
        )  # left=10, top=20

        with patch.dict("sys.modules", {"windows_utils": mock_windows_utils}):
            self.recorder._events = [
                {
                    "type": "mouse_click",
                    "x": 20,
                    "y": 30,
                    "button": "left",
                    "timestamp": 1.0,
                },  # region 0: x=10(left+0) y=20(top+0) -> 20,30 inside 20x20 region
                {
                    "type": "mouse_click",
                    "x": 50,
                    "y": 60,
                    "button": "right",
                    "timestamp": 1.1,
                },  # region 1: x=10+30=40 y=20+30=50 -> 50,60 inside 20x20 region
                {
                    "type": "mouse_click",
                    "x": 100,
                    "y": 100,
                    "button": "left",
                    "timestamp": 1.2,
                },  # Outside any region
            ]

            regions = [
                {
                    "x": 0,
                    "y": 0,
                    "width": 20,
                    "height": 20,
                },  # Real position: 10-30, 20-40
                {
                    "x": 30,
                    "y": 30,
                    "width": 20,
                    "height": 20,
                },  # Real position: 40-60, 50-70
            ]

            script = self.recorder.generate_script(regions=regions, target_hwnd=12345)

            expected = (
                "bot.click_region(0)\n"
                "bot.wait(0.10)\n"
                "bot.click_region(1, 'right')\n"
                "bot.wait(0.10)\n"
                "bot.click(100, 100)"
            )
            self.assertEqual(script, expected)

    def test_generate_script_with_regions_but_no_target_hwnd(self):
        self.recorder._events = [
            {
                "type": "mouse_click",
                "x": 20,
                "y": 30,
                "button": "left",
                "timestamp": 1.0,
            }
        ]

        regions = [{"x": 0, "y": 0, "width": 20, "height": 20}]

        # If target_hwnd is not provided, it shouldn't use click_region
        script = self.recorder.generate_script(regions=regions)

        expected = "bot.click(20, 30)"
        self.assertEqual(script, expected)


if __name__ == "__main__":
    unittest.main()
