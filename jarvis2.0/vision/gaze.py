import pickle
import numpy as np


# 9 calibration points in normalized screen coords [0,1]
CALIBRATION_POINTS = [
    (0.05, 0.05), (0.5, 0.05), (0.95, 0.05),
    (0.05, 0.5),  (0.5, 0.5),  (0.95, 0.5),
    (0.05, 0.95), (0.5, 0.95), (0.95, 0.95),
]


class GazeCalibrator:
    """
    Records (iris_x, iris_y) → (screen_x, screen_y) pairs during calibration
    and fits a 2D affine transform via least squares.
    """

    def __init__(self):
        self._iris_pts = []   # list of [x, y]
        self._screen_pts = [] # list of [x, y] in pixels

    def record_point(self, iris_x, iris_y, screen_x, screen_y):
        self._iris_pts.append([iris_x, iris_y])
        self._screen_pts.append([screen_x, screen_y])

    def compute(self):
        """
        Fit affine transform: [sx, sy] = A @ [ix, iy, 1]
        Returns the (3,2) matrix A.
        """
        src = np.array([[x, y, 1.0] for x, y in self._iris_pts], dtype=np.float64)
        dst = np.array(self._screen_pts, dtype=np.float64)
        # Least-squares solve: src @ A = dst
        A, _, _, _ = np.linalg.lstsq(src, dst, rcond=None)
        return A

    def save(self, path, matrix):
        with open(path, "wb") as f:
            pickle.dump(matrix, f)

    @staticmethod
    def load(path):
        with open(path, "rb") as f:
            return pickle.load(f)


class GazeMapper:
    """
    Applies a fitted affine transform to map iris coords → screen pixels.
    Falls back to linear scaling if no calibration matrix is loaded.
    """

    def __init__(self, screen_w, screen_h, smoothing=0.08):
        self._matrix = None
        self._screen_w = screen_w
        self._screen_h = screen_h
        self._smoothing = smoothing
        self._cur_x = screen_w / 2
        self._cur_y = screen_h / 2

    def load(self, matrix):
        self._matrix = matrix

    def map(self, iris_x, iris_y):
        """
        Map normalized iris coords to smoothed screen pixel position.
        Returns (screen_x, screen_y).
        """
        if self._matrix is not None:
            vec = np.array([iris_x, iris_y, 1.0], dtype=np.float64)
            result = vec @ self._matrix
            tx = float(np.clip(result[0], 0, self._screen_w))
            ty = float(np.clip(result[1], 0, self._screen_h))
        else:
            # Fallback: simple linear scale
            tx = iris_x * self._screen_w
            ty = iris_y * self._screen_h

        # Exponential smoothing
        self._cur_x += self._smoothing * (tx - self._cur_x)
        self._cur_y += self._smoothing * (ty - self._cur_y)

        return int(self._cur_x), int(self._cur_y)
