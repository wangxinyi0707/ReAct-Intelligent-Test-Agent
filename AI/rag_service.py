from __future__ import annotations
import os
import threading
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .embedding import EmbeddingService
from .openai_service import OpenAIService
from .prompt import build_rag_prompt


class RAGService:
    def __init__(self):
        path = os.getenv("CHROMA_PATH", "rag_data/chroma_db")
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection = self.client.get_or_create_collection(name="travel_knowledge")
        self.embedding = EmbeddingService()
        self.llm = OpenAIService()

    def split_text(self, text):
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        return splitter.split_text(text)

    def add_documents(self, documents):
        """构建知识库"""
        chunks = []
        for doc in documents:
            chunks.extend(self.split_text(doc))

        vectors = self.embedding.embed_documents(chunks)
        ids = [f"doc_{i}" for i in range(len(chunks))]
        self.collection.add(documents=chunks, embeddings=vectors, ids=ids)
        return len(chunks)

    def search(self, question, top_k=3):
        """向量检索"""
        vector = self.embedding.embed_text(question)
        result = self.collection.query(
            query_embeddings=[vector],
            n_results=top_k
        )
        return result["documents"][0]

    def ask(self, question):
        """RAG问答"""
        docs = self.search(question)
        context = "\n".join(docs)
        prompt = build_rag_prompt(question, context)
        return self.llm.chat(prompt)

    def build_vector_store(self):
        """初始化测试知识库"""
        documents = [
            """日本东京旅游：浅草寺、东京塔、银座购物区、秋叶原动漫文化。东京地铁非常方便。""",
            """巴黎旅游：埃菲尔铁塔、卢浮宫、塞纳河。法国美食包括法棍和蜗牛。""",
            """中国杭州旅游：西湖、灵隐寺、龙井茶园。"""
        ]
        return self.add_documents(documents)


# 进程级单例：模型加载是一次性开销，避免每次请求都重新加载 embedding 模型
_rag_service = None
_rag_service_lock = threading.Lock()


def get_rag_service():
    """获取 RAGService 单例（双重检查锁，线程安全）。"""
    global _rag_service
    if _rag_service is None:
        with _rag_service_lock:
            if _rag_service is None:
                _rag_service = RAGService()
    return _rag_service
