import pyttsx3
import threading
from typing import Any, cast


class TTS:
    def __init__(self):
        self._lock = threading.Lock()

    def _build_engine(self):
        engine = pyttsx3.init()

        # tune voice properties
        engine.setProperty('rate', 170)        # Setting speed of sound
        engine.setProperty('volume', 1.0)      # maximum volume

        # Selecting voice(,ale/female)
        voices = cast(list[Any], engine.getProperty('voices'))
        if voices:
            engine.setProperty('voice', voices[0].id)
        return engine

    def speak(self, text):
        try:
            if not text:
                return
            if len(text) > 500:
                text = text[:500]+"..."
            print("Jarvis Speaking...")

            # Keep pyttsx3 on the calling thread for better Windows stability.
            with self._lock:
                engine = self._build_engine()
                engine.say(text)
                engine.runAndWait()
                engine.stop()
        except Exception as e:
            print(f"TTS Error: {e}")

    def close(self):
        return

# if __name__ == "__main__":
#     tts = TTS()
#     tts.speak("Hello, I am Jarvis, How can I help you?")
