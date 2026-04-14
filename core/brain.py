import json
from rag.retriever import Retriever
from tools.registry import call_tool, list_tools
import tools.web_tools
import tools.system_tools  # Registers system tools via decorators
import tools.web_tools  # Registers web tools via decorators


class Brain:
    def __init__(self, llm_client):
        # Inject dependency instead of creating it -> loose coupling(flexible system)
        self.client = llm_client
        # Stores consersation manually -> state management (llm has no memory)
        self.history = []
        # Limit the size of memory to avoid the slow reponse or crashing the model
        self.max_history = 10
        # Retriever (RAG)
        self.retriever = Retriever()
        tools_description = list_tools()
        self.system_prompt = {
            "role": "system",
            "content": (
            "You are Jarvis, a precise and concise AI assistant.\n\n"

            "You have access to tools.\n\n"

            "RULES:\n"
            "1. ONLY call a tool if the user explicitly asks for system stats, process list, kill a process, or weather.\n"
            "2. For all other questions — answer from your own knowledge in plain text.\n"
            "3. For greetings and identity questions — respond directly.\n"
            "4. DO NOT call a tool for general knowledge questions like ML, programming, or concepts.\n"
            "5. ONLY respond in JSON when calling a tool.\n\n"

            "FORMAT (tool call only):\n"
            '{"tool": "tool_name", "arguments": {...}}\n\n'

            "EXAMPLES:\n"
            "User: Check my system usage\n"
            '{"tool": "get_system_stats", "arguments": {}}\n\n'
            "User: What is the weather in Chennai?\n"
            '{"tool": "get_weather", "arguments": {"city": "Chennai"}}\n\n'
            "User: What is your name?\n"
            "I am Jarvis, your personal AI assistant.\n\n"

            "Available tools:\n"
            f"{tools_description}\n"
            )
        }  # defining with behaviour rules

    def chat(self, user_input, stream=False):
        # Step 1: retriever relevant context
        if "system" in user_input.lower() or len(user_input.split()) <= 4:
            context_chunks = []
        else:
            context_chunks = self.retriever.retrieve(user_input)[:2]
        # Combine retrieved chunks
        context = "\n".join(context_chunks)
        # Step 2: Build augument input
        if context:
            augument_input = f"""
Context:{context}
Question:{user_input}
"""
        else:
            augument_input = user_input
        # Step 3: Add to histroy
        user_message = {
            'role': 'user',
            'content': augument_input
        }  # converting the raw_input to memory -> structured format ->interface standardization
        self.history.append(user_message)  # add new input to memory
        # keep only recent messages
        self.history = self.history[-self.max_history:]
        messages = [self.system_prompt] + \
            self.history  # combines the rules + memory
        if stream:  # deciding the execution mode
            response = self.client.stream(messages)  # streaming
        else:
            response = self._run_tool_loop(messages)

        assistant_message = {
            'role': 'assistant',
            'content': response
        }
        self.history.append(assistant_message)
        return response

    def _parse_tool_call(self, response):
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Support fenced JSON responses from the model.
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()

        try:
            # Step 1: Try to parse response as JSON
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try extracting the first JSON object from mixed text.
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                data = json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                # If parsing fails -> it's normal text
                return None
        # Step 2: Check if required key exist
        if "tool" in data:
            tool_name = data["tool"]
            arguments = data.get("arguments", {})

            # Step 3: Validates types
            if isinstance(tool_name, str) and isinstance(arguments, dict):
                return tool_name, arguments
        # Step 4: Not a valid tool call
        return None

    def _run_tool_loop(self, messages):
        max_loops = 3
        for loop_idx in range(max_loops):
            # Step 1: get response from LLM
            response = self.client.generate(messages)
            # Step 2: check if tool call
            tool_call = self._parse_tool_call(response)

            # if not tool_call:
            #     last_user = messages[-1]['content'].lower()

            #     if 'weather' in last_user:
            #         import re
            #         match = re.search(r'weather in (\w+)', last_user)
            #         if match:
            #             city = match.group(1)
            #         else:
            #             city = "Ranipet"
            #         tool_call = ('get_weather', {'city': city})

            if tool_call:
                # Step 3: extract tool name and arguments
                tool_name, arguments = tool_call

                # step 4: execute tool
                result = call_tool(tool_name, arguments)

                # Step 5: send the result back to LLM
                # 5.1 Keep assistant tool-call trace for coherence.
                messages.append({
                    "role": "assistant",
                    "content": json.dumps({"tool": tool_name, "arguments": arguments})
                })
                # 5.2 Feed tool output to model and request final answer.
                messages.append({
                    "role": "user",
                    "content": (
                        "Tool result:\n"
                        f"{json.dumps(result, ensure_ascii=True)}\n\n"
                        "Now provide the final user-facing answer using this result. "
                        "Do not call any more tools."
                    )
                })

            else:
                # Step 6: normal response-> return
                return response
        # step 6: fallback safety
        return "Error: Max tool iteration reached"

    def reset(self):
        self.history = []  # clearing the memory


if __name__ == "__main__":
    from core.llm_client import LLMClient
    brain = Brain(LLMClient())
