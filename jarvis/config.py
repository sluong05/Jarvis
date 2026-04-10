import platform
import pyautogui

IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

# Screen dimensions
SCREEN_W, SCREEN_H = pyautogui.size()

# Smoothing factor for cursor (0=no movement, 1=raw/jittery)
SMOOTHING = 0.2

# Fraction of the frame edge (each side) that maps to the screen boundary.
# e.g. 0.15 means the hand only needs to reach 15% from the edge to hit the screen edge.
# Increase if you still can't reach corners; decrease if movement feels too sensitive.
CURSOR_MARGIN = 0.30

# Pinch click threshold (normalized distance between thumb tip and index tip)
PINCH_THRESHOLD = 0.15

# Click debounce in seconds
CLICK_DEBOUNCE = 0.5

# Scroll sensitivity (pixels per frame when scroll gesture active)
SCROLL_SPEED = 1

# Webcam index
CAM_INDEX = 0

# HUD display
SHOW_HUD = True

# MediaPipe detection confidence
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# Voice (Ollama)
OLLAMA_MODEL = "llama3.2"   # run `ollama pull llama3.2` to download
