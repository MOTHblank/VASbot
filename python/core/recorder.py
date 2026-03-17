"""
Action Recorder Module

Provides mouse and keyboard recording functionality using pynput.
Supports recording, playback, save/load, and export to Python script.
"""

import json
import time
import threading
from typing import List, Dict, Any, Optional, Callable
from pynput import mouse, keyboard

try:
    from bot import Bot
except ImportError:
    from core.bot import Bot


class ActionRecorder:
    """Records and plays back mouse and keyboard events.
    
    Can be used standalone for recording/playback or integrated with the bot
    infrastructure for automation tasks.
    
    Event types:
        - mouse_move: x, y, timestamp
        - mouse_click: x, y, button, timestamp
        - mouse_release: x, y, button, timestamp
        - mouse_scroll: x, y, dx, dy, timestamp
        - key_press: key, timestamp
        - key_release: key, timestamp
    """
    
    def __init__(self):
        """Initialize the ActionRecorder."""
        self._events: List[Dict[str, Any]] = []
        self._is_recording = False
        self._is_paused = False
        self._start_time: Optional[float] = None
        self._pause_start_time: Optional[float] = 0
        self._total_pause_time: float = 0
        
        # pynput listeners
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Callbacks for real-time event handling
        self._on_event_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    
    def start_recording(self) -> None:
        """Start recording mouse and keyboard events.
        
        Raises:
            RuntimeError: If already recording.
        """
        if self._is_recording:
            raise RuntimeError("Already recording")
        
        self._events = []
        self._is_recording = True
        self._is_paused = False
        self._start_time = time.time()
        self._total_pause_time = 0
        self._pause_start_time = None
        
        # Start mouse listener
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self._mouse_listener.start()
        
        # Start keyboard listener
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._keyboard_listener.start()
    
    def stop_recording(self) -> None:
        """Stop recording mouse and keyboard events.
        
        Raises:
            RuntimeError: If not currently recording.
        """
        if not self._is_recording:
            raise RuntimeError("Not currently recording")
        
        # Stop listeners
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        self._is_recording = False
        self._is_paused = False
    
    def pause_recording(self) -> None:
        """Pause recording events.
        
        Raises:
            RuntimeError: If not currently recording or already paused.
        """
        if not self._is_recording:
            raise RuntimeError("Not currently recording")
        
        if self._is_paused:
            raise RuntimeError("Recording is already paused")
        
        self._is_paused = True
        self._pause_start_time = time.time()
    
    def resume_recording(self) -> None:
        """Resume recording events.
        
        Raises:
            RuntimeError: If not currently recording or not paused.
        """
        if not self._is_recording:
            raise RuntimeError("Not currently recording")
        
        if not self._is_paused:
            raise RuntimeError("Recording is not paused")
        
        # Calculate paused duration
        if self._pause_start_time:
            self._total_pause_time += time.time() - self._pause_start_time
        
        self._is_paused = False
        self._pause_start_time = None
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get the recorded events.
        
        Returns:
            List of event dictionaries.
        """
        with self._lock:
            return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear all recorded events."""
        with self._lock:
            self._events = []
    
    def is_recording(self) -> bool:
        """Check if currently recording.
        
        Returns:
            True if recording, False otherwise.
        """
        return self._is_recording
    
    def is_paused(self) -> bool:
        """Check if recording is paused.
        
        Returns:
            True if paused, False otherwise.
        """
        return self._is_paused
    
    def set_event_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set a callback for real-time event handling.
        
        Args:
            callback: Function to call for each recorded event.
        """
        self._on_event_callback = callback
    
    def save_recording(self, filepath: str) -> None:
        """Save the recording to a JSON file.
        
        Args:
            filepath: Path to save the JSON file.
            
        Raises:
            RuntimeError: If not currently recording.
            IOError: If file cannot be written.
        """
        if not self._events:
            raise RuntimeError("No events to save. Record something first.")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._events, f, indent=2)
        except IOError as e:
            raise IOError(f"Failed to save recording: {e}")
    
    def load_recording(self, filepath: str) -> None:
        """Load a recording from a JSON file.
        
        Args:
            filepath: Path to the JSON file to load.
            
        Raises:
            IOError: If file cannot be read.
            ValueError: If file format is invalid.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                events = json.load(f)
            
            if not isinstance(events, list):
                raise ValueError("Invalid recording format: expected list of events")
            
            # Validate event structure
            for event in events:
                if not isinstance(event, dict):
                    raise ValueError("Invalid recording format: expected list of event objects")
                if 'type' not in event or 'timestamp' not in event:
                    raise ValueError("Invalid event format: missing required fields")
            
            with self._lock:
                self._events = events
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except IOError as e:
            raise IOError(f"Failed to load recording: {e}")
    
    def playback(self, bot: Optional[Bot] = None, speed: float = 1.0, 
                 event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """Play back recorded events using a bot instance.
        
        Args:
            bot: Bot instance to use for playback. If None, creates a new Bot.
            speed: Playback speed multiplier (1.0 = normal, 2.0 = double speed).
            event_callback: Optional callback for each event during playback.
            
        Raises:
            ValueError: If no events to play or speed is invalid.
        """
        if not self._events:
            raise ValueError("No events to play back")
        
        if speed <= 0:
            raise ValueError("Speed must be positive")
        
        if bot is None:
            bot = Bot()
        
        callback = event_callback or self._on_event_callback
        
        # Get first event timestamp as base
        base_time = self._events[0].get('timestamp', 0)
        last_time = base_time
        
        for event in self._events:
            event_type = event.get('type', '')
            event_timestamp = event.get('timestamp', 0)
            
            # Calculate delay based on timing
            delay = (event_timestamp - last_time) / speed
            if delay > 0:
                time.sleep(delay)
            
            last_time = event_timestamp
            
            # Execute event based on type
            try:
                self._execute_event(event, bot)
            except Exception as e:
                print(f"Error executing event {event_type}: {e}")
            
            # Call callback if set
            if callback:
                callback(event)
    
    def export_to_script(self, filepath: str, script_name: str = "recorded_script") -> None:
        """Export recording to a Python script.
        
        Generates a standalone Python script that can replay the recording.
        
        Args:
            filepath: Path to save the Python script.
            script_name: Name for the generated script (used for class/function names).
            
        Raises:
            RuntimeError: If no events to export.
            IOError: If file cannot be written.
        """
        if not self._events:
            raise RuntimeError("No events to export")
        
        # Sanitize script name
        safe_name = ''.join(c if c.isalnum() else '_' for c in script_name)
        
        script_lines = [
            '"""',
            f'Auto-generated script from recording: {script_name}',
            f'Generated at: {time.strftime("%Y-%m-%d %H:%M:%S")}',
            '"""',
            '',
            'import time',
            'from core.bot import Bot',
            '',
            '',
            f'def run_{safe_name}():',
            '    """Plays back the recorded actions."""',
            '    bot = Bot()',
            '    events = [',
        ]
        
        # Add events as Python dictionaries
        for event in self._events:
            event_repr = json.dumps(event, indent=6)
            script_lines.append(f'        {event_repr},')
        
        script_lines.append('    ]')
        script_lines.append('')
        script_lines.append('    # Base timestamp for timing calculations')
        script_lines.append('    base_time = events[0]["timestamp"] if events else 0')
        script_lines.append('    last_time = base_time')
        script_lines.append('')
        script_lines.append('    for event in events:')
        script_lines.append('        event_type = event.get("type", "")')
        script_lines.append('        event_timestamp = event.get("timestamp", 0)')
        script_lines.append('        delay = event_timestamp - last_time')
        script_lines.append('        if delay > 0:')
        script_lines.append('            time.sleep(delay)')
        script_lines.append('        last_time = event_timestamp')
        script_lines.append('')
        script_lines.append('        # Execute event')
        script_lines.append('        if event_type == "mouse_move":')
        script_lines.append('            bot.move_to(event["x"], event["y"])')
        script_lines.append('        elif event_type == "mouse_click":')
        script_lines.append('            bot.click(event["x"], event["y"], event.get("button", "left"))')
        script_lines.append('        elif event_type == "mouse_scroll":')
        script_lines.append('            # Scroll is not directly supported, move to position')
        script_lines.append('            bot.move_to(event["x"], event["y"])')
        script_lines.append('        elif event_type == "key_press":')
        script_lines.append('            key = event.get("key", "")')
        script_lines.append('            if key:')
        script_lines.append('                bot.press_key(key)')
        script_lines.append('        elif event_type == "key_release":')
        script_lines.append('            pass  # Key release handled by press_key')
        script_lines.append('')
        script_lines.append('if __name__ == "__main__":')
        script_lines.append(f'    run_{safe_name}()')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(script_lines))
        except IOError as e:
            raise IOError(f"Failed to export script: {e}")
    
    def _get_timestamp(self) -> float:
        """Get timestamp adjusted for recording state.
        
        Returns:
            Adjusted timestamp in seconds.
        """
        if self._start_time is None:
            return 0
        
        timestamp = time.time() - self._start_time - self._total_pause_time
        
        # Subtract current pause duration if paused
        if self._is_paused and self._pause_start_time:
            timestamp -= (time.time() - self._pause_start_time)
        
        return timestamp
    
    def _on_mouse_move(self, x: int, y: int) -> None:
        """Handle mouse move events."""
        if not self._is_recording or self._is_paused:
            return
        
        event = {
            'type': 'mouse_move',
            'x': x,
            'y': y,
            'timestamp': self._get_timestamp()
        }
        self._add_event(event)
    
    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """Handle mouse click and release events."""
        if not self._is_recording or self._is_paused:
            return
        
        button_name = self._button_to_name(button)
        event_type = 'mouse_click' if pressed else 'mouse_release'
        
        event = {
            'type': event_type,
            'x': x,
            'y': y,
            'button': button_name,
            'timestamp': self._get_timestamp()
        }
        self._add_event(event)
    
    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Handle mouse scroll events."""
        if not self._is_recording or self._is_paused:
            return
        
        event = {
            'type': 'mouse_scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy,
            'timestamp': self._get_timestamp()
        }
        self._add_event(event)
    
    def _on_key_press(self, key) -> None:
        """Handle key press events."""
        if not self._is_recording or self._is_paused:
            return
        
        key_name = self._key_to_name(key)
        
        event = {
            'type': 'key_press',
            'key': key_name,
            'timestamp': self._get_timestamp()
        }
        self._add_event(event)
    
    def _on_key_release(self, key) -> None:
        """Handle key release events."""
        if not self._is_recording or self._is_paused:
            return
        
        key_name = self._key_to_name(key)
        
        event = {
            'type': 'key_release',
            'key': key_name,
            'timestamp': self._get_timestamp()
        }
        self._add_event(event)
    
    def _add_event(self, event: Dict[str, Any]) -> None:
        """Add an event to the recording."""
        with self._lock:
            self._events.append(event)
        
        if self._on_event_callback:
            self._on_event_callback(event)
    
    @staticmethod
    def _button_to_name(button: mouse.Button) -> str:
        """Convert pynput Button to string name."""
        if button == mouse.Button.left:
            return 'left'
        elif button == mouse.Button.right:
            return 'right'
        elif button == mouse.Button.middle:
            return 'middle'
        return str(button)
    
    @staticmethod
    def _key_to_name(key) -> str:
        """Convert pynput Key to string name."""
        if hasattr(key, 'char') and key.char:
            return key.char
        elif hasattr(key, 'name'):
            return key.name
        return str(key)
    
    @staticmethod
    def _execute_event(event: Dict[str, Any], bot: Bot) -> None:
        """Execute a single event using the bot.
        
        Args:
            event: Event dictionary to execute.
            bot: Bot instance to use.
        """
        event_type = event.get('type', '')
        
        if event_type == 'mouse_move':
            bot.move_to(event['x'], event['y'])
        
        elif event_type == 'mouse_click':
            bot.click(
                event['x'], 
                event['y'], 
                event.get('button', 'left')
            )
        
        elif event_type == 'mouse_scroll':
            # Move to position - actual scroll not supported by basic bot
            bot.move_to(event['x'], event['y'])
        
        elif event_type == 'key_press':
            key = event.get('key', '')
            if key:
                bot.press_key(key)
        
        elif event_type == 'key_release':
            # Release is handled by press_key's internal timing
            pass


# Standalone functions for simple usage

def quick_record(seconds: float = 10.0) -> List[Dict[str, Any]]:
    """Quickly record actions for a specified duration.
    
    Args:
        seconds: Duration to record in seconds.
        
    Returns:
        List of recorded events.
    """
    recorder = ActionRecorder()
    recorder.start_recording()
    
    try:
        time.sleep(seconds)
    finally:
        recorder.stop_recording()
    
    return recorder.get_events()


def quick_playback(events: List[Dict[str, Any]], speed: float = 1.0) -> None:
    """Quickly play back a list of events.
    
    Args:
        events: List of events to play.
        speed: Playback speed multiplier.
    """
    recorder = ActionRecorder()
    recorder._events = events.copy()
    recorder.playback(speed=speed)
