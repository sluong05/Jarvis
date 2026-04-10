from enum import Enum, auto
import math


class GestureType(Enum):
    NONE = auto()
    CURSOR = auto()       # Index finger up → move cursor
    CLICK = auto()        # Pinch (thumb + index) → left click
    SCROLL = auto()       # Two fingers (index + middle) up → scroll
    RIGHT_CLICK = auto()  # Open palm (all fingers extended) → right click
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


def classify(landmarks) -> GestureType:
    """Classify 21 MediaPipe landmarks into a GestureType."""
    if landmarks is None:
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
    # Normalize by hand size (wrist to middle MCP)
    hand_size = _distance(wrist, middle_mcp)
    if hand_size > 0:
        pinch_dist_norm = pinch_dist / hand_size
    else:
        pinch_dist_norm = 1.0

    # --- Fist: no fingers extended ---
    if not index_up and not middle_up and not ring_up and not pinky_up:
        return GestureType.PAUSE

    # --- Open palm: all fingers extended ---
    if index_up and middle_up and ring_up and pinky_up:
        return GestureType.RIGHT_CLICK

    # --- Pinch: index and middle down, thumb close to index ---
    if pinch_dist_norm < 0.35 and not middle_up and not ring_up and not pinky_up:
        return GestureType.CLICK

    # --- Scroll: index + middle up, others down ---
    if index_up and middle_up and not ring_up and not pinky_up:
        return GestureType.SCROLL

    # --- Cursor: only index up ---
    if index_up and not middle_up and not ring_up and not pinky_up:
        return GestureType.CURSOR

    return GestureType.NONE
