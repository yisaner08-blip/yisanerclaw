"""长期记忆 —— 基于向量数据库的语义记忆"""

import os
import chromadb
from chromadb.config import Settings


class VectorMemory:
    def __init__(self, persist_dir: str = None):
        if persist_dir is None:
            persist_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "chroma"
            )
        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="agent_memory"
        )
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            import os
            # 国内网络优先使用镜像
            if "HF_ENDPOINT" not in os.environ:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder

    def remember(self, key: str, content: str):
        """存储一条记忆"""
        embedder = self._get_embedder()
        embedding = embedder.encode(content).tolist()
        self.collection.add(
            documents=[content],
            metadatas=[{"key": key}],
            ids=[key],
            embeddings=[embedding],
        )

    def recall(self, query: str, n_results: int = 3) -> list[dict]:
        """根据语义查询检索相关记忆"""
        embedder = self._get_embedder()
        query_embedding = embedder.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )
        memories = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 0
                memories.append({
                    "key": meta.get("key", ""),
                    "content": doc,
                    "distance": dist,
                })
        return memories

    def forget(self, key: str):
        """删除一条记忆"""
        self.collection.delete(ids=[key])
