from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np

class STT:
    def __init__(self):
        # Loading the whisper model
        self.model = WhisperModel(
            "base",                 # model size 
            device="cpu",           # no GPU usage
            compute_type="int8"     # low memory + faster on CPU
        )
    
    def listen(self, duration=10):
        # reponsible for recording from microphone and converting into text
        try:
            print("Listening")
            # Step 1: Record audio
            audio = sd.rec(
                int(duration * 16000), # samplerate (sample = duration * sample_rate)
                samplerate=16000,
                channels=1, # single channel for mono audio
                dtype='float32'
            )
            # Step 2: Wait for the recording to finish
            sd.wait()
            print('Processing...')
            audio = np.squeeze(audio).astype(np.float32) # converting to 1D to support the model format
            # Step 3: Transcribe
            segments, info = self.model.transcribe(
                audio,
                beam_size=1 # fast decoding (low latency)
            )
            # Step 4: Combine all segments into one string
            text = ""
            for segment in segments:
                text += segment.text
            return text.strip()
        except Exception as e:
            return f"STT Error: {e}"

# if __name__ == "__main__":
#     stt = STT()
#     result = stt.listen(5)
#     print("I said:", result)

