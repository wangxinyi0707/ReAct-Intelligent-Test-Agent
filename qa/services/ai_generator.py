"""AI 测试用例生成服务：基于需求描述 / 接口定义，调用大模型生成结构化测试用例。"""
import json

from qa.models import TestCase
from qa.services.llm import call_llm_json

SYSTEM_PROMPT = (
    "你是一名严谨的资深测试工程师，擅长接口测试与测试用例设计。"
    "只输出 JSON，不要输出任何其他内容。"
)

CASE_SCHEMA_HINT = (
    "输出 JSON 数组，每个元素为一条用例，字段如下：\n"
    "- title: 用例标题(必填)\n"
    "- description: 用例描述/前置条件\n"
    "- case_type: \"api\" 或 \"manual\"\n"
    "- priority: \"P0\"/\"P1\"/\"P2\"/\"P3\"\n"
    "- method: HTTP 方法(GET/POST/PUT/DELETE)\n"
    "- endpoint: 接口路径\n"
    "- params: 请求参数对象(JSON)\n"
    "- expected_status: 预期 HTTP 状态码(数字)\n"
    "- expected_keywords: 预期响应中应包含的关键字数组\n"
    "- tags: 标签数组\n"
)


def generate_from_requirement(requirement: str, count: int = 5):
    """根据需求描述生成测试用例（返回 LLM 原始结构化数据列表）"""
    prompt = (
        f"请根据以下需求设计 {count} 条测试用例，尽量覆盖正常路径、边界值、异常输入、"
        f"权限与安全等场景，接口相关用例请给出具体的 method / endpoint / params。\n\n"
        f"需求描述：\n{requirement}\n\n{CASE_SCHEMA_HINT}"
    )
    return call_llm_json(prompt, system=SYSTEM_PROMPT)


def generate_from_api(api: dict, count: int = 3):
    """根据单个接口定义生成测试用例（覆盖正常/异常/鉴权场景）"""
    prompt = (
        f"请根据以下接口定义生成 {count} 条接口测试用例，至少覆盖：正常路径、异常参数、"
        f"未授权访问等场景。\n\n接口定义：\n{json.dumps(api, ensure_ascii=False)}\n\n"
        f"{CASE_SCHEMA_HINT}"
    )
    return call_llm_json(prompt, system=SYSTEM_PROMPT)


def save_cases(cases_data, user, suite=None, source=TestCase.Source.AI):
    """将 LLM 生成的结构化用例落库，返回创建的 TestCase 列表"""
    created = []
    for item in cases_data or []:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        case = TestCase.objects.create(
            suite_id=suite,
            title=title,
            description=item.get("description", ""),
            case_type=item.get("case_type", "manual"),
            priority=item.get("priority", "P2"),
            source=source,
            tags=item.get("tags", []) or [],
            method=item.get("method", "GET"),
            endpoint=item.get("endpoint", "") or "",
            params=item.get("params", {}) or {},
            expected_status=item.get("expected_status"),
            expected_keywords=item.get("expected_keywords", []) or [],
            created_by=user,
        )
        created.append(case)
    return created
