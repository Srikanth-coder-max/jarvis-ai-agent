OLLAMA_BASE_URL = "http://localhost:11434" 
OLLAMA_MODEL = "mistral:7b-instruct-q4_K_M"
EMBED_MODEL = "nomic-embed-text" # Used for RAG which converts text into vectors
CHROMA_PATH = "./chroma_db" # Path to the Chroma vector database
TOP_K_RESULTS = 5 # Number of top results to return in RAG