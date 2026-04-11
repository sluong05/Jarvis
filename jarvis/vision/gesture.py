from enum import Enum, auto
import math


class GestureType(Enum):
    NONE = auto()
    CURSOR = auto()       # Index finger up → move cursor
    CLICK = auto()        # Pinch (thumb + index) → left click / drag
    SCROLL_UP = auto()    # Index + middle pointing up → scroll up
    SCROLL_DOWN = auto()  # Index + middle pointing down → scroll down
    RIGHT_CLICK = auto()  # Only pinky up → right click
    ZOOM_IN = auto()      # Thumb + index + middle spreading apart → zoom in
    ZOOM_OUT = auto()     # Thumb + index + middle coming together → zoom out
    PAUSE = auto()        # Fist (all fingers curled) → pause tracking


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


def _distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _finger_extended(tip, mcp, wrist):
    """True if fingertip is farther from wrist than MCP joint (finger is up)."""
    return _distance(tip, wrist) > _distance(mcp, wrist)


# Tracks the previous spread distance between thumb, index, and middle
# for detecting zoom direction across frames.
_prev_zoom_dist = None


def get_zoom_spread(landmarks):
    """Return the average spread between thumb, index, and middle tips."""
    thumb_tip = landmarks[THUMB_TIP]
    index_tip = landmarks[INDEX_TIP]
    middle_tip = landmarks[MIDDLE_TIP]
    d1 = _distance(thumb_tip, index_tip)
    d2 = _distance(index_tip, middle_tip)
    d3 = _distance(thumb_tip, middle_tip)
    hand_size = _distance(landmarks[WRIST], landmarks[MIDDLE_MCP])
    if hand_size == 0:
        return 0.0
    return (d1 + d2 + d3) / (3 * hand_size)


def classify(landmarks) -> GestureType:
    """Classify 21 MediaPipe landmarks into a GestureType."""
    global _prev_zoom_dist

    if landmarks is None:
        _prev_zoom_dist = None
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

    # Pinch: thumb and index tips are close together
    pinch_dist = _distance(thumb_tip, index_tip)
    hand_size = _distance(wrist, middle_mcp)
    pinch_dist_norm = (pinch_dist / hand_size) if hand_size > 0 else 1.0

    thumb_extended = _distance(thumb_tip, wrist) > _distance(landmarks[1], wrist)

    # --- Fist: no fingers extended → pause tracking ---
    if not index_up and not middle_up and not ring_up and not pinky_up:
        _prev_zoom_dist = None
        return GestureType.PAUSE

    # --- Pinch: thumb close to index, other fingers down → click/drag ---
    if pinch_dist_norm < 0.35 and not middle_up and not ring_up and not pinky_up:
        _prev_zoom_dist = None
        return GestureType.CLICK

    # --- Right click: only pinky up ---
    if pinky_up and not index_up and not middle_up and not ring_up:
        _prev_zoom_dist = None
        return GestureType.RIGHT_CLICK

    # --- Zoom: thumb + index + middle extended, ring + pinky down ---
    if thumb_extended and index_up and middle_up and not ring_up and not pinky_up:
        current_dist = get_zoom_spread(landmarks)
        if _prev_zoom_dist is not None:
            delta = current_dist - _prev_zoom_dist
            _prev_zoom_dist = current_dist
            # Threshold filters out small tremor noise
            if delta > 0.015:
                return GestureType.ZOOM_IN
            elif delta < -0.015:
                return GestureType.ZOOM_OUT
        else:
            _prev_zoom_dist = current_dist
        return GestureType.NONE

    # --- Scroll: index + middle raised, ring + pinky down ---
    if index_up and middle_up and not ring_up and not pinky_up:
        _prev_zoom_dist = None
        avg_tip_y = (index_tip[1] + middle_tip[1]) / 2
        avg_mcp_y = (index_mcp[1] + middle_mcp[1]) / 2
        if avg_tip_y < avg_mcp_y:
            return GestureType.SCROLL_UP
        else:
            return GestureType.SCROLL_DOWN

    # --- Cursor: only index finger up ---
    if index_up and not middle_up and not ring_up and not pinky_up:
        _prev_zoom_dist = None
        return GestureType.CURSOR

    _prev_zoom_dist = None
    return GestureType.NONE