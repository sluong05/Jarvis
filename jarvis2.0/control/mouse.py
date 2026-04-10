import pyautogui
import time
from config import SCREEN_W, SCREEN_H, SMOOTHING, CLICK_DEBOUNCE, SCROLL_SPEED, CURSOR_MARGIN

pyautogui.FAILSAFE = False  # Disable corner failsafe so hand can reach edges
pyautogui.PAUSE = 0         # No artificial delay between pyautogui calls


class MouseController:
    def __init__(self):
        self._cursor_x = SCREEN_W / 2
        self._cursor_y = SCREEN_H / 2
        self._last_click_time = 0
        self._last_scroll_y = None
        self._clicking = False
        self._right_clicking = False

    def move(self, norm_x, norm_y):
        """
        Move cursor to normalized coords [0,1].
        Applies exponential smoothing to reduce jitter.
        Remaps the active hand zone (inside CURSOR_MARGIN) to the full screen,
        so the hand doesn't need to reach the frame edge.
        """
        # Remap [margin, 1-margin] → [0, 1] so full screen is reachable from center of frame
        m = CURSOR_MARGIN
        norm_x = max(0.0, min(1.0, (norm_x - m) / (1.0 - 2 * m)))
        norm_y = max(0.0, min(1.0, (norm_y - m) / (1.0 - 2 * m)))

        target_x = norm_x * SCREEN_W
        target_y = norm_y * SCREEN_H

        self._cursor_x += SMOOTHING * (target_x - self._cursor_x)
        self._cursor_y += SMOOTHING * (target_y - self._cursor_y)

        pyautogui.moveTo(int(self._cursor_x), int(self._cursor_y))

    def click(self):
        """Trigger a left click with debounce."""
        now = time.time()
        if not self._clicking and (now - self._last_click_time) > CLICK_DEBOUNCE:
            pyautogui.click()
            self._last_click_time = now
            self._clicking = True

    def release_click(self):
        self._clicking = False

    def right_click(self):
        """Trigger a right click with debounce."""
        now = time.time()
        if not self._right_clicking and (now - self._last_click_time) > CLICK_DEBOUNCE:
            pyautogui.rightClick()
            self._last_click_time = now
            self._right_clicking = True

    def release_right_click(self):
        self._right_clicking = False

    def scroll(self, norm_y):
        """
        Joystick-style scroll: hand Y position in frame controls direction + speed.
        Center of frame = dead zone (no scroll).
        Above center = scroll up (faster the higher).
        Below center = scroll down (faster the lower).
        """
        # Distance from center (-0.5 to +0.5), positive = above center
        offset = 0.5 - norm_y
        dead_zone = 0.12  # fraction of frame that counts as "center"

        if abs(offset) < dead_zone:
            return  # hand in neutral zone, no scroll

        # Scale offset outside dead zone into a speed value
        direction = 1 if offset > 0 else -1
        magnitude = (abs(offset) - dead_zone) / (0.5 - dead_zone)  # 0→1
        scroll_amount = int(direction * magnitude * SCROLL_SPEED * 8)
        if scroll_amount != 0:
            pyautogui.scroll(scroll_amount)

    def reset_scroll(self):
        self._last_scroll_y = None
