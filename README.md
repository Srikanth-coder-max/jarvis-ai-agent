# jarvis-ai-agent

Local AI assistant built with Ollama, featuring RAG, tool execution, memory, and real-time system plus web data integration.

## Installation

This project can be run on Windows, macOS, or Linux as long as you have Python and Ollama installed.

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

### 4. Install and start Ollama

Install Ollama from https://ollama.com and make sure the Ollama service is running.

Pull the models used by the project:

```bash
ollama pull mistral:7b-instruct-q4_K_M
ollama pull nomic-embed-text
```

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

## Project Overview

- `main.py` starts the assistant.
- `core/` contains the LLM client, conversation brain, and memory layer.
- `rag/` handles document ingestion and retrieval.
- `tools/` contains system and web tools.
- `voice/` contains speech-to-text and text-to-speech support.

## Troubleshooting

- If the assistant cannot connect to Ollama, check that the Ollama service is running locally on port `11434`.
- If audio recording fails, verify that your microphone is available to the operating system.
- If embeddings or responses fail, confirm that the required models are installed in Ollama.
