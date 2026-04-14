import os
from typing import Any, cast

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader
from config import CHROMA_PATH, EMBED_MODEL


class Ingester:
    def __init__(self):
        # Initialize persistent chromaDB client(stored on disk)
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        self.collection = self.client.get_or_create_collection(
            name="documents",
            embedding_function=cast(Any, self.embedding_function),
        )  # Get or create a collection (like a table in DB)

    def load_document(self, file_path):
        # check file type
        if file_path.endswith(".pdf"):
            reader = PdfReader(file_path)
            text = ""

            # Extract text page by page (PDF structure)
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif file_path.endswith('.txt'):
            with open(file_path, "r", encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError("Unsupported file type. Use PDF or TXT.")

    def chunk_text(self, text, chunk_size=500, overlap_sentence=2):

        sentences = text.split(". ")
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()+"."

            if current_length + len(sentence) > chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = current_chunk[-overlap_sentence:]
                current_length = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_length += len(sentence)
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    def store(self, chunks, doc_name):
        try:
            self.collection.delete(
                where={"source": doc_name}
            )
        except Exception:
            pass
        ids = []  # Each entry must be have unique id
        metadatas = []

        for i, chunk in enumerate(chunks):
            # creating unique ID per chunk
            chunk_id = f"{doc_name}_{i}"

            ids.append(chunk_id)
            metadatas.append({'source': doc_name})

        # Store in chromaDB
        self.collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )

    def ingest(self, file_path):

        # Extract document name (used for IDS)
        doc_name = os.path.basename(file_path)

        # Step 1: load raw text
        text = self.load_document(file_path)
        # Step 2: Chunk text
        chunks = self.chunk_text(text)
        # Step 3: Store in DB
        self.store(chunks, doc_name)

        print(f"Ingested {len(chunks)} chunks from {doc_name}")


if __name__ == "__main__":
    ingester = Ingester()

