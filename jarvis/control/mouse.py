import pyautogui
import time
from config import SCREEN_W, SCREEN_H, SMOOTHING, CLICK_DEBOUNCE, CURSOR_MARGIN, IS_MAC

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

DEADZONE = 0.02
SCROLL_RATE = 1000
SCROLL_TICKS_MAX = 10
SCROLL_TICKS_MIN = 1
ZOOM_TICKS = 3


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
        now = time.time()
        if now - self._last_scroll_time >= 1.0 / SCROLL_RATE:
            pyautogui.scroll(ticks)
            self._last_scroll_time = now

    def scroll_up(self, speed=1.0):
        ticks = max(SCROLL_TICKS_MIN, round(SCROLL_TICKS_MAX * speed))
        self._scroll(ticks)

    def scroll_down(self, speed=1.0):
        ticks = max(SCROLL_TICKS_MIN, round(SCROLL_TICKS_MAX * speed))
        self._scroll(-ticks)

    def zoom_in(self):
        """Zoom in via Ctrl+scroll up."""
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