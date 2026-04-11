import pyautogui
import time
from config import SCREEN_W, SCREEN_H, SMOOTHING, CLICK_DEBOUNCE, CURSOR_MARGIN, IS_MAC

pyautogui.FAILSAFE = False  # Disable corner failsafe so hand can reach edges
pyautogui.PAUSE = 0         # No artificial delay between pyautogui calls

# Minimum normalized movement required before the cursor moves.
DEADZONE = 0.02

# Scroll ticks fired per second while the gesture is held.
SCROLL_RATE = 1000

# How many ticks per scroll event (higher = faster scroll per tick).
SCROLL_TICKS = 10

# Zoom ticks per event (Ctrl+scroll). Higher = bigger zoom step.
ZOOM_TICKS = 10


class MouseController:
    def __init__(self):
        self._cursor_x = SCREEN_W / 2
        self._cursor_y = SCREEN_H / 2
        self._last_click_time = 0
        self._last_right_click_time = 0
        self._clicking = False
        self._last_norm_x = None
        self._last_norm_y = None
        self._last_scroll_time = 0.0

    def move(self, norm_x, norm_y):
        """
        Move cursor to normalized coords [0,1].
        Applies a deadzone so small finger tremors don't move the cursor.
        Applies exponential smoothing to reduce jitter.
        Remaps the active hand zone (inside CURSOR_MARGIN) to the full screen.
        """
        m = CURSOR_MARGIN
        norm_x = max(0.0, min(1.0, (norm_x - m) / (1.0 - 2 * m)))
        norm_y = max(0.0, min(1.0, (norm_y - m) / (1.0 - 2 * m)))

        if self._last_norm_x is not None:
            dx = abs(norm_x - self._last_norm_x)
            dy = abs(norm_y - self._last_norm_y)
            if dx < DEADZONE and dy < DEADZONE:
                return

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
        self._scroll(SCROLL_TICKS)

    def scroll_down(self):
        self._scroll(-SCROLL_TICKS)

    def zoom_in(self):
        """Zoom in via Ctrl+scroll up (works in browsers, image viewers, etc.)."""
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(ZOOM_TICKS)
        pyautogui.keyUp('ctrl')

    def zoom_out(self):
        """Zoom out via Ctrl+scroll down."""
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(-ZOOM_TICKS)
        pyautogui.keyUp('ctrl')

    def click(self):
        now = time.time()
        if (now - self._last_click_time) > CLICK_DEBOUNCE:
            pyautogui.click()
            self._last_click_time = now

    def release_click(self):
        pass

    def right_click(self):
        """Trigger a right click, debounced independently from left click."""
        now = time.time()
        if (now - self._last_right_click_time) > CLICK_DEBOUNCE:
            pyautogui.rightClick()
            self._last_right_click_time = now

    def double_click(self):
        now = time.time()
        if (now - self._last_click_time) > CLICK_DEBOUNCE:
            pyautogui.doubleClick()
            self._last_click_time = now

    def drag_start(self):
        if not self._clicking:
            pyautogui.mouseDown()
            self._clicking = True

    def drag_end(self):
        if self._clicking:
            pyautogui.mouseUp()
            self._clicking = False