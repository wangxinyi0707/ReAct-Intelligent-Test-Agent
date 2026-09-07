# import os
# import httpx
# from openai import OpenAI, DefaultHttpxClient
#
# class EmbeddingService:
#     def __init__(self):
#         self.api_key = os.getenv("OPENAI_API_KEY")
#         self.base_url = os.getenv("OPENAI_BASE_URL")
#         self.embed_model = os.getenv("OPENAI_EMBEDDING_MODEL")
#
#         if not self.api_key:
#             raise ValueError("未配置环境变量 OPENAI_API_KEY")
#
#         # 和 OpenAIService 保持一致，强制禁用代理
#         transport = httpx.HTTPTransport(proxy=None)
#         self.client = OpenAI(
#             api_key=self.api_key,
#             base_url=self.base_url,
#             http_client=DefaultHttpxClient(transport=transport)
#         )
#
#     def embed_text(self, text: str):
#         res = self.client.embeddings.create(input=text, model=self.embed_model)
#         return res.data[0].embedding
#
#     def embed_documents(self, texts: list):
#         res = self.client.embeddings.create(input=texts, model=self.embed_model)
#         return [item.embedding for item in res.data]
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    文本嵌入服务类，基于 SentenceTransformer 实现单文本和批量文本的 Embedding 生成
    选用模型：BAAI/bge-small-zh-v1.5（轻量版中文文本嵌入模型，兼顾效果与效率）
    """

    def __init__(self):
        """初始化方法，加载 Embedding 模型"""
        print("正在加载 Embedding 模型...")
        # 加载预训练的中文嵌入模型
        self.model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        print("Embedding 模型加载完成")

    def embed_text(self, text):
        """
        单文本 Embedding 生成方法
        :param text: 待嵌入的单个文本字符串
        :return: 文本对应的嵌入向量（列表格式）
        """
        # 对单个文本进行编码，生成嵌入向量
        vector = self.model.encode(text)
        # 将 numpy 数组转换为列表返回，便于后续存储和传输
        return vector.tolist()

    def embed_documents(self, documents):
        """
        批量文本 Embedding 生成方法
        :param documents: 待嵌入的文本列表，每个元素为一个文本字符串
        :return: 批量文本对应的嵌入向量列表，每个元素为对应文本的嵌入向量（列表格式）
        """
        # 对批量文本进行编码，生成批量嵌入向量
        vectors = self.model.encode(documents)
        # 将每个 numpy 数组向量转换为列表，组成新列表返回
        return [vector.tolist() for vector in vectors]