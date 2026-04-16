import sys
from core.llm_client import LLMClient
from core.brain import Brain


def main():
    # Initialize core components
    client = LLMClient()
    brain = Brain(client)

    # Check if voice mode is enabled
    voice_mode = "--voice" in sys.argv

    if voice_mode:
        from voice.stt import STT
        from voice.tts import TTS

        stt = STT()
        tts = TTS()

        print("Jarvis (voice mode) is ready. Say 'exit' or press Ctrl+C to stop.\n")

        while True:
            try:
                # Step 1: Listen
                user_input = stt.listen(duration=15)

                # Skip empty or failed input
                if not user_input or "STT Error" in user_input:
                    continue

                print(f"You said: {user_input}")

                # Exit condition (voice)
                if user_input.lower() in ["exit", "quit"]:
                    print("Exiting Jarvis. Goodbye!")
                    break

                # Step 2: Brain
                response = brain.chat(user_input)

                print(f"Jarvis: {response}")

                # Step 3: Speak
                tts.speak(response)

            except KeyboardInterrupt:
                print("\nInterrupted. Exiting Jarvis.")
                break

    else:
        # Text mode (unchanged)
        print("Jarvis (text mode) is ready. Type 'exit' or 'quit' to stop.\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    print("Exiting Jarvis. Goodbye!")
                    break

                response = brain.chat(user_input)

                print(f"Jarvis: {response}\n")

            except KeyboardInterrupt:
                print("\nInterrupted. Exiting Jarvis.")
                break


if __name__ == "__main__":
    main()