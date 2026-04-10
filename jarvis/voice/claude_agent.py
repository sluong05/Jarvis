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
- "open_url": open a website in the default browser. target = site name (e.g. "netflix", "youtube", "gmail") or a full URL
- "type_text": type text. text = what to type
- "delete_text": delete everything in the current field (select all + delete). Use for "delete everything", "clear that", "backspace everything"
- "backspace": press backspace N times. target = number as a string (e.g. "5", "20"). Use for "delete 3 words", "backspace 10 times"
- "hotkey": press a keyboard shortcut. target = keys joined by + (e.g. "ctrl+c", "cmd+tab", "win+d")
- "screenshot": take a screenshot
- "scroll_up": scroll up
- "scroll_down": scroll down
- "none": no action, just respond conversationally

Prefer "open_url" over "open_app" for streaming services, social media, and web-based tools (e.g. Netflix, YouTube, Gmail, Twitter, Reddit).
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

URL_MAP = {
    "netflix": "https://www.netflix.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "github": "https://www.github.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "reddit": "https://www.reddit.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "hulu": "https://www.hulu.com",
    "disney plus": "https://www.disneyplus.com",
    "disney+": "https://www.disneyplus.com",
    "twitch": "https://www.twitch.tv",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "notion": "https://www.notion.so",
    "figma": "https://www.figma.com",
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

        elif action == "open_url":
            self._open_url(target)

        elif action == "type_text":
            if text:
                keyboard.typewrite(text)

        elif action == "delete_text":
            if IS_MAC:
                keyboard.hotkey("cmd", "a")
            else:
                keyboard.hotkey("ctrl", "a")
            keyboard.press("backspace")

        elif action == "backspace":
            try:
                count = int(target) if target else 1
            except ValueError:
                count = 1
            for _ in range(count):
                keyboard.press("backspace")

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

    def _open_url(self, target: str):
        key = target.lower().strip()
        url = URL_MAP.get(key, target if target.startswith("http") else f"https://{target}")
        if IS_MAC:
            subprocess.Popen(["open", url])
        elif IS_WINDOWS:
            subprocess.Popen(["start", "", url], shell=True)
        else:
            subprocess.Popen(["xdg-open", url])

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
