import threading
import queue
import speech_recognition as sr

WAKE_WORD = "jarvis"


class VoiceListener:
    """
    Background thread that listens for the wake word then captures a command.
    Puts transcribed command strings into self.command_queue.
    """

    def __init__(self):
        self.command_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _listen_loop(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("[Voice] Listening for 'Jarvis'...")
            while not self._stop_event.is_set():
                try:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"[Voice] Heard: {text}")

                    if WAKE_WORD in text:
                        # Strip wake word and queue the command
                        command = text.replace(WAKE_WORD, "").strip().lstrip(",").strip()
                        if command:
                            print(f"[Voice] Command: {command}")
                            self.command_queue.put(command)
                        else:
                            # Wake word only — listen for follow-up
                            print("[Voice] Waiting for command...")
                            try:
                                audio2 = self.recognizer.listen(source, timeout=4, phrase_time_limit=6)
                                command = self.recognizer.recognize_google(audio2).lower().strip()
                                print(f"[Voice] Command: {command}")
                                self.command_queue.put(command)
                            except (sr.WaitTimeoutError, sr.UnknownValueError):
                                pass

                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print(f"[Voice] Error: {e}")
