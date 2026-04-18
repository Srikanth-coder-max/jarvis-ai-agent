import io
import re
import wave
from typing import Optional

import requests
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np

from config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_STT_MODEL,
    STT_BEAM_SIZE,
    STT_INITIAL_PROMPT,
    STT_LANGUAGE,
    STT_LOCAL_COMPUTE_TYPE,
    STT_LOCAL_MODEL,
    STT_PROVIDER,
)

class STT:
    def __init__(self):
        self.provider = STT_PROVIDER

        # Loading the whisper model for local transcription
        self.model: Optional[WhisperModel] = None
        if self.provider != "groq":
            self.model = WhisperModel(
                STT_LOCAL_MODEL,
                device="cpu",        # no GPU usage
                compute_type=STT_LOCAL_COMPUTE_TYPE,
            )

    def _record_audio(self, duration):
        print("Listening")
        audio = sd.rec(
            int(duration * 16000),
            samplerate=16000,
            channels=1,
            dtype="float32"
        )
        sd.wait()
        print("Processing...")
        return np.squeeze(audio).astype(np.float32)

    def _transcribe_local(self, audio):
        if self.model is None:
            return "STT Error: Local Whisper model is not initialized."

        segments, _ = self.model.transcribe(
            audio,
            beam_size=max(1, STT_BEAM_SIZE),
            language=STT_LANGUAGE or None,
            initial_prompt=STT_INITIAL_PROMPT or None,
            condition_on_previous_text=False,
            vad_filter=True,
            temperature=0.0,
        )

        text = ""
        for segment in segments:
            text += segment.text
        return self._normalize_transcript(text.strip())

    def _audio_to_wav_bytes(self, audio):
        clipped = np.clip(audio, -1.0, 1.0)
        pcm16 = (clipped * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm16.tobytes())

        buffer.seek(0)
        return buffer

    def _transcribe_groq(self, audio):
        if not GROQ_API_KEY:
            return "STT Error: GROQ_API_KEY is not set."

        wav_buffer = self._audio_to_wav_bytes(audio)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        files = {
            "file": ("speech.wav", wav_buffer, "audio/wav")
        }
        data = {
            "model": GROQ_STT_MODEL,
            "language": STT_LANGUAGE,
            "prompt": STT_INITIAL_PROMPT,
        }

        response = requests.post(
            f"{GROQ_BASE_URL}/audio/transcriptions",
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("text", "").strip()
        return self._normalize_transcript(text)

    def _normalize_transcript(self, text):
        if not text:
            return text

        normalized = text
        # Common STT confusions for place names in local weather queries.
        replacements = {
            r"\brani\s+pit\b": "Ranipet",
            r"\bvellu\b": "Vellore",
            r"\bbaora\b": "Vellore",
        }

        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        return normalized
    
    def listen(self, duration=15):
        # reponsible for recording from microphone and converting into text
        try:
            audio = self._record_audio(duration)

            if self.provider == "groq":
                return self._transcribe_groq(audio)

            return self._transcribe_local(audio)
        except Exception as e:
            return f"STT Error: {e}"

# if __name__ == "__main__":
#     stt = STT()
#     result = stt.listen(5)
#     print("I said:", result)

