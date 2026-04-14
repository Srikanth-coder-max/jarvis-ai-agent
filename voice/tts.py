import pyttsx3
import threading

class TTS:
    def __init__(self):
        # Initializing TTS Engine
        self.engine = pyttsx3.init()

        # tune voice properties
        self.engine.setProperty('rate', 170)        # Setting speed of sound
        self.engine.setProperty('volume', 1.0)      # maximum volume

        # Selecting voice(,ale/female)
        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[0].id)

    def speak(self, text):
        # Convert TTS in a separate thread to prevent blocking
        try:
            if not text:
                return
            if len(text) > 500:
                text = text[:500]+"..."
            print("Jarvis Speaking...")
            
            # Stop any ongoing speech
            self.engine.stop()
            
            # Clear the queue
            self.engine.setProperty('rate', 170)
            
            # Say the text
            self.engine.say(text)
            
            # Run in thread to prevent blocking
            thread = threading.Thread(target=self.engine.runAndWait)
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)  # Wait max 10 seconds
            
        except Exception as e:
            print(f"TTS Error: {e}")

# if __name__ == "__main__":
#     tts = TTS()
#     tts.speak("Hello, I am Jarvis, How can I help you?")
