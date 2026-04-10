# Jarvis — Developer Reference

## What This Is
Hands-free computer control via webcam hand tracking + Claude voice commands. Built in Python for a Claude Code hackathon. The demo story is "Tony Stark's Jarvis" — control your entire machine with no mouse or keyboard. Runs on macOS and Windows.

## Architecture Overview

```
main.py
├── vision/hand_tracker.py   → webcam frame → 21 hand keypoints (up to 2 hands)
├── vision/gesture.py        → keypoints → GestureType enum
├── control/mouse.py         → GestureType → pyautogui mouse actions
├── control/keyboard.py      → hotkeys / typewrite helpers
├── voice/listener.py        → mic → wake word → transcribed command string
├── voice/claude_agent.py    → command string → Claude API → JSON action → execute + TTS
├── hud.py                   → OpenCV overlay drawn on webcam frame
└── config.py                → tuning constants + IS_MAC / IS_WINDOWS flags
```

`main.py` runs a `CameraStream` (background thread) feeding into a single OpenCV display loop on the main thread. Voice listening is a separate background daemon thread. Claude API calls and TTS each run on their own daemon threads so neither blocks the vision loop.

## Key Design Decisions

### MediaPipe version
Uses **mediapipe >= 0.10.30** (ARM macOS only ships 0.10.30+). This version removed `mp.solutions` — the code uses the new **Tasks API** (`mediapipe.tasks.python.vision.HandLandmarker`) with `RunningMode.VIDEO` and `num_hands=2`. The model file `hand_landmarker.task` (7.5MB) must be present in the project root — downloaded separately (not in pip).

### Camera backend
`CameraStream` in `main.py` wraps `cv2.VideoCapture` in a background reader thread — required on macOS because AVFoundation blocks the main thread unpredictably. Platform selection:
- **Windows**: `cv2.VideoCapture(index, cv2.CAP_DSHOW)` — DirectShow backend, no warmup delay needed
- **macOS**: `cv2.VideoCapture(index)` — AVFoundation, requires `time.sleep(1.0)` before the reader thread starts to let macOS fully initialize the stream

`config.IS_MAC` / `config.IS_WINDOWS` are set via `platform.system()` and used to branch this and other platform-specific logic.

### Gesture detection
`gesture.py` uses pure geometry on the 21 MediaPipe landmarks — no ML classifier. Each finger is "extended" if its tip is farther from the wrist than its MCP joint. Pinch is detected by normalizing thumb-index distance against hand size (wrist-to-middle-MCP).

Landmark indices (MediaPipe spec):
- `0` = WRIST, `4` = THUMB_TIP, `8` = INDEX_TIP, `5` = INDEX_MCP
- `12` = MIDDLE_TIP, `9` = MIDDLE_MCP, `16` = RING_TIP, `13` = RING_MCP
- `20` = PINKY_TIP, `17` = PINKY_MCP

### Cursor mapping
Index fingertip normalized coords [0,1] are remapped using `CURSOR_MARGIN` so the hand doesn't need to reach the frame edge to hit the screen edge. Formula: `(norm - margin) / (1 - 2*margin)`, clamped to [0,1]. The frame is flipped horizontally (`cv2.flip`) before MediaPipe processes it, so no additional X-axis flip is needed in mouse coordinates.

### Cursor smoothing
Exponential moving average: `cursor += SMOOTHING * (target - cursor)`. `SMOOTHING=0.2` in config. Lower = smoother/laggier.

### Click debounce
`MouseController` tracks `_last_click_time` and `_clicking` bool. Click fires only if `time.time() - last_click_time > CLICK_DEBOUNCE` (0.5s) and the previous frame was not already CLICK. `release_click()` must be called when gesture leaves CLICK state.

### Scroll (joystick-style)
V-sign gesture maps hand Y position to scroll speed/direction. Dead zone at ±12% from frame center. Outside dead zone, speed scales linearly to max. No delta tracking — absolute position drives direction. This avoids drift from delta-based approaches.

### Pause gesture
Requires **both hands in a fist simultaneously**. `hand_tracker.py` returns up to 2 hand landmark sets. `main.py` calls `classify()` on each and checks both return `GestureType.PAUSE`. Triggers on the rising edge (`both_fists and not prev_both_fists`) to avoid repeated toggles.

### Voice + Claude layer
`VoiceListener` uses Google STT via `speech_recognition`. Wake word is `"jarvis"`. On detection it either parses the remainder of the utterance as the command, or opens a second listen window for a follow-up phrase.

`ClaudeAgent.handle_command()` sends to `claude-opus-4-6` with a strict JSON-only system prompt. Response parsed with `json.loads` — fallback dict on failure (no crash). Platform-aware dispatch:
- `open_app`: `open -a <name>` on macOS, `start "" <exe>` (shell=True) on Windows
- `screenshot`: `cmd+shift+3` on macOS, `win+shift+s` on Windows
- `hotkey`: keys split on `+` and passed to `pyautogui.hotkey()`

