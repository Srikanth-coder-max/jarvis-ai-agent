# jarvis-ai-agent

Local AI assistant built with Groq for chat and voice, plus local sentence-transformer embeddings for RAG.

## Installation

This project can be run on Windows, macOS, or Linux as long as you have Python installed.

### 1. Clone the repository

```bash
git clone <repository-url>
cd jarvis-ai-agent
```

Replace `<repository-url>` with the URL of your fork or the original repository.

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If your clone includes `requirement.txt`, use that file instead.

### 4. Configure Groq and local embeddings

Set a Groq API key for chat and voice.

For Groq, create a `.env` file in the project root with:

```env
LLM_PROVIDER=groq
STT_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_STT_MODEL=whisper-large-v3-turbo
EMBED_MODEL=all-MiniLM-L6-v2
CHAT_MEMORY_PATH=./memory/chat_history.json
MAX_CHAT_HISTORY=10
USER_PROFILE_PATH=./memory/user_profile.json
CONVERSATION_MEMORY_COLLECTION=conversation_memory
CONVERSATION_MEMORY_RECALL_K=4
```

If you only want Groq for speech recognition, set `STT_PROVIDER=groq` and keep `LLM_PROVIDER=ollama`.

RAG now uses a local sentence-transformer model, so Ollama is no longer required for embeddings.

If you already have an old `chroma_db` created with Ollama embeddings, delete it and reingest your documents so the stored vectors match the new embedding model.

### 5. Run Jarvis

Text mode:

```bash
python main.py
```

Voice mode:

```bash
python main.py --voice
```

## Voice mode requirements

Voice mode uses `faster-whisper`, `sounddevice`, and `pyttsx3`.

- On Windows, ensure microphone access is enabled.
- On Linux, you may need `ffmpeg` and system audio packages installed.
- If voice input fails, try text mode first to confirm the core assistant is working.

## Optional: Add your own documents

The project includes a Chroma-based RAG pipeline. You can ingest your own `.pdf` or `.txt` files using the ingester in `rag/`.

## Internet Research Mode

Jarvis supports broad internet research across topics using `research_web`:

- Query expansion for better coverage (including date-aware variants)
- Lightweight page fetch + text extraction from top results
- Evidence ranking using lexical overlap and trusted-domain bonus
- Citation-ready output so responses can reference sources as `[1]`, `[2]`
- Basic safety screening for clearly unsafe requests

For very time-sensitive or specialized topics, consider adding dedicated APIs (for example sports, finance, weather) and keeping web search as fallback.

## Project Overview

- `main.py` starts the assistant.
- `core/` contains the LLM client, conversation brain, and memory layer.
- `rag/` handles document ingestion and retrieval.
- `tools/` contains system and web tools.
- `voice/` contains speech-to-text and text-to-speech support.

## Troubleshooting

- If you use Groq and get an authorization error, verify that `GROQ_API_KEY` is set correctly in `.env`.
- If Groq speech recognition fails, verify that `STT_PROVIDER=groq` and `GROQ_STT_MODEL` are set correctly in `.env`.
- If audio recording fails, verify that your microphone is available to the operating system.
- If embeddings or retrieval fail, delete `chroma_db` and reingest your documents.

## Persistent Conversation Memory

Jarvis now uses hybrid memory:

- Short-term memory: recent turns in `memory/chat_history.json`
- Long-term memory: vectorized conversation archive in Chroma for semantic recall
- Profile memory: stable user attributes in `memory/user_profile.json`

- Recent-turn window is controlled by `MAX_CHAT_HISTORY`
- Number of recalled long-term memories per query is controlled by `CONVERSATION_MEMORY_RECALL_K`
- To clear everything, call `Brain.reset()`
