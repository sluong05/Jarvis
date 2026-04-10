# Jarvis — Hands-Free Computer Control

Control your computer without a mouse or keyboard. Two versions are available depending on your setup and preference.

---

## jarvis/

**Hand gesture control.** Your hand is the cursor — point your index finger to move it, pinch to click, and use other gestures to scroll and right-click. Voice commands are handled locally via Ollama.

Best for:
- Getting started quickly
- Environments where you can't position your face steadily in front of the camera
- Users who find hand control more intuitive

See [`jarvis/README.md`](jarvis/README.md) for setup and usage.

---

## jarvis2.0/

**Eye tracking control.** Your eyes move the cursor — look at what you want to interact with, then use hand gestures only for clicking, scrolling, and pausing. Runs a 9-point calibration on every launch to map your gaze to the screen. Voice commands are handled locally via Ollama.

Best for:
- A more natural, hands-free experience
- Demos — the eye tracking is the "wow factor"
- Users who want the full Tony Stark Jarvis feel

Requires a well-lit environment and a stable head position for accurate gaze tracking.

See [`jarvis2.0/README.md`](jarvis2.0/README.md) for setup and usage.

---

## Quick Comparison

| | jarvis | jarvis2.0 |
|---|---|---|
| Cursor control | Hand (index finger) | Eyes (iris tracking) |
| Click | Pinch | Pinch |
| Scroll | V-sign | V-sign |
| Pause | Both fists | Both fists |
| Voice | Ollama (local) | Ollama (local) |
| Calibration | None | 9-point on every launch |
| Setup complexity | Simple | Slightly more (face model + calibration) |

---

## Shared Requirements

Both versions require:
- Python 3.9+
- A webcam (built-in — do **not** use iPhone Continuity Camera on macOS)
- [Ollama](https://ollama.com) installed and running for voice commands
- `llama3.2` pulled via `ollama pull llama3.2`
