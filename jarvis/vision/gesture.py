from enum import Enum, auto
import math


class GestureType(Enum):
    NONE = auto()
    CURSOR = auto()       # Index finger up → move cursor
    CLICK = auto()        # Pinch (thumb + index) → left click / drag
    SCROLL_UP = auto()    # Index + middle pointing up → scroll up
    SCROLL_DOWN = auto()  # Index + middle pointing down → scroll down
    RIGHT_CLICK = auto()  # Only pinky up → right click
    PAUSE = auto()        # Fist → pause tracking


# MediaPipe hand landmark indices
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
INDEX_MCP = 5
MIDDLE_TIP = 12
MIDDLE_MCP = 9
RING_TIP = 16
RING_MCP = 13
PINKY_TIP = 20
PINKY_MCP = 17

# Minimum hand size as a fraction of frame width to be considered "in range".
MIN_HAND_SIZE = 0.20


def _distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _finger_extended(tip, mcp, wrist):
    return _distance(tip, wrist) > _distance(mcp, wrist)


def _hand_in_range(landmarks) -> bool:
    size = _distance(landmarks[WRIST], landmarks[MIDDLE_MCP])
    return size >= MIN_HAND_SIZE


def get_scroll_speed(landmarks) -> float:
    """
    Returns a scroll speed multiplier between 0.0 and 1.0 based on how
    vertical the index+middle fingers are pointing.

    Measures the angle of the vector from MCP to fingertip relative to
    vertical. Straight up or straight down = 1.0 (fastest).
    Horizontal = 0.0 (slowest / dead zone).
    """
    index_tip = landmarks[INDEX_TIP]
    index_mcp = landmarks[INDEX_MCP]
    middle_tip = landmarks[MIDDLE_TIP]
    middle_mcp = landmarks[MIDDLE_MCP]

    # Average direction vector from knuckle to fingertip
    dx = ((index_tip[0] - index_mcp[0]) + (middle_tip[0] - middle_mcp[0])) / 2
    dy = ((index_tip[1] - index_mcp[1]) + (middle_tip[1] - middle_mcp[1])) / 2

    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return 0.0

    # abs(dy) / length gives how vertical the finger vector is (1.0 = perfectly vertical)
    verticality = abs(dy) / length
    return verticality


def classify(landmarks) -> GestureType:
    if landmarks is None:
        return GestureType.NONE

    if not _hand_in_range(landmarks):
        return GestureType.NONE

    wrist = landmarks[WRIST]
    thumb_tip = landmarks[THUMB_TIP]
    index_tip = landmarks[INDEX_TIP]
    index_mcp = landmarks[INDEX_MCP]
    middle_tip = landmarks[MIDDLE_TIP]
    middle_mcp = landmarks[MIDDLE_MCP]
    ring_tip = landmarks[RING_TIP]
    ring_mcp = landmarks[RING_MCP]
    pinky_tip = landmarks[PINKY_TIP]
    pinky_mcp = landmarks[PINKY_MCP]

    index_up = _finger_extended(index_tip, index_mcp, wrist)
    middle_up = _finger_extended(middle_tip, middle_mcp, wrist)
    ring_up = _finger_extended(ring_tip, ring_mcp, wrist)
    pinky_up = _finger_extended(pinky_tip, pinky_mcp, wrist)

    pinch_dist = _distance(thumb_tip, index_tip)
    hand_size = _distance(wrist, middle_mcp)
    pinch_dist_norm = (pinch_dist / hand_size) if hand_size > 0 else 1.0

    # --- Fist → pause ---
    if not index_up and not middle_up and not ring_up and not pinky_up:
        return GestureType.PAUSE

    # --- Pinch → click/drag ---
    if pinch_dist_norm < 0.35 and not middle_up and not ring_up and not pinky_up:
        return GestureType.CLICK

    # --- Only pinky up → right click ---
    if pinky_up and not index_up and not middle_up and not ring_up:
        return GestureType.RIGHT_CLICK

    # --- Scroll: index + middle up, ring + pinky down ---
    # tip_y < mcp_y = pointing up → SCROLL_UP, otherwise SCROLL_DOWN
    if index_up and middle_up and not ring_up and not pinky_up:
        avg_tip_y = (index_tip[1] + middle_tip[1]) / 2
        avg_mcp_y = (index_mcp[1] + middle_mcp[1]) / 2
        if avg_tip_y < avg_mcp_y:
            return GestureType.SCROLL_UP
        else:
            return GestureType.SCROLL_DOWN

    # --- Cursor: only index up ---
    if index_up and not middle_up and not ring_up and not pinky_up:
        return GestureType.CURSOR

    return GestureType.NONE