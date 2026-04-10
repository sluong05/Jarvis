import sys
import os
import cv2
import threading
import time
import numpy as np
import pyautogui

# Allow imports from project root
sys.path.insert(0, os.path.dirname(__file__))

from vision.hand_tracker import HandTracker
from vision.face_tracker import FaceTracker
from vision.gesture import GestureType, classify
from vision.gaze import GazeCalibrator, GazeMapper, CALIBRATION_POINTS
from control.mouse import MouseController
from voice.listener import VoiceListener
from voice.claude_agent import ClaudeAgent
import hud
import config


class CameraStream:
    """Reads camera frames on a background thread.
    Uses DirectShow on Windows, AVFoundation on macOS.
    """

    def __init__(self, index=0):
        if config.IS_WINDOWS:
            self._cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        else:
            self._cap = cv2.VideoCapture(index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._frame = None
        self._lock = threading.Lock()
        self._running = False

    def start(self):
        if config.IS_MAC:
            time.sleep(1.0)
        self._running = True
        threading.Thread(target=self._reader, daemon=True).start()
        for _ in range(100):
            time.sleep(0.05)
            with self._lock:
                if self._frame is not None:
                    return True
        return False

    def _reader(self):
        while self._running:
            ret, frame = self._cap.read()
            if ret:
                with self._lock:
                    self._frame = frame

    def read(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def release(self):
        self._running = False
        self._cap.release()


def _iris_center(left_iris, right_iris):
    """Return a single iris point based on EYE_PREFER config."""
    if config.EYE_PREFER == "left" and left_iris:
        return left_iris
    if config.EYE_PREFER == "right" and right_iris:
        return right_iris
    # average (default)
    if left_iris and right_iris:
        return ((left_iris[0] + right_iris[0]) / 2,
                (left_iris[1] + right_iris[1]) / 2)
    return left_iris or right_iris


def run_calibration(cam, hand_tracker, face_tracker):
    """
    Full-screen 9-point calibration.
    User looks at each dot and pinches to confirm.
    Returns fitted affine matrix or None on abort.
    """
    sw, sh = config.SCREEN_W, config.SCREEN_H
    calibrator = GazeCalibrator()
    cv2.namedWindow("JARVIS 2.0 — Calibration", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("JARVIS 2.0 — Calibration",
                          cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    for idx, (nx, ny) in enumerate(CALIBRATION_POINTS):
        tx = int(nx * sw)
        ty = int(ny * sh)
        confirmed = False
        point_start = time.time()
        flash_until = 0.0

        while not confirmed:
            frame = cam.read()
            if frame is None:
                continue
            frame = cv2.flip(frame, 1)

            all_landmarks, _ = hand_tracker.process(frame)
            left_iris, right_iris, _ = face_tracker.process(frame)

            landmarks = all_landmarks[0] if all_landmarks else None
            gesture = classify(landmarks)

            # Build fullscreen canvas
            canvas = np.zeros((sh, sw, 3), dtype=np.uint8)

            # Draw all upcoming dots dimly
            for i, (pnx, pny) in enumerate(CALIBRATION_POINTS):
                if i > idx:
                    cv2.circle(canvas, (int(pnx * sw), int(pny * sh)),
                               8, (50, 50, 50), -1)

            # Flash green on confirmation, else pulse white/cyan
            elapsed = time.time() - point_start
            if time.time() < flash_until:
                dot_color = (0, 255, 100)
                radius = 18
            else:
                pulse = int(10 + 6 * abs(np.sin(elapsed * 3)))
                dot_color = (0, 220, 255)
                radius = pulse

            cv2.circle(canvas, (tx, ty), radius + 6, (30, 80, 80), 2)
            cv2.circle(canvas, (tx, ty), radius, dot_color, -1)

            # Instructions
            msg = f"Look at the dot and PINCH to confirm  ({idx + 1}/{len(CALIBRATION_POINTS)})"
            cv2.putText(canvas, msg, (sw // 2 - 320, sh - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 180, 180), 2)
            cv2.putText(canvas, "JARVIS 2.0 — Calibration", (sw // 2 - 260, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)

            cv2.imshow("JARVIS 2.0 — Calibration", canvas)
            cv2.waitKey(1)

            # Pinch to confirm
            if gesture == GestureType.CLICK:
                iris = _iris_center(left_iris, right_iris)
                if iris:
                    calibrator.record_point(iris[0], iris[1], tx, ty)
                    flash_until = time.time() + 0.4
                    confirmed = True
                    time.sleep(0.5)  # brief pause before next point

            # 4-second timeout — auto-advance using best iris estimate
            if time.time() - point_start > 4.0:
                iris = _iris_center(left_iris, right_iris)
                if iris:
                    calibrator.record_point(iris[0], iris[1], tx, ty)
                confirmed = True

            if cv2.waitKey(1) & 0xFF == ord("q"):
                cv2.destroyWindow("JARVIS 2.0 — Calibration")
                return None

    cv2.destroyWindow("JARVIS 2.0 — Calibration")

    if len(calibrator._iris_pts) < 4:
        print("[Jarvis] Not enough calibration points captured.")
        return None

    matrix = calibrator.compute()
    print("[Jarvis 2.0] Calibration complete.")
    return matrix


def main():
    print("=" * 50)
    print("  JARVIS 2.0 — Eye Tracking Control")
    print("=" * 50)
    print("  Eyes  → Move cursor")
    print("  Pinch → Left click")
    print("  V-sign → Scroll")
    print("  Open palm → Right click")
    print("  Both fists → Pause/resume")
    print("  Voice: Say 'Jarvis <command>'")
    print("  Press Q to quit.")
    print("=" * 50)

    print("[Jarvis 2.0] Loading trackers...")
    hand_tracker = HandTracker(
        min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
    )
    face_tracker = FaceTracker()
    mouse = MouseController()
    gaze_mapper = GazeMapper(config.SCREEN_W, config.SCREEN_H,
                             smoothing=config.GAZE_SMOOTHING)

    print("[Jarvis 2.0] Opening camera...")
    cam = CameraStream(config.CAM_INDEX)
    ready = cam.start()
    if not ready:
        print("[ERROR] Camera opened but no frames received.")
        print("        Go to System Settings → Privacy & Security → Camera")
        print("        and make sure Terminal.app is toggled on.")
        cam.release()
        return

    print("[Jarvis 2.0] Camera ready.")

    # --- Always calibrate on launch for accuracy ---
    print("[Jarvis 2.0] Starting calibration...")
    matrix = run_calibration(cam, hand_tracker, face_tracker)
    if matrix is None:
        print("[Jarvis 2.0] Calibration aborted.")
        cam.release()
        return

    gaze_mapper.load(matrix)
    print("[Jarvis 2.0] Gaze mapper ready.")

    # --- Voice layer ---
    voice_listener = VoiceListener()
    claude_agent = ClaudeAgent()
    voice_listener.start()

    paused = False
    prev_both_fists = False
    iris_stable_frames = 0       # require N consecutive detections before moving cursor
    IRIS_STABLE_THRESHOLD = 3

    while True:
        frame = cam.read()
        if frame is None:
            continue

        frame = cv2.flip(frame, 1)

        # Process both trackers each frame
        all_landmarks, frame = hand_tracker.process(frame)
        left_iris, right_iris, frame = face_tracker.process(frame)

        # Primary hand for gestures
        landmarks = all_landmarks[0] if all_landmarks else None
        gesture = classify(landmarks)

        # --- Both fists → toggle pause ---
        both_fists = (
            len(all_landmarks) == 2 and
            classify(all_landmarks[0]) == GestureType.PAUSE and
            classify(all_landmarks[1]) == GestureType.PAUSE
        )
        if both_fists and not prev_both_fists:
            paused = not paused
            print(f"[Jarvis 2.0] Tracking {'paused' if paused else 'resumed'}")
        prev_both_fists = both_fists

        # --- Gaze cursor ---
        if not paused:
            iris = _iris_center(left_iris, right_iris)
            if iris:
                iris_stable_frames = min(iris_stable_frames + 1, IRIS_STABLE_THRESHOLD)
            else:
                iris_stable_frames = 0  # lost face — reset, don't snap cursor

            if iris and iris_stable_frames >= IRIS_STABLE_THRESHOLD:
                sx, sy = gaze_mapper.map(iris[0], iris[1])
                pyautogui.moveTo(sx, sy)

        # --- Hand gestures (actions only, no cursor) ---
        if not paused and landmarks is not None:
            if gesture == GestureType.CLICK:
                mouse.click()
                mouse.reset_scroll()

            elif gesture == GestureType.SCROLL:
                index_tip = landmarks[8]
                mouse.scroll(index_tip[1])
                mouse.release_click()

            elif gesture == GestureType.RIGHT_CLICK:
                mouse.right_click()
                mouse.reset_scroll()

            else:
                mouse.release_click()
                mouse.release_right_click()
                mouse.reset_scroll()

        elif not paused:
            mouse.release_click()
            mouse.release_right_click()
            mouse.reset_scroll()

        # --- Voice commands ---
        while not voice_listener.command_queue.empty():
            command = voice_listener.command_queue.get_nowait()
            print(f"[Jarvis 2.0] Executing: {command}")
            threading.Thread(
                target=claude_agent.handle_command,
                args=(command,),
                daemon=True,
            ).start()

        # --- HUD ---
        if config.SHOW_HUD:
            frame = hud.draw(frame, gesture, paused)

        cv2.imshow("JARVIS 2.0", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    voice_listener.stop()
    hand_tracker.close()
    face_tracker.close()
    cam.release()
    cv2.destroyAllWindows()
    print("[Jarvis 2.0] Shutdown complete.")


if __name__ == "__main__":
    main()
