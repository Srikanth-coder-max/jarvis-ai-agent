import requests
import chromadb
from config import CHROMA_PATH, EMBED_MODEL, TOP_K_RESULTS


class Retriever:
    def __init__(self):
        # Connecting to presistent DB
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        # Use same collection name as ingester
        self.collection = self.client.get_or_create_collection(
            name="documents")
        # Embedding model
        self.embed_model = EMBED_MODEL
        # ollama embedding endpoint
        self.embed_url = "http://localhost:11434/api/embed"

    def embed_query(self, query):
        response = requests.post(
            self.embed_url,
            json={
                'model': self.embed_model,
                'input': query
            }
        )
        response.raise_for_status()
        data = response.json()

        return data.get('embeddings', [])[0]

    def retrieve(self, query, top_k=TOP_K_RESULTS):
        # Step 1: Embed query
        query_embedding = self.embed_query(query)
        # Step 2: search DB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        # Step 3: Extract text chunks
        documents = results.get("documents", [])
        # documents is nested: [[chunk1, chunk2, ......]]
        if documents:
            return documents[0]
        return []


# if __name__ == "__main__":
#     retriever = Retriever()
#     chunks = retriever.retrieve("What is traction control system?")
#     for i, chunk in enumerate(chunks):
#         print(i+1, chunk[:200])
#         print()
