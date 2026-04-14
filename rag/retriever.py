from typing import Any, cast

import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_PATH, EMBED_MODEL, TOP_K_RESULTS


class Retriever:
    def __init__(self):
        # Connecting to presistent DB
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        # Use same collection name as ingester
        self.collection = self.client.get_or_create_collection(
            name="documents",
            embedding_function=cast(Any, self.embedding_function),
        )

    def retrieve(self, query, top_k=TOP_K_RESULTS):
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        # Extract text chunks
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
