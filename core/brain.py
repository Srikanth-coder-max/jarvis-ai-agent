import json
import re
from rag.retriever import Retriever
from tools.registry import call_tool, list_tools
from core.memory import ConversationArchive, ConversationMemory, UserProfileMemory
from config import (
    CHAT_MEMORY_PATH,
    CHROMA_PATH,
    CONVERSATION_MEMORY_COLLECTION,
    CONVERSATION_MEMORY_RECALL_K,
    EMBED_MODEL,
    MAX_CHAT_HISTORY,
    USER_PROFILE_PATH,
)
import tools.system_tools  # Registers system tools via decorators
import tools.web_tools  # Registers web tools via decorators


class Brain:
    def __init__(self, llm_client):
        # Inject dependency instead of creating it -> loose coupling(flexible system)
        self.client = llm_client
        # Limit the size of memory to avoid the slow reponse or crashing the model
        self.max_history = MAX_CHAT_HISTORY
        self.memory_store = ConversationMemory(CHAT_MEMORY_PATH, self.max_history)
        self.profile_store = UserProfileMemory(USER_PROFILE_PATH)
        self.archive_store = ConversationArchive(
            chroma_path=CHROMA_PATH,
            embed_model=EMBED_MODEL,
            collection_name=CONVERSATION_MEMORY_COLLECTION,
        )
        # Stores conversation and restores the last turns across restarts.
        self.history = self.memory_store.load_history()
        # Retriever (RAG)
        self.retriever = Retriever()
        tools_description = list_tools()
        self.system_prompt = {
            "role": "system",
            "content": (
            "You are Jarvis, a precise and concise AI assistant.\n\n"

            "You have access to tools.\n\n"

            "RULES:\n"
            "1. ONLY call a tool if the user explicitly asks for system stats, process list, kill a process, weather, or latest/current web information.\n"
            "2. For all other questions — answer from your own knowledge in plain text.\n"
            "3. For greetings and identity questions — respond directly.\n"
            "4. For thought, opinion, suggestion, comparison, and advice questions — always answer directly in plain text.\n"
            "5. For latest news/current affairs/real-time topics — call search_web.\n"
            "6. DO NOT call a tool for general knowledge questions like ML, programming, concepts, or opinions.\n"
            "7. ONLY respond in JSON when calling a tool.\n\n"

            "FORMAT (tool call only):\n"
            '{"tool": "tool_name", "arguments": {...}}\n\n'

            "EXAMPLES:\n"
            "User: Check my system usage\n"
            '{"tool": "get_system_stats", "arguments": {}}\n\n'
            "User: What is the weather in Chennai?\n"
            '{"tool": "get_weather", "arguments": {"city": "Chennai"}}\n\n'
            "User: What is the latest AI news this week?\n"
            '{"tool": "search_web", "arguments": {"query": "latest AI news this week", "max_results": 5}}\n\n'
            "User: What is your name?\n"
            "I am Jarvis, your personal AI assistant.\n\n"
            "User: What do you think about electric cars?\n"
            "Electric cars are strong for efficiency and low running costs, while charging access and battery cost are key tradeoffs.\n\n"

            "Available tools:\n"
            f"{tools_description}\n"
            )
        }  # defining with behaviour rules

    def _extract_user_name(self, text):
        pattern = re.compile(r"\b(?:my name is|i am|i'm)\s+([a-zA-Z][a-zA-Z\-']{1,30})\b", re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return ""

        candidate = match.group(1).strip()
        blocked = {"fine", "good", "okay", "ok", "straight", "here", "ready"}
        if candidate.lower() in blocked:
            return ""
        return candidate.title()

    def _is_identity_question(self, text):
        lowered = text.lower()
        triggers = [
            "who am i",
            "do you know me",
            "remember my name",
            "what is my name",
        ]
        return any(token in lowered for token in triggers)

    def _build_conversation_memory_context(self, user_input):
        recalled = self.archive_store.recall(user_input, CONVERSATION_MEMORY_RECALL_K)
        if not recalled:
            return ""

        lines = []
        for item in recalled:
            role = item.get("role", "memory")
            content = item.get("content", "").strip()
            if not content:
                continue
            if len(content) > 220:
                content = content[:220] + "..."
            lines.append(f"- ({role}) {content}")

        return "\n".join(lines)

    def chat(self, user_input, stream=False):
        extracted_name = self._extract_user_name(user_input)
        if extracted_name:
            self.profile_store.set_name(extracted_name)

        remembered_name = self.profile_store.get_name()
        if self._is_identity_question(user_input) and remembered_name:
            response = f"You are {remembered_name}."
            self.history.append({'role': 'user', 'content': user_input})
            self.history.append({'role': 'assistant', 'content': response})
            self.history = self.history[-self.max_history:]
            self.memory_store.save_history(self.history)
            self.archive_store.add_message("user", user_input)
            self.archive_store.add_message("assistant", response)
            return response

        # Step 1: retrieve relevant context from docs and long-term conversation memory
        memory_context = self._build_conversation_memory_context(user_input)

        if "system" in user_input.lower() or len(user_input.split()) <= 4:
            context_chunks = []
        else:
            context_chunks = self.retriever.retrieve(user_input)[:2]

        # Combine retrieved chunks
        context = "\n".join(context_chunks)

        # Step 2: Build augmented input
        context_sections = []
        if memory_context:
            context_sections.append(f"Conversation memory:\n{memory_context}")
        if context:
            context_sections.append(f"Reference context:\n{context}")

        if context_sections:
            augument_input = (
                "\n\n".join(context_sections)
                + "\n\n"
                + f"Question: {user_input}"
            )
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
        messages = [self.system_prompt]
        if remembered_name:
            messages.append({
                "role": "system",
                "content": f"Known user name: {remembered_name}. Use it when relevant."
            })
        messages = messages + \
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
        self.history = self.history[-self.max_history:]
        self.memory_store.save_history(self.history)
        self.archive_store.add_message("user", user_input)
        self.archive_store.add_message("assistant", response)
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

            if not tool_call and loop_idx == 0:
                last_user = messages[-1].get("content", "")
                lower_user = last_user.lower()
                is_latest_news_query = (
                    not lower_user.startswith("tool result:") and
                    any(
                        key in lower_user for key in [
                            "latest news",
                            "current news",
                            "news about",
                            "latest update",
                            "latest updates",
                            "what's happening",
                            "whats happening",
                            "search the web",
                            "web search",
                            "today news",
                            "this week",
                        ]
                    )
                )

                if is_latest_news_query:
                    query = last_user
                    marker = "question:"
                    if marker in lower_user:
                        idx = lower_user.rfind(marker)
                        query = last_user[idx + len(marker):].strip()
                    tool_call = ("search_web", {"query": query, "max_results": 5})

            if tool_call:
                # Step 3: extract tool name and arguments
                tool_name, arguments = tool_call

                # step 4: execute tool
                result = call_tool(tool_name, arguments)
                if isinstance(result, dict):
                    answer = result.get("answer")

                    if answer:
                        return answer

                    # 🔥 HARD fallback (no hallucination)
                    raw = result.get("raw", [])
                    if raw:
                        return raw[0].get("snippet", "I couldn't find a reliable answer.")

                    return "I couldn't find a reliable answer for that."
                # ADD THIS BLOCK HERE
                if isinstance(result, dict) and "answer" in result and result["answer"]:
                    return result["answer"]

                # existing error handling
                if isinstance(result, dict) and result.get("error"):
                    return f"I could not complete '{tool_name}': {result['error']}"
                if isinstance(result, str) and result.lower().startswith("error"):
                    return result

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
        self.memory_store.clear()
        self.profile_store.clear()
        self.archive_store.clear()


if __name__ == "__main__":
    from core.llm_client import LLMClient
    brain = Brain(LLMClient())
