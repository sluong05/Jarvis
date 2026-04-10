import json
import platform
import subprocess
import threading
import ollama
import pyttsx3
from control import keyboard
import config

IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

SYSTEM_PROMPT = """You are Jarvis, an AI assistant controlling a computer via voice commands.
When given a voice command, respond ONLY with a valid JSON object (no markdown, no explanation) with this schema:

{
  "action": "<action_name>",
  "target": "<optional target>",
  "text": "<optional text to type>",
  "speak": "<short spoken response to user>"
}

Available actions:
- "open_app": open an application. target = app name (e.g. "chrome", "terminal", "explorer", "vscode")
- "type_text": type text. text = what to type
- "hotkey": press a keyboard shortcut. target = keys joined by + (e.g. "ctrl+c", "cmd+tab", "win+d")
- "screenshot": take a screenshot
- "scroll_up": scroll up
- "scroll_down": scroll down
- "none": no action, just respond conversationally

Keep the "speak" field short (1-2 sentences max). Sound like Tony Stark's Jarvis — confident and concise.
Respond with JSON only. No extra text, no markdown fences."""

APP_MAP_MAC = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "firefox": "Firefox",
    "terminal": "Terminal",
    "finder": "Finder",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "spotify": "Spotify",
    "slack": "Slack",
    "notes": "Notes",
    "calendar": "Calendar",
    "mail": "Mail",
}

APP_MAP_WINDOWS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "explorer": "explorer",
    "file explorer": "explorer",
    "vscode": "code",
    "vs code": "code",
    "spotify": "spotify",
    "slack": "slack",
    "terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    "calculator": "calc",
    "paint": "mspaint",
}


class ClaudeAgent:
    def __init__(self):
        self._tts_engine = pyttsx3.init()
        self._tts_engine.setProperty("rate", 175)
        self._tts_lock = threading.Lock()
        print(f"[Jarvis] Voice model: {config.OLLAMA_MODEL} (Ollama — local, free)")

    def handle_command(self, command: str):
        """Send command to local Ollama model, parse response, execute, speak."""
        try:
            response = ollama.chat(
                model=config.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": command},
                ],
            )
            raw = response["message"]["content"].strip()
            # Strip markdown fences if the model adds them anyway
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            print(f"[Jarvis] Response: {raw}")
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"action": "none", "speak": "Sorry, I didn't quite catch that."}
        except Exception as e:
            print(f"[Jarvis] Error: {e}")
            data = {"action": "none", "speak": "I encountered an error."}

        self._execute(data)
        speak_text = data.get("speak", "")
        if speak_text:
            self._speak(speak_text)

    def _execute(self, data: dict):
        action = data.get("action", "none")
        target = data.get("target", "")
        text = data.get("text", "")

        if action == "open_app":
            self._open_app(target)

        elif action == "type_text":
            if text:
                keyboard.typewrite(text)

        elif action == "hotkey":
            if target:
                keys = target.replace("+", " ").split()
                keyboard.hotkey(*keys)

        elif action == "screenshot":
            if IS_MAC:
                keyboard.hotkey("cmd", "shift", "3")
            else:
                keyboard.hotkey("win", "shift", "s")

        elif action == "scroll_up":
            import pyautogui
            pyautogui.scroll(10)

        elif action == "scroll_down":
            import pyautogui
            pyautogui.scroll(-10)

    def _open_app(self, target: str):
        key = target.lower().strip()
        if IS_MAC:
            app_name = APP_MAP_MAC.get(key, target)
            subprocess.Popen(["open", "-a", app_name])
        elif IS_WINDOWS:
            exe = APP_MAP_WINDOWS.get(key, target)
            subprocess.Popen(["start", "", exe], shell=True)
        else:
            subprocess.Popen([key])

    def _speak(self, text: str):
        def _run():
            with self._tts_lock:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
        threading.Thread(target=_run, daemon=True).start()
