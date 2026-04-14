import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, cast

import chromadb
from chromadb.utils import embedding_functions


class ConversationMemory:
	def __init__(self, file_path: str, max_history: int = 10):
		self.file_path = file_path
		self.max_history = max_history

	def _ensure_parent_dir(self) -> None:
		parent = os.path.dirname(self.file_path)
		if parent:
			os.makedirs(parent, exist_ok=True)

	def load_history(self) -> List[Dict[str, str]]:
		if not os.path.exists(self.file_path):
			return []

		try:
			with open(self.file_path, "r", encoding="utf-8") as f:
				data = json.load(f)

			if not isinstance(data, list):
				return []

			cleaned: List[Dict[str, str]] = []
			for item in data:
				if not isinstance(item, dict):
					continue
				role = item.get("role")
				content = item.get("content")
				if role in {"user", "assistant"} and isinstance(content, str):
					cleaned.append({"role": role, "content": content})

			return cleaned[-self.max_history:]
		except Exception:
			return []

	def save_history(self, history: List[Dict[str, str]]) -> None:
		trimmed = history[-self.max_history:]
		self._ensure_parent_dir()
		with open(self.file_path, "w", encoding="utf-8") as f:
			json.dump(trimmed, f, ensure_ascii=False, indent=2)

	def clear(self) -> None:
		try:
			if os.path.exists(self.file_path):
				os.remove(self.file_path)
		except Exception:
			pass


class UserProfileMemory:
	def __init__(self, file_path: str):
		self.file_path = file_path

	def _ensure_parent_dir(self) -> None:
		parent = os.path.dirname(self.file_path)
		if parent:
			os.makedirs(parent, exist_ok=True)

	def load_profile(self) -> Dict[str, str]:
		if not os.path.exists(self.file_path):
			return {}

		try:
			with open(self.file_path, "r", encoding="utf-8") as f:
				data = json.load(f)
			if isinstance(data, dict):
				return {k: str(v) for k, v in data.items()}
		except Exception:
			pass
		return {}

	def save_profile(self, profile: Dict[str, str]) -> None:
		self._ensure_parent_dir()
		with open(self.file_path, "w", encoding="utf-8") as f:
			json.dump(profile, f, ensure_ascii=False, indent=2)

	def get_name(self) -> str:
		return self.load_profile().get("name", "").strip()

	def set_name(self, name: str) -> None:
		profile = self.load_profile()
		profile["name"] = name.strip()
		self.save_profile(profile)

	def clear(self) -> None:
		try:
			if os.path.exists(self.file_path):
				os.remove(self.file_path)
		except Exception:
			pass


class ConversationArchive:
	def __init__(self, chroma_path: str, embed_model: str, collection_name: str = "conversation_memory"):
		self.chroma_path = chroma_path
		self.embed_model = embed_model
		self.collection_name = collection_name

		self.client = chromadb.PersistentClient(path=self.chroma_path)
		self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
			model_name=self.embed_model
		)
		self.collection = self.client.get_or_create_collection(
			name=self.collection_name,
			embedding_function=cast(Any, self.embedding_function),
		)

	def add_message(self, role: str, content: str) -> None:
		if not content or not content.strip():
			return

		doc_id = str(uuid.uuid4())
		metadata = {
			"role": role,
			"created_at": datetime.now(timezone.utc).isoformat(),
		}

		self.collection.add(
			ids=[doc_id],
			documents=[content.strip()],
			metadatas=[metadata],
		)

	def recall(self, query: str, top_k: int = 4) -> List[Dict[str, str]]:
		if not query or not query.strip():
			return []

		try:
			results = self.collection.query(query_texts=[query], n_results=max(1, top_k))
			docs = results.get("documents", [[]])
			metas = results.get("metadatas", [[]])

			if not docs or not docs[0]:
				return []

			output: List[Dict[str, str]] = []
			for doc, meta in zip(docs[0], metas[0] if metas else []):
				if not isinstance(doc, str):
					continue
				role = "memory"
				created_at = ""
				if isinstance(meta, dict):
					role = str(meta.get("role", "memory"))
					created_at = str(meta.get("created_at", ""))
				output.append({
					"role": role,
					"content": doc,
					"created_at": created_at,
				})
			return output
		except Exception:
			return []

	def clear(self) -> None:
		try:
			self.client.delete_collection(self.collection_name)
		except Exception:
			pass

		self.collection = self.client.get_or_create_collection(
			name=self.collection_name,
			embedding_function=cast(Any, self.embedding_function),
		)
