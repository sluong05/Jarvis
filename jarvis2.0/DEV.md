# Jarvis 2.0 — Developer Reference

## What This Is
Hands-free computer control via webcam **eye tracking** (cursor) + **hand gestures** (click/scroll/pause) + Claude voice commands. Jarvis 2.0 replaces the hand-based cursor from v1 with iris tracking via MediaPipe FaceLandmarker. Built in Python for a Claude Code hackathon. Runs on macOS and Windows.

## Architecture Overview

```
main.py
├── vision/hand_tracker.py   → webcam frame → 21 hand keypoints (up to 2 hands)
├── vision/face_tracker.py   → webcam frame → left/right iris centers (normalized)
├── vision/gesture.py        → keypoints → GestureType enum
├── vision/gaze.py           → GazeCalibrator (9-point affine fit) + GazeMapper (runtime)
├── control/mouse.py         → GestureType → pyautogui mouse actions
├── control/keyboard.py      → hotkeys / typewrite helpers
├── voice/listener.py        → mic → wake word → transcribed command string
├── voice/claude_agent.py    → command string → Claude API → JSON action → execute + TTS
├── hud.py                   → OpenCV overlay drawn on webcam frame
└── config.py                → tuning constants + IS_MAC / IS_WINDOWS flags
```

`main.py` runs a `CameraStream` (background thread) feeding into a single OpenCV display loop on the main thread. Both `HandTracker` and `FaceTracker` are called sequentially each frame. Voice listening is a separate background daemon thread. Claude API calls and TTS each run on their own daemon threads so neither blocks the vision loop.

## Key Design Decisions

### MediaPipe version
Uses **mediapipe >= 0.10.30** (ARM macOS only ships 0.10.30+). This version removed `mp.solutions` — the code uses the new **Tasks API** with `RunningMode.VIDEO`. Two model files required in project root:
- `hand_landmarker.task` (7.5MB) — hand tracking
- `face_landmarker.task` (3.9MB) — iris/face tracking

### Eye tracking — iris landmarks
`face_tracker.py` uses `FaceLandmarker` with iris output enabled. Key landmark indices:
- Left iris center: **468**
- Right iris center: **473**

Both are in normalized [0,1] frame coords. `EYE_PREFER` in config selects left, right, or average. Average is most stable when both eyes are visible.

### Gaze calibration
`vision/gaze.py` — `GazeCalibrator` collects 9 (iris_x, iris_y) → (screen_x, screen_y) pairs during a fullscreen calibration phase, then fits a **2D affine transform** via `numpy.linalg.lstsq`. The 3×2 matrix `A` satisfies `[ix, iy, 1] @ A = [sx, sy]`.

At runtime, `GazeMapper.map(iris_x, iris_y)` applies this matrix and applies exponential smoothing (`GAZE_SMOOTHING=0.08` — lower than hand smoothing because eyes move faster). Result is passed directly to `pyautogui.moveTo()` — bypasses `MouseController.move()` since calibration already handles screen mapping.

Calibration is saved to `calibration.pkl` (pickle). `--recalibrate` CLI flag forces redo. Auto-advances after 4s timeout per point if no pinch detected.

### Calibration UI
Runs as a fullscreen OpenCV window before the main loop. 9 points shown one at a time. User looks at dot + pinches to confirm. Pulsing animation on active dot, green flash on capture. The calibration window is destroyed before the main HUD window opens.

### Camera backend
`CameraStream` wraps `cv2.VideoCapture` in a background reader thread — required on macOS because AVFoundation blocks the main thread unpredictably.
- **Windows**: `cv2.VideoCapture(index, cv2.CAP_DSHOW)`
- **macOS**: `cv2.VideoCapture(index)` + `time.sleep(1.0)` before reader thread starts

### Gesture detection
`gesture.py` uses pure geometry — no ML classifier. Each finger is "extended" if its tip is farther from the wrist than its MCP joint. Pinch = normalized thumb-index distance < 0.35.

Landmark indices (MediaPipe spec):
- `0` = WRIST, `4` = THUMB_TIP, `8` = INDEX_TIP, `5` = INDEX_MCP
- `12` = MIDDLE_TIP, `9` = MIDDLE_MCP, `16` = RING_TIP, `13` = RING_MCP
- `20` = PINKY_TIP, `17` = PINKY_MCP

### Hand gestures in 2.0
`GestureType.CURSOR` is no longer used for cursor control (eyes do that). Remaining gestures:
- `CLICK` → left click (pinch)
- `SCROLL` → joystick-style (V-sign, hand Y = speed/direction)
- `RIGHT_CLICK` → open palm
- `PAUSE` → both fists simultaneously (rising-edge trigger)

### Click debounce
`MouseController` tracks `_last_click_time` and `_clicking` bool. Fires only if `time.time() - last_click_time > CLICK_DEBOUNCE` (0.5s). `release_click()` called when gesture leaves CLICK.

### Scroll (joystick-style)
V-sign hand Y position controls scroll speed/direction. Dead zone ±12% from frame center. Outside dead zone, speed scales linearly. No delta tracking — absolute position drives direction.

