# Jarvis — Hands-Free Computer Control

Control your computer with hand gestures and your voice. No mouse, no keyboard.

## Requirements

- Python 3.9+
- A webcam
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

**3. Download the hand tracking model**
```bash
curl -L "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" \
     -o hand_landmarker.task
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

**2. Download the hand tracking model**
```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -OutFile "hand_landmarker.task"
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

> **Camera permissions:** Windows may show a camera access prompt the first time. Click Allow. If camera access is blocked, go to Settings → Privacy & Security → Camera and enable it for desktop apps.

> **PyAudio issues:** If `pip install pyaudio` fails, download the matching pre-built wheel from [https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install with `pip install <wheel_file>.whl`.

---

## Gesture Controls

| Gesture | What to do | Action |
|---|---|---|
| **Cursor** | Point with index finger, curl others | Moves the mouse cursor |
| **Click** | Pinch thumb and index finger together | Left click |
| **Scroll** | Hold up index + middle finger (V-sign) — hand position controls direction: raise hand to scroll up, lower to scroll down, center to stop | Scroll the page |
| **Right Click** | Open palm facing camera (all fingers spread) | Right click |
| **Pause** | Make a fist with both hands simultaneously | Freezes/unfreezes tracking |

**Tips:**
- Keep your hand 1–2 feet from the camera for best results
- Move slowly at first — the cursor smooths out small shakes automatically
- You don't need to push your hand to the edge of the frame to reach screen corners

---

## Voice Commands

Make sure Ollama is running, then say **"Jarvis"** followed by a command:

- *"Jarvis, open Chrome"*
- *"Jarvis, take a screenshot"*
- *"Jarvis, copy"* → triggers Ctrl+C (or Cmd+C on Mac)
- *"Jarvis, type hello world"*
- *"Jarvis, scroll down"*

Voice runs fully locally — no internet or API key required.

**To change the voice model**, edit `OLLAMA_MODEL` in `config.py`. Available models: `llama3.2` (default, fast), `llama3.1` (larger, smarter). See all options at https://ollama.com/library.

---

## Troubleshooting

**Cursor moves in the wrong direction** — Make sure you disconnected iPhone Continuity Camera (macOS). The script expects the built-in webcam.

**Cursor is shaky** — Try keeping your hand steadier, or adjust `CURSOR_MARGIN` in `config.py` (higher = easier to reach edges, lower = more precision).

**Clicks keep firing accidentally** — Increase `CLICK_DEBOUNCE` in `config.py`.

**Voice commands not working** — Make sure Ollama is running (`brew services start ollama` on Mac, or check that the Ollama app is open on Windows). Verify with `ollama list` — you should see `llama3.2` listed.

**Voice command slow to respond** — First command after idle takes a few seconds to load the model into memory. Subsequent commands are faster.

**Voice not picking up** — Check microphone permissions. Try speaking more clearly after the wake word.

**`hand_landmarker.task` not found** — Re-run the download step.

**Camera not opening (macOS)** — Check System Settings → Privacy & Security → Camera. Make sure Terminal.app is enabled. Also disconnect iPhone Continuity Camera if active.

**Camera not opening (Windows)** — Check Settings → Privacy & Security → Camera. Make sure "Let desktop apps access your camera" is on.

**`pyaudio` install fails (Windows)** — Install via pre-built wheel (see Windows setup step 1 note above).
