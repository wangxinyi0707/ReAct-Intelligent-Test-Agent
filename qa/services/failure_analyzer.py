"""AI 失败分析：把失败用例的日志交给大模型，自动定位根因并给出修复建议。"""
import json

from qa.services.llm import call_llm_json

SYSTEM_PROMPT = (
    "你是一名资深测试开发工程师，擅长从失败日志中定位缺陷根因。"
    "只输出 JSON，不要输出任何其他内容。"
)


def analyze_failure(case_title: str, log: str) -> str:
    """输入用例标题与失败日志，返回结构化的 AI 分析结果"""
    prompt = f"""以下是一条失败的接口测试用例，请分析失败原因并给出修复建议。

用例标题：{case_title}

失败日志：
{log[:2000]}

请输出 JSON，字段如下：
- root_cause: 失败根因(一句话)
- suggestion: 修复建议/排查方向
- severity: "high"/"medium"/"low"
"""
    try:
        data = call_llm_json(prompt, system=SYSTEM_PROMPT)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:  # 大模型调用失败时降级为原始日志，不影响执行流程
        return f"AI 分析暂不可用：{exc}"
