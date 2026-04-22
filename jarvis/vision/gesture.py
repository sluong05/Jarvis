from enum import Enum, auto
import math


class GestureType(Enum):
    NONE = auto()
    CURSOR = auto()       # Index finger up → move cursor
    CLICK = auto()        # Pinch (thumb + index) → left click / drag
    SCROLL_UP = auto()    # Index + middle pointing up → scroll up
    SCROLL_DOWN = auto()  # Index + middle pointing down → scroll down
    RIGHT_CLICK = auto()  # Only pinky up → right click
    ZOOM_IN = auto()      # Both palms open, close together → zoom in
    ZOOM_OUT = auto()     # Both palms open, far apart → zoom out
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

MIN_HAND_SIZE = 0.2

# Distance thresholds between the two wrists (normalized coords).
# Hands closer than ZOOM_IN_DIST → zoom in.
# Hands further than ZOOM_OUT_DIST → zoom out.
# Between the two = neutral dead zone (no zoom).
ZOOM_IN_DIST = 0.35
ZOOM_OUT_DIST = 0.55


def _distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _finger_extended(tip, mcp, wrist):
    return _distance(tip, wrist) > _distance(mcp, wrist)


def _hand_in_range(landmarks) -> bool:
    size = _distance(landmarks[WRIST], landmarks[MIDDLE_MCP])
    return size >= MIN_HAND_SIZE


def _is_open_palm(landmarks) -> bool:
    """True if all four fingers are extended (open palm)."""
    wrist = landmarks[WRIST]
    return (
        _finger_extended(landmarks[INDEX_TIP], landmarks[INDEX_MCP], wrist) and
        _finger_extended(landmarks[MIDDLE_TIP], landmarks[MIDDLE_MCP], wrist) and
        _finger_extended(landmarks[RING_TIP], landmarks[RING_MCP], wrist) and
        _finger_extended(landmarks[PINKY_TIP], landmarks[PINKY_MCP], wrist)
    )


def get_scroll_speed(landmarks) -> float:
    """
    Returns a scroll speed multiplier 0.0–1.0 based on how vertical the
    index+middle fingers are pointing. Straight up/down = 1.0, horizontal = 0.0.
    """
    index_tip = landmarks[INDEX_TIP]
    index_mcp = landmarks[INDEX_MCP]
    middle_tip = landmarks[MIDDLE_TIP]
    middle_mcp = landmarks[MIDDLE_MCP]

    dx = ((index_tip[0] - index_mcp[0]) + (middle_tip[0] - middle_mcp[0])) / 2
    dy = ((index_tip[1] - index_mcp[1]) + (middle_tip[1] - middle_mcp[1])) / 2

    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return 0.0
    return abs(dy) / length


def get_two_hand_zoom(all_landmarks) -> GestureType:
    """
    Returns ZOOM_IN if both palms are open and close together,
    ZOOM_OUT if both palms are open and far apart, NONE otherwise.
    Distance thresholds are in normalized frame coords.
    """
    if len(all_landmarks) < 2:
        return GestureType.NONE

    lm0, lm1 = all_landmarks[0], all_landmarks[1]

    if not _hand_in_range(lm0) or not _hand_in_range(lm1):
        return GestureType.NONE

    if not _is_open_palm(lm0) or not _is_open_palm(lm1):
        return GestureType.NONE

    dist = _distance(lm0[WRIST], lm1[WRIST])

    if dist < ZOOM_IN_DIST:
        return GestureType.ZOOM_IN
    elif dist > ZOOM_OUT_DIST:
        return GestureType.ZOOM_OUT

    return GestureType.NONE


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
    if pinch_dist_norm < 0.25 and not middle_up and not ring_up and not pinky_up:
        return GestureType.CLICK

    # --- Only pinky up → right click ---
    if pinky_up and not index_up and not middle_up and not ring_up:
        return GestureType.RIGHT_CLICK

    # --- Scroll: index + middle up, ring + pinky down ---
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