TTS via `pyttsx3`, runs in its own thread behind a lock to prevent concurrent speech.

## Gesture → Action Map

| GestureType | Hand pose | Action |
|---|---|---|
| `CURSOR` | Index up, others curled | Move mouse cursor |
| `CLICK` | Pinch (thumb + index close, others curled) | Left click (debounced) |
| `SCROLL` | Index + middle up — hand Y position = scroll speed/direction | Scroll |
| `RIGHT_CLICK` | All 5 fingers extended | Right click (debounced) |
| `PAUSE` | Fist — used only in both-hands-fist check | Toggle tracking on/off |
| `NONE` | Anything else | No action |

## File Responsibilities

| File | Owns |
|---|---|
| `config.py` | All tuning constants + `IS_MAC` / `IS_WINDOWS` platform flags |
| `vision/hand_tracker.py` | MediaPipe session lifecycle, frame → up to 2 landmark lists, skeleton drawing |
| `vision/gesture.py` | Geometry math, `classify()` function, `GestureType` enum |
| `control/mouse.py` | `MouseController` — all pyautogui mouse calls, smoothing, debounce, joystick scroll |
| `control/keyboard.py` | Thin wrappers around `pyautogui.hotkey/press/typewrite` |
| `voice/listener.py` | `VoiceListener` — mic thread, wake word logic, `command_queue` |
| `voice/claude_agent.py` | `ClaudeAgent` — Claude API, JSON parse, platform-aware action dispatch, TTS |
| `hud.py` | `draw(frame, gesture, paused)` — pure drawing, no state |
| `main.py` | `CameraStream` class, main loop, gesture→controller routing, voice queue drain |

## Environment Setup

### macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install portaudio && pip install pyaudio
curl -L "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" \
     -o hand_landmarker.task
export ANTHROPIC_API_KEY=sk-...
python3 main.py
```

### Windows
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyaudio   # pre-built wheel, no portaudio needed
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -OutFile "hand_landmarker.task"
$env:ANTHROPIC_API_KEY="sk-..."
python main.py
```
If `pip install pyaudio` fails on Windows, download the matching `.whl` from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio and install with `pip install <file>.whl`.

## Common Issues

| Symptom | Platform | Cause | Fix |
|---|---|---|---|
| `module 'mediapipe' has no attribute 'solutions'` | Both | Old code path | Tasks API is used — already fixed |
| `hand_landmarker.task` not found | Both | Model file missing | Re-run the download command |
| Camera opens but no frames (dropped frames loop) | macOS | iPhone Continuity Camera active, or AVFoundation timing | Disconnect Continuity Camera; script adds `sleep(1.0)` before reader thread |
| Camera not opening at all | macOS | Terminal not in Camera privacy list | System Settings → Privacy & Security → Camera → enable Terminal |
| Camera not opening at all | Windows | Camera access blocked | Settings → Privacy & Security → Camera → enable desktop apps |
| Cursor jitter | Both | SMOOTHING too high | Lower `SMOOTHING` in `config.py` (try 0.1) |
| Can't reach screen edges | Both | CURSOR_MARGIN too low | Raise `CURSOR_MARGIN` in `config.py` |
| Clicks firing constantly | Both | Debounce too short | Raise `CLICK_DEBOUNCE` in `config.py` |
| Voice not triggering | Both | Mic permissions / noise | Check mic privacy settings; raise `energy_threshold` in `listener.py` |
| `pyaudio` install fails | macOS | Missing portaudio | `brew install portaudio` first |
| `pyaudio` install fails | Windows | No compiler / missing wheel | Use pre-built wheel from lfd.uci.edu |
| Claude not responding | Both | Missing API key | Set `ANTHROPIC_API_KEY` env var |

## Dependencies

```
mediapipe>=0.10.30   # Tasks API; ARM macOS only has 0.10.30+
opencv-python        # Webcam capture + HUD drawing
pyautogui            # System mouse/keyboard control (cross-platform)
SpeechRecognition    # Google STT via mic
anthropic            # Claude API client
pyttsx3              # TTS (cross-platform)
pyaudio              # Mic backend (brew+pip on macOS, pip-only on Windows)
```

## Extending

- **New gesture**: Add value to `GestureType`, detection logic in `gesture.py:classify()`, handle in `main.py` dispatch block.
- **New voice action**: Add case in `ClaudeAgent._execute()`, update `SYSTEM_PROMPT` action list, add to both `APP_MAP_MAC` and `APP_MAP_WINDOWS` if app-related.
- **New platform branch**: Check `config.IS_MAC` / `config.IS_WINDOWS` — add Linux support the same way.
- **Swap STT**: Replace `recognize_google` in `listener.py` with Whisper (`openai-whisper`) — same interface, works offline.
- **Add eye tracking**: Layer `mediapipe.tasks.python.vision.FaceLandmarker` — iris landmarks are indices 468-477.
