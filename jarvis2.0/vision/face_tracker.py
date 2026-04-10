import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import os

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "face_landmarker.task")

# MediaPipe iris landmark indices
LEFT_IRIS_CENTER  = 468
RIGHT_IRIS_CENTER = 473


class FaceTracker:
    def __init__(self, min_face_detection_confidence=0.6, min_tracking_confidence=0.6):
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=min_face_detection_confidence,
            min_face_presence_confidence=min_face_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        self._frame_ts = 0

    def process(self, frame):
        """
        Process a BGR frame and return (left_iris, right_iris, annotated_frame).
        left_iris / right_iris: (x, y) normalized [0,1], or None if not detected.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_ts += 33
        result = self._landmarker.detect_for_video(mp_image, self._frame_ts)

        left_iris = None
        right_iris = None

        if result.face_landmarks:
            lms = result.face_landmarks[0]
            left_iris  = (lms[LEFT_IRIS_CENTER].x,  lms[LEFT_IRIS_CENTER].y)
            right_iris = (lms[RIGHT_IRIS_CENTER].x, lms[RIGHT_IRIS_CENTER].y)
            self._draw_iris(frame, left_iris,  (0, 255, 200))
            self._draw_iris(frame, right_iris, (0, 200, 255))

        return left_iris, right_iris, frame

    def _draw_iris(self, frame, iris, color):
        h, w = frame.shape[:2]
        cx = int(iris[0] * w)
        cy = int(iris[1] * h)
        cv2.circle(frame, (cx, cy), 5, color, 2)
        cv2.line(frame, (cx - 8, cy), (cx + 8, cy), color, 1)
        cv2.line(frame, (cx, cy - 8), (cx, cy + 8), color, 1)

    def close(self):
        self._landmarker.close()
