import os

from dotenv import load_dotenv


load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
STT_PROVIDER = os.getenv("STT_PROVIDER", "local").strip().lower()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-q4_K_M")

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en").strip().lower()
STT_LOCAL_MODEL = os.getenv("STT_LOCAL_MODEL", "small").strip()
STT_LOCAL_COMPUTE_TYPE = os.getenv("STT_LOCAL_COMPUTE_TYPE", "int8").strip().lower()
STT_BEAM_SIZE = int(os.getenv("STT_BEAM_SIZE", "5"))
STT_INITIAL_PROMPT = os.getenv(
	"STT_INITIAL_PROMPT",
	"Indian English. Common places: Ranipet, Vellore, Chennai, Bengaluru.",
).strip()

EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")  # Used for RAG which converts text into vectors
if EMBED_MODEL == "nomic-embed-text":
	EMBED_MODEL = "all-MiniLM-L6-v2"
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")  # Path to the Chroma vector database
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))  # Number of top results to return in RAG
CHAT_MEMORY_PATH = os.getenv("CHAT_MEMORY_PATH", "./memory/chat_history.json")
MAX_CHAT_HISTORY = int(os.getenv("MAX_CHAT_HISTORY", "10"))
USER_PROFILE_PATH = os.getenv("USER_PROFILE_PATH", "./memory/user_profile.json")
CONVERSATION_MEMORY_COLLECTION = os.getenv("CONVERSATION_MEMORY_COLLECTION", "conversation_memory")
CONVERSATION_MEMORY_RECALL_K = int(os.getenv("CONVERSATION_MEMORY_RECALL_K", "4"))
WEATHER_DEFAULT_CITY = os.getenv("WEATHER_DEFAULT_CITY", "Ranipet, Tamil Nadu, India").strip()