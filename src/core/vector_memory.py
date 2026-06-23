"""长期记忆 —— 基于向量数据库的语义记忆"""

import os
import chromadb
from chromadb.config import Settings


class VectorMemory:
    """基于 ChromaDB + SentenceTransformer 的长期语义记忆

    使用 all-MiniLM-L6-v2 模型（384 维）进行文本向量化，
    支持语义检索（recall）、存储（remember）和删除（forget）。
    数据持久化在 data/chroma/ 目录。
    """

    def __init__(self, persist_dir: str = None):
        """初始化 ChromaDB 持久化客户端

        Args:
            persist_dir: 数据存储目录，默认 data/chroma/
        """
        # 默认存储目录：项目根目录下的 data/chroma
        persist_dir = persist_dir or os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")
        os.makedirs(persist_dir, exist_ok=True)  # 确保目录存在

        self.client = chromadb.PersistentClient(
            path=persist_dir, settings=Settings(anonymized_telemetry=False),  # 关闭匿名遥测
        )
        self.collection = self.client.get_or_create_collection(name="agent_memory")  # 获取或创建集合
        self._embedder = None  # 延迟加载嵌入模型

    def _get_embedder(self):
        """延迟加载 SentenceTransformer 嵌入模型（首次使用时加载）"""
        if self._embedder is None:
            if "HF_ENDPOINT" not in os.environ:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 国内镜像
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")  # 384 维轻量模型
        return self._embedder

    def remember(self, key: str, content: str):
        """存储一条长期记忆

        Args:
            key: 记忆唯一标识
            content: 记忆内容文本
        """
        embedder = self._get_embedder()
        embedding = embedder.encode(content).tolist()  # 文本 → 向量
        self.collection.add(
            documents=[content], metadatas=[{"key": key}],
            ids=[key], embeddings=[embedding],
        )

    def recall(self, query: str, n_results: int = 3) -> list[dict]:
        """语义检索相关记忆

        Args:
            query: 查询文本
            n_results: 返回结果数，默认 3
        Returns:
            含 key/content/distance 的字典列表，按相关度排序
        """
        embedder = self._get_embedder()
        query_embedding = embedder.encode(query).tolist()  # 查询文本 → 向量
        results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
        if not results.get("documents") or not results["documents"][0]:
            return []
        return [
            {
                "key": results["metadatas"][0][i].get("key", ""),  # 记忆标识
                "content": doc,  # 记忆内容
                "distance": results["distances"][0][i],  # 向量距离（越小越相关）
            }
            for i, doc in enumerate(results["documents"][0])
        ]

    def forget(self, key: str):
        """删除一条记忆"""
        self.collection.delete(ids=[key])
