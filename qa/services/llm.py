"""LLM JSON 调用工具：统一封装大模型调用 + 鲁棒的 JSON 解析。"""
import json
import re

from AI.openai_service import OpenAIService

DEFAULT_SYSTEM = "你是一名严谨的资深测试工程师，擅长测试设计。只输出 JSON，不要输出任何其他内容。"


def call_llm_json(prompt: str, system: str = DEFAULT_SYSTEM):
    """调用大模型并解析 JSON 返回（支持数组 / 对象）"""
    raw = OpenAIService().chat(prompt, temperature=0.2, system=system)
    return parse_json(raw)


def parse_json(raw: str):
    """从大模型输出中鲁棒提取 JSON：剥离 markdown 代码块，裁剪前后杂质"""
    text = raw.strip()
    fence = re.match(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fence:
        text = fence.group(1).strip()

    # 定位第一个数组/对象起始位置
    starts = [i for i in (text.find("["), text.find("{")) if i != -1]
    if not starts:
        raise ValueError(f"未找到 JSON 内容: {raw[:200]}")
    start = min(starts)
    return json.loads(text[start:])
