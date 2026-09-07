"""AI 测试 Agent：基于 LLM 工具调用（Function Calling）的 ReAct 循环测试执行器。

与「AI 生成用例」「AI 失败分析」的单次调用不同，Agent 具备自主性：
1. 模型自主决定调用哪些工具（scan_apis / execute_request）
2. 观察工具返回结果后继续决策（重试、换参数、下一步）
3. 直到完成测试目标，输出结构化测试报告

执行模型：deepseek-chat（OpenAI 兼容接口，支持 tools/function calling）。
"""
import json
import os

import httpx
import requests
from openai import DefaultHttpxClient, OpenAI

from qa.services import api_scanner

# ---------------- 工具定义 ----------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scan_apis",
            "description": "扫描被测系统，返回全部 API 接口清单（含路径、方法、参数字段）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_request",
            "description": "向被测系统发送一个 HTTP 请求，返回状态码与响应体；auth 控制是否携带登录态",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    },
                    "path": {
                        "type": "string",
                        "description": "接口路径，例如 /api/accounts/login/",
                    },
                    "params": {
                        "type": "object",
                        "description": "请求参数（JSON 对象）",
                    },
                    "auth": {
                        "type": "boolean",
                        "description": "是否携带登录态，默认 true；测试「未登录/无权限」场景请设为 false",
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
]

AGENT_SYSTEM_PROMPT = """你是部署在 TripGenius 智能旅行平台上的 AI 测试 Agent，任务是自主完成接口测试。
规则：
1. 先调用 scan_apis 工具了解被测系统有哪些接口；
2. 用 execute_request 工具发送请求（method/path/params），观察返回的状态码和响应体；
3. 自己判断每个请求是否符合预期，例如：注册成功应 201、未登录访问受保护接口应 401、参数错误应 400；
4. 需要登录的接口：execute_request 的 auth 参数控制是否携带登录态，默认 true；
   测试「未登录/无权限」场景时把 auth 设为 false；
5. 失败时不要立刻放弃，可调整参数重试一次；
6. 测试完成后，最后只输出一个 JSON（不要输出其他任何内容），格式：
{"summary": "总体结论(一句话)", "passed": 通过数, "failed": 失败数,
 "results": [{"test": "测试点描述", "status": "passed|failed", "detail": "实际结果说明"}]}
"""

MAX_STEP_DEFAULT = 15


class AgentHTTPService:
    """Agent 的 HTTP 工具后端：管理 JWT 登录态并执行真实请求"""

    def __init__(self):
        self.base_url = os.getenv("AGENT_BASE_URL", "http://127.0.0.1:8000")
        self.username = os.getenv("AGENT_USERNAME", "demo_admin")
        self.password = os.getenv("AGENT_PASSWORD", "admin12345")
        self.token = None

    def _login(self):
        resp = requests.post(
            f"{self.base_url}/api/accounts/login/",
            json={"username": self.username, "password": self.password},
            timeout=10,
        )
        data = resp.json()
        self.token = data.get("access", "")

    def execute_request(self, method: str, path: str, params: dict = None, auth: bool = True):
        is_login = path.rstrip("/").endswith("/login")
        if auth and self.token is None and not is_login:
            self._login()

        headers = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        method = method.upper()
        kwargs = {"headers": headers, "timeout": 15}
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            kwargs["json"] = params or {}
        else:
            kwargs["params"] = params or {}
        try:
            resp = requests.request(method, self.base_url + path, **kwargs)
            return {"status_code": resp.status_code, "body": self._parse_body(resp)}
        except requests.RequestException as exc:
            return {"error": str(exc)}

    @staticmethod
    def _parse_body(resp):
        try:
            return resp.json()
        except ValueError:
            return resp.text[:1000]


