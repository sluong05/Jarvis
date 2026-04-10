import cv2
from vision.gesture import GestureType

# Gesture label colors (BGR)
GESTURE_COLORS = {
    GestureType.NONE: (100, 100, 100),
    GestureType.CURSOR: (0, 255, 0),
    GestureType.CLICK: (0, 200, 255),
    GestureType.SCROLL: (255, 200, 0),
    GestureType.RIGHT_CLICK: (0, 100, 255),
    GestureType.PAUSE: (0, 0, 255),
}

GESTURE_LABELS = {
    GestureType.NONE: "---",
    GestureType.CURSOR: "CURSOR",
    GestureType.CLICK: "CLICK",
    GestureType.SCROLL: "SCROLL",
    GestureType.RIGHT_CLICK: "RIGHT CLICK",
    GestureType.PAUSE: "FIST",
}


def draw(frame, gesture: GestureType, paused: bool):
    h, w = frame.shape[:2]

    # Status bar background
    cv2.rectangle(frame, (0, 0), (w, 50), (20, 20, 20), -1)

    # Title
    cv2.putText(frame, "JARVIS", (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)

    # Gesture label
    label = GESTURE_LABELS.get(gesture, "---")
    color = GESTURE_COLORS.get(gesture, (200, 200, 200))
    cv2.putText(frame, label, (120, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    # Paused overlay
    if paused:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 50), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        cv2.putText(frame, "TRACKING PAUSED", (w // 2 - 180, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

    # Gesture reference guide (bottom)
    guide = [
        "Index up: CURSOR",
        "Pinch: CLICK",
        "2 fingers: SCROLL",
        "Open palm: RIGHT CLICK",
        "Both fists: PAUSE",
    ]
    for i, line in enumerate(guide):
        cv2.putText(frame, line, (10, h - 20 - (len(guide) - 1 - i) * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)

    return frame
