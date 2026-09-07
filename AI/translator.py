from django.core.cache import cache
from .openai_service import OpenAIService

class Translator:
    def __init__(self):
        self.llm = OpenAIService()

    def translate(self, text, target_language):
        key = f"translate:{text}:{target_language}"
        cached = cache.get(key)
        if cached:
            return cached

        prompt = f"""
请将下面内容翻译成{target_language}。
要求：保持旅游信息准确。
文本：
{text}
        """
        result = self.llm.chat(prompt)
        cache.set(key, result, timeout=3600)
        return result
