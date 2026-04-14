from core.llm_client import LLMClient
from core.brain import Brain

def main():
    # Initialize core components
    client = LLMClient()
    brain = Brain(client)

    print("Jarvis is ready. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            # Get the user input
            user_input = input("You: ").strip()
            # Skip empty input
            if not user_input:
                continue
            #Exit condition
            if user_input.lower() in ['exit','quit']:
                print('Exiting Jarvis. Bye!bye!')
                break
            # Get the response from brain
            response = brain.chat(user_input)
            print(f"Jarvis: {response}\n")
        except KeyboardInterrupt:
            # handle Ctrl+C gracefully
            print("\n Interrupted. Exiting Jarvis")
            break

if __name__ == "__main__":
    main()

