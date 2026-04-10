import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import os

# Landmark connection pairs for drawing
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hand_landmarker.task")


class HandTracker:
    def __init__(self, min_detection_confidence=0.7, min_tracking_confidence=0.7):
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._frame_ts = 0

    def process(self, frame):
        """
        Process a BGR frame and return (all_landmarks, annotated_frame).
        all_landmarks: list of up to 2 hands, each a list of 21 (x,y,z) tuples. May be empty.
        The primary hand (index 0) is used for cursor/gesture control.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_ts += 33
        result = self._landmarker.detect_for_video(mp_image, self._frame_ts)

        all_landmarks = []
        for hand_lms in result.hand_landmarks:
            lms = [(lm.x, lm.y, lm.z) for lm in hand_lms]
            all_landmarks.append(lms)
            self._draw_landmarks(frame, lms)

        return all_landmarks, frame

    def _draw_landmarks(self, frame, landmarks):
        h, w = frame.shape[:2]
        pts = [(int(x * w), int(y * h)) for x, y, z in landmarks]
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (0, 220, 100), 2)
        for pt in pts:
            cv2.circle(frame, pt, 4, (255, 255, 255), -1)
            cv2.circle(frame, pt, 4, (0, 180, 80), 1)

    def close(self):
        self._landmarker.close()
