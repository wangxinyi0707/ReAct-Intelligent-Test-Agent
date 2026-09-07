import os
import httpx
from openai import OpenAI, DefaultHttpxClient


class OpenAIService:
    """OpenAI 对话服务，彻底屏蔽系统代理，解决proxies参数报错"""
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("OPENAI_MODEL")

        if not self.api_key:
            raise ValueError("未配置环境变量 OPENAI_API_KEY")

        # 强制禁用任何代理传输层
        transport = httpx.HTTPTransport(proxy=None)
        # 传入中转base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,  # 新增这一行，对接中转接口
            http_client=DefaultHttpxClient(transport=transport)
        )

    def chat(self, prompt: str, temperature=0.7, system: str = None) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system or "你是一名专业旅游规划助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content or ""

    def stream_chat(self, prompt: str):
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是智能旅行助手"},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