### Pause gesture
Both hands fist simultaneously. Rising-edge triggered (`both_fists and not prev_both_fists`).

### Voice + Claude layer
`VoiceListener` uses Google STT. Wake word `"jarvis"`. `ClaudeAgent` sends to `claude-opus-4-6`, expects JSON-only response. Platform-aware dispatch: `open -a` on macOS, `start "" <exe>` on Windows. TTS via `pyttsx3` in background thread with lock.

## Gesture → Action Map (2.0)

| GestureType | Hand pose | Action |
|---|---|---|
| `CURSOR` | (unused — eyes control cursor) | — |
| `CLICK` | Pinch (thumb + index close) | Left click (debounced) |
| `SCROLL` | V-sign — hand Y = scroll speed/direction | Scroll |
| `RIGHT_CLICK` | All 5 fingers extended | Right click (debounced) |
| `PAUSE` | Both fists simultaneously | Toggle tracking on/off |
| `NONE` | Anything else | No action |

## File Responsibilities

| File | Owns |
|---|---|
| `config.py` | All tuning constants + platform flags + eye tracking config |
| `vision/hand_tracker.py` | MediaPipe HandLandmarker, frame → up to 2 landmark lists |
| `vision/face_tracker.py` | MediaPipe FaceLandmarker, frame → iris centers, crosshair drawing |
| `vision/gesture.py` | Geometry math, `classify()`, `GestureType` enum |
| `vision/gaze.py` | `GazeCalibrator` (affine fit, save/load), `GazeMapper` (runtime mapping + smoothing) |
| `control/mouse.py` | `MouseController` — click, scroll, right-click, debounce |
| `control/keyboard.py` | Thin wrappers around `pyautogui.hotkey/press/typewrite` |
| `voice/listener.py` | `VoiceListener` — mic thread, wake word, `command_queue` |
| `voice/claude_agent.py` | `ClaudeAgent` — Claude API, JSON parse, platform-aware dispatch, TTS |
| `hud.py` | `draw(frame, gesture, paused)` — pure drawing, no state |
| `main.py` | `CameraStream`, calibration UI, main loop, gaze cursor, gesture routing |

## Environment Setup

### macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install portaudio && pip install pyaudio
curl -L "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -o hand_landmarker.task
curl -L "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" -o face_landmarker.task
export ANTHROPIC_API_KEY=sk-...
python3 main.py
```

### Windows
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyaudio
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -OutFile "hand_landmarker.task"
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" -OutFile "face_landmarker.task"
$env:ANTHROPIC_API_KEY="sk-..."
python main.py
```

## Common Issues

| Symptom | Platform | Cause | Fix |
|---|---|---|---|
| Cursor not following eyes | Both | Bad calibration | Run `python3 main.py --recalibrate`; ensure good face lighting |
| `face_landmarker.task` not found | Both | Model not downloaded | Re-run face model curl/Invoke-WebRequest |
| `hand_landmarker.task` not found | Both | Model not downloaded | Re-run hand model curl/Invoke-WebRequest |
| Camera opens but dropped frames | macOS | iPhone Continuity Camera active | Disconnect from Control Center or menu bar |
| Camera not opening | macOS | Terminal not in Camera permissions | System Settings → Privacy → Camera → enable Terminal |
| Camera not opening | Windows | Camera access blocked | Settings → Privacy → Camera → enable desktop apps |
| Clicks firing constantly | Both | Debounce too short | Raise `CLICK_DEBOUNCE` in `config.py` |
| Voice not triggering | Both | Mic permissions / noise | Check mic settings; raise `energy_threshold` in `listener.py` |
| `pyaudio` install fails | macOS | Missing portaudio | `brew install portaudio` first |
| `pyaudio` install fails | Windows | No compiler | Use pre-built wheel from lfd.uci.edu |
| Claude not responding | Both | Missing API key | Set `ANTHROPIC_API_KEY` env var |

## Dependencies

```
mediapipe>=0.10.30   # Tasks API; two models needed: hand + face
opencv-python        # Webcam capture + HUD + calibration UI
pyautogui            # System mouse/keyboard (cross-platform)
numpy                # Affine transform fit (pulled in by mediapipe)
SpeechRecognition    # Google STT via mic
anthropic            # Claude API client
pyttsx3              # TTS (cross-platform)
pyaudio              # Mic backend
```

## Extending

- **Improve calibration accuracy**: Replace affine with polynomial regression (`numpy.polyfit` 2D) — handles lens distortion better.
- **New gesture**: Add value to `GestureType`, detection logic in `gesture.py:classify()`, handle in `main.py` dispatch.
- **New voice action**: Add case in `ClaudeAgent._execute()`, update `SYSTEM_PROMPT`, add to both `APP_MAP_MAC` and `APP_MAP_WINDOWS`.
- **Swap STT**: Replace `recognize_google` in `listener.py` with Whisper — same interface, works offline.
- **Blink-to-click**: MediaPipe FaceLandmarker also outputs eye blendshapes (`eyeBlinkLeft`, `eyeBlinkRight`) — could detect deliberate slow blinks as an alternate click trigger.
