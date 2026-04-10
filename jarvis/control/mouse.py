import pyautogui
import time
from config import SCREEN_W, SCREEN_H, SMOOTHING, CLICK_DEBOUNCE, CURSOR_MARGIN, IS_MAC

pyautogui.FAILSAFE = False  # Disable corner failsafe so hand can reach edges
pyautogui.PAUSE = 0         # No artificial delay between pyautogui calls

# Minimum normalized movement required before the cursor moves.
# Raise this to require more finger movement (0.0 = off, 0.02 = default, 0.05 = very sluggish).
DEADZONE = 0.02

# Scroll ticks fired per second while the gesture is held.
SCROLL_RATE = 1000

# How many ticks per scroll event (higher = faster scroll per tick).
SCROLL_TICKS = 3


class MouseController:
    def __init__(self):
        self._cursor_x = SCREEN_W / 2
        self._cursor_y = SCREEN_H / 2
        self._last_click_time = 0
        self._clicking = False
        self._right_clicking = False
        self._last_norm_x = None
        self._last_norm_y = None
        self._last_scroll_time = 0.0

    def move(self, norm_x, norm_y):
        """
        Move cursor to normalized coords [0,1].
        Applies a deadzone so small finger tremors don't move the cursor.
        Applies exponential smoothing to reduce jitter.
        Remaps the active hand zone (inside CURSOR_MARGIN) to the full screen,
        so the hand doesn't need to reach the frame edge.
        """
        # Remap [margin, 1-margin] → [0, 1] so full screen is reachable from center of frame
        m = CURSOR_MARGIN
        norm_x = max(0.0, min(1.0, (norm_x - m) / (1.0 - 2 * m)))
        norm_y = max(0.0, min(1.0, (norm_y - m) / (1.0 - 2 * m)))

        # Deadzone: ignore movement smaller than DEADZONE relative to last position
        if self._last_norm_x is not None:
            dx = abs(norm_x - self._last_norm_x)
            dy = abs(norm_y - self._last_norm_y)
            if dx < DEADZONE and dy < DEADZONE:
                return  # Too little movement — don't update cursor

        self._last_norm_x = norm_x
        self._last_norm_y = norm_y

        target_x = norm_x * SCREEN_W
        target_y = norm_y * SCREEN_H

        self._cursor_x += SMOOTHING * (target_x - self._cursor_x)
        self._cursor_y += SMOOTHING * (target_y - self._cursor_y)

        pyautogui.moveTo(int(self._cursor_x), int(self._cursor_y))

    def _scroll(self, ticks):
        """Fire a scroll event rate-limited to SCROLL_RATE times per second."""
        now = time.time()
        if now - self._last_scroll_time >= 1.0 / SCROLL_RATE:
            pyautogui.scroll(ticks)
            self._last_scroll_time = now

    def scroll_up(self):
        """Scroll up by SCROLL_TICKS, rate-limited."""
        self._scroll(SCROLL_TICKS)

    def scroll_down(self):
        """Scroll down by SCROLL_TICKS, rate-limited."""
        self._scroll(-SCROLL_TICKS)

    def click(self):
        """Click without drag (for compatibility)."""
        now = time.time()
        if (now - self._last_click_time) > CLICK_DEBOUNCE:
            pyautogui.click()
            self._last_click_time = now

    def release_click(self):
        pass

    def right_click(self):
        """Trigger a right click with debounce."""
        now = time.time()
        if not self._right_clicking and (now - self._last_click_time) > CLICK_DEBOUNCE:
            pyautogui.rightClick()
            self._last_click_time = now
            self._right_clicking = True

    def release_right_click(self):
        self._right_clicking = False

    def double_click(self):
        """Trigger a double click with debounce."""
        now = time.time()
        if (now - self._last_click_time) > CLICK_DEBOUNCE:
            pyautogui.doubleClick()
            self._last_click_time = now

    def three_finger_swipe(self):
        """Simulate a three-finger swipe (switch apps on Mac / task view on Windows)."""
        now = time.time()
        if (now - self._last_click_time) > CLICK_DEBOUNCE:
            if IS_MAC:
                pyautogui.hotkey('ctrl', 'right')  # macOS: three-finger swipe right
            else:
                pyautogui.hotkey('alt', 'tab')  # Windows: alt+tab switches apps
            self._last_click_time = now

    def drag_start(self):
        """Start dragging (mouse down)."""
        if not self._clicking:
            pyautogui.mouseDown()
            self._clicking = True

    def drag_end(self):
        """End dragging (mouse up)."""
        if self._clicking:
            pyautogui.mouseUp()
            self._clicking = False