class TestAgent:
    """ReAct 循环主体：思考 -> 调用工具 -> 观察结果 -> 再思考"""

    def __init__(self, http_service: AgentHTTPService = None):
        self.http = http_service or AgentHTTPService()
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            http_client=DefaultHttpxClient(transport=httpx.HTTPTransport(proxy=None)),
        )
        self.model = os.getenv("OPENAI_MODEL", "deepseek-chat")

    def run(self, goal: str, max_steps: int = MAX_STEP_DEFAULT) -> dict:
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": goal},
        ]
        steps = []

        for _ in range(max_steps):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                temperature=0.2,
            )
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                # 模型给出最终答案，解析为结构化报告
                return self._finish(steps, msg.content or "")

            assistant_msg = msg.model_dump()
            if assistant_msg.get("content") is None:
                assistant_msg["content"] = ""
            messages.append(assistant_msg)

            for call in tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self._dispatch(call.function.name, args)
                steps.append(
                    {"tool": call.function.name, "arguments": args, "result": result}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False)[:3000],
                    }
                )

        return {
            "status": "max_steps_exceeded",
            "steps": steps,
            "summary": "超过最大执行步数，任务未完成",
            "results": [],
            "passed": 0,
            "failed": 0,
        }

    def _dispatch(self, name: str, args: dict):
        """执行模型请求的工具"""
        if name == "scan_apis":
            return {"apis": api_scanner.discover_apis()}
        if name == "execute_request":
            return self.http.execute_request(
                args.get("method", "GET"),
                args.get("path", ""),
                args.get("params") or {},
                args.get("auth", True),
            )
        return {"error": f"未知工具: {name}"}

    def _finish(self, steps: list, final_content: str) -> dict:
        from qa.services.llm import parse_json

        try:
            data = parse_json(final_content)
        except Exception:
            data = {}
        results = data.get("results") or []
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = len(results) - passed
        return {
            "status": "failed" if failed else "passed",
            "steps": steps,
            "summary": data.get("summary", final_content[:200]),
            "results": results,
            "passed": passed,
            "failed": failed,
        }


def run_agent_execution(execution_id: int, goal: str):
    """执行一次 Agent 测试并落库：结果写入 TestCaseResult，统计写入 TestExecution"""
    import time as _time

    from django.utils import timezone

    from qa.models import TestCaseResult, TestExecution

    execution = TestExecution.objects.get(id=execution_id)
    execution.status = TestExecution.Status.RUNNING
    execution.started_at = timezone.now()
    execution.save(update_fields=["status", "started_at"])

    start = _time.time()
    try:
        report = TestAgent().run(goal)
    except Exception as exc:
        report = {
            "status": "error",
            "summary": f"Agent 执行异常: {exc}",
            "results": [],
            "passed": 0,
            "failed": 0,
        }

    valid_statuses = {s.value for s in TestCaseResult.Status}
    for item in report.get("results") or []:
        status = item.get("status")
        if status not in valid_statuses:
            status = TestCaseResult.Status.ERROR
        TestCaseResult.objects.create(
            execution=execution,
            case=None,
            case_title=(item.get("test") or "")[:300],
            status=status,
            duration=0,
            log=(item.get("detail") or "")[:3000],
        )

    results = list(execution.results.all())
    execution.total = len(results)
    execution.passed = sum(
        1 for r in results if r.status == TestCaseResult.Status.PASSED
    )
    execution.failed = sum(
        1 for r in results if r.status == TestCaseResult.Status.FAILED
    )
    execution.skipped = sum(
        1 for r in results if r.status == TestCaseResult.Status.SKIPPED
    )
    execution.duration = round(_time.time() - start, 2)
    execution.summary = (report.get("summary") or "")[:4000]
    execution.finished_at = timezone.now()
    if execution.total == 0:
        execution.status = TestExecution.Status.ERROR
    elif execution.failed > 0:
        execution.status = TestExecution.Status.FAILED
    else:
        execution.status = TestExecution.Status.PASSED
    execution.save()
    return execution
