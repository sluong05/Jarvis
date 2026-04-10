# Jarvis 2.0 — Eye Tracking Control

Control your computer with your eyes and hand gestures. No mouse, no keyboard. **Eyes move the cursor — hands click, scroll, and act.**

## Requirements

- Python 3.9+
- A webcam (built-in or external — do NOT use iPhone Continuity Camera)
- macOS or Windows
- Ollama (free, local AI for voice commands)

---

## Setup — macOS

**1. Create a virtual environment and install dependencies**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Install audio support**
```bash
brew install portaudio
pip install pyaudio
```

**3. Download both tracking models**
```bash
curl -L "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" \
     -o hand_landmarker.task

curl -L "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" \
     -o face_landmarker.task
```

**4. Set up Ollama (voice commands)**
```bash
# Install Ollama
brew install ollama

# Start the Ollama server (runs in background)
brew services start ollama

# Pull the voice model (~2GB, one-time download)
ollama pull llama3.2
```

**5. Run**
```bash
source venv/bin/activate
python3 main.py
```

> **Camera permissions:** The first time you run, macOS will ask for camera access. Click Allow. If it doesn't ask, go to System Settings → Privacy & Security → Camera and enable Terminal.

---

## Setup — Windows

**1. Create a virtual environment and install dependencies**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyaudio
```

**2. Download both tracking models**
```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -OutFile "hand_landmarker.task"
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" -OutFile "face_landmarker.task"
```

**3. Set up Ollama (voice commands)**

1. Download and install Ollama from **https://ollama.com/download**
2. Ollama starts automatically after install. To verify it's running, open a browser and go to `http://localhost:11434` — you should see `Ollama is running`.
3. Pull the voice model (~2GB, one-time download):
```powershell
ollama pull llama3.2
```

**4. Run**
```powershell
venv\Scripts\activate
python main.py
```

> **Camera permissions:** Windows may prompt for camera access the first time. Click Allow. If blocked, go to Settings → Privacy & Security → Camera and enable desktop apps.

> **PyAudio issues:** If `pip install pyaudio` fails, download the matching pre-built wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio and install with `pip install <wheel_file>.whl`.

---

## Calibration

Every launch, Jarvis 2.0 runs a **9-point calibration** to map your eye movement to the screen.

1. A fullscreen black screen appears with a glowing dot
2. Look directly at the dot
3. **Pinch** (thumb + index finger) to confirm your gaze
4. Repeat for all 9 dots
5. Jarvis starts immediately after

**Tips for good calibration:**
- Sit at a consistent distance from your screen (arm's length)
- Keep your head still while looking at each dot
- Good lighting on your face improves iris detection accuracy

---

## Controls

| Input | What to do | Action |
|---|---|---|
| **Eyes** | Look at what you want to interact with | Moves the cursor |
| **Click** | Pinch thumb and index finger together | Left click |
| **Scroll** | Hold up index + middle finger (V-sign) — raise hand to scroll up, lower to scroll down, center to stop | Scroll |
| **Right Click** | Open palm facing camera (all fingers spread) | Right click |
| **Pause** | Make a fist with both hands simultaneously | Freezes/unfreezes tracking |

---

## Voice Commands

Make sure Ollama is running, then say **"Jarvis"** followed by a command:

- *"Jarvis, open Chrome"*
- *"Jarvis, take a screenshot"*
- *"Jarvis, copy"*
- *"Jarvis, type hello world"*
- *"Jarvis, scroll down"*

Voice runs fully locally — no internet or API key required.

**To change the voice model**, edit `OLLAMA_MODEL` in `config.py`. Available models: `llama3.2` (default, fast), `llama3.1` (larger, smarter). See all options at https://ollama.com/library.

---

## Troubleshooting

**Cursor not following eyes** — Recalibrate by restarting. Ensure good lighting on your face and sit at a consistent distance.

**Calibration dot not responding to pinch** — Make sure your hand is visible in the webcam frame during calibration.

**Voice commands not working** — Make sure Ollama is running (`brew services start ollama` on Mac, or check that the Ollama app is open on Windows). Verify with `ollama list` — you should see `llama3.2` listed.

**Voice command slow to respond** — First command after idle takes a few seconds to load the model into memory. Subsequent commands are faster.

**`face_landmarker.task` not found** — Re-run the model download step.

**`hand_landmarker.task` not found** — Re-run the model download step.

**Camera not opening (macOS)** — System Settings → Privacy & Security → Camera → enable Terminal.app. Disconnect iPhone Continuity Camera if active.

**Camera not opening (Windows)** — Settings → Privacy & Security → Camera → enable desktop apps.

**Clicks keep firing accidentally** — Increase `CLICK_DEBOUNCE` in `config.py`.

**Voice not picking up** — Check microphone permissions. Speak clearly after the wake word.

**`pyaudio` install fails (Windows)** — Use the pre-built wheel (see setup step 1).
