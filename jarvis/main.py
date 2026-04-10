import sys
import os
import cv2
import threading
import time

# Allow imports from project root
sys.path.insert(0, os.path.dirname(__file__))

from vision.hand_tracker import HandTracker
from vision.gesture import GestureType, classify, INDEX_TIP
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
        # macOS AVFoundation needs a moment to initialize; Windows does not
        if config.IS_MAC:
            time.sleep(1.0)
        self._running = True
        threading.Thread(target=self._reader, daemon=True).start()
        # Wait until first frame arrives
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


def main():
    print("=" * 50)
    print("  JARVIS — Hands-Free Computer Control")
    print("=" * 50)
    print("Gestures:")
    print("  Index finger up           → Move cursor")
    print("  Pinch                     → Click / drag")
    print("  Index + middle up         → Scroll up")
    print("  Index + middle down       → Scroll down")
    print("  Fist                      → Pause/resume")
    print("Voice: Say 'Jarvis <command>'")
    print("Press Q to quit.")
    print("=" * 50)

    print("[Jarvis] Loading hand tracker...")
    tracker = HandTracker(
        min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
    )
    mouse = MouseController()

    print("[Jarvis] Opening camera...")
    cam = CameraStream(config.CAM_INDEX)
    ready = cam.start()
    if not ready:
        print("[ERROR] Camera opened but no frames received.")
        print("        Go to System Settings → Privacy & Security → Camera")
        print("        and make sure Terminal.app is toggled on.")
        cam.release()
        return

    print("[Jarvis] Camera ready.")

    # Start voice layer
    voice_listener = VoiceListener()
    claude_agent = ClaudeAgent()
    voice_listener.start()

    paused = False
    prev_both_fists = False
    is_dragging = False

    while True:
        frame = cam.read()
        if frame is None:
            continue

        # Flip frame horizontally for mirror view
        frame = cv2.flip(frame, 1)

        # Detect hand landmarks (up to 2 hands)
        all_landmarks, frame = tracker.process(frame)

        # Primary hand drives cursor/gestures
        landmarks = all_landmarks[0] if all_landmarks else None
        gesture = classify(landmarks)

        # --- Both fists simultaneously → toggle pause ---
        both_fists = (
            len(all_landmarks) == 2 and
            classify(all_landmarks[0]) == GestureType.PAUSE and
            classify(all_landmarks[1]) == GestureType.PAUSE
        )
        if both_fists and not prev_both_fists:
            paused = not paused
            print(f"[Jarvis] Tracking {'paused' if paused else 'resumed'}")
        prev_both_fists = both_fists

        if not paused and landmarks is not None:
            index_tip = landmarks[INDEX_TIP]

            if gesture == GestureType.CLICK:
                # Hold mouse button and move — enables click, drag, and text selection
                if not is_dragging:
                    mouse.drag_start()
                    is_dragging = True
                mouse.move(index_tip[0], index_tip[1])

            elif gesture == GestureType.CURSOR:
                # Releasing pinch ends the drag/click
                if is_dragging:
                    mouse.drag_end()
                    is_dragging = False
                mouse.move(index_tip[0], index_tip[1])

            elif gesture == GestureType.SCROLL_UP:
                if is_dragging:
                    mouse.drag_end()
                    is_dragging = False
                mouse.scroll_up()

            elif gesture == GestureType.SCROLL_DOWN:
                if is_dragging:
                    mouse.drag_end()
                    is_dragging = False
                mouse.scroll_down()

            else:
                if is_dragging:
                    mouse.drag_end()
                    is_dragging = False
                mouse.release_click()

        elif not paused:
            if is_dragging:
                mouse.drag_end()
                is_dragging = False
            mouse.release_click()

        # --- Voice commands ---
        while not voice_listener.command_queue.empty():
            command = voice_listener.command_queue.get_nowait()
            print(f"[Jarvis] Executing: {command}")
            # Run in thread so vision loop stays responsive
            threading.Thread(
                target=claude_agent.handle_command,
                args=(command,),
                daemon=True,
            ).start()

        # --- HUD ---
        if config.SHOW_HUD:
            frame = hud.draw(frame, gesture, paused)

        cv2.imshow("JARVIS", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    voice_listener.stop()
    tracker.close()
    cam.release()
    cv2.destroyAllWindows()
    print("[Jarvis] Shutdown complete.")


if __name__ == "__main__":
    main()