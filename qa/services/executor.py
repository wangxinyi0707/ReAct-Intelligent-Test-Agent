"""测试执行引擎：将接口用例渲染为 pytest 源码，子进程执行并解析结果入库。

设计要点：
1. 接口用例 → 生成独立 pytest 文件（使用测试专用配置 SQLite，不污染生产库）
2. 子进程调用 pytest + junitxml，解析 JUnit XML 得到逐条结果
3. 失败用例自动触发 AI 失败分析
4. 全程记录执行统计（总数/通过/失败/跳过/耗时）
"""
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from django.utils import timezone

from qa.models import TestCase, TestCaseResult, TestExecution
from qa.services.failure_analyzer import analyze_failure

BASE_DIR = Path(__file__).resolve().parent.parent.parent

PYTEST_TEMPLATE = """# -*- coding: utf-8 -*-
\"\"\"由 TripGenius AI 测试中心自动生成的接口测试用例（请勿手改）\"\"\"
import json

import pytest
from django.test import Client

CASES = __CASES_JSON__

pytestmark = pytest.mark.django_db


@pytest.fixture
@pytest.mark.django_db
def qa_user():
    from django.contrib.auth.models import User
    return User.objects.create_user(username="qa_runner", password="qa_pass_123")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_api_case(case, qa_user):
    client = Client()
    if case.get("auth"):
        assert client.login(username="qa_runner", password="qa_pass_123"), "测试用户登录失败"
    path = case["path"]
    method = case["method"].upper()
    params = case.get("params") or {}
    kwargs = {}
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        kwargs["data"] = json.dumps(params)
        kwargs["content_type"] = "application/json"
    else:
        kwargs["data"] = params
    resp = getattr(client, method.lower())(path, **kwargs)
    expected_status = case.get("expected_status")
    if expected_status is not None:
        assert resp.status_code == expected_status, (
            f"期望状态码 {expected_status}，实际 {resp.status_code}，响应: {resp.content[:500]}"
        )
    for keyword in case.get("expected_keywords", []):
        assert keyword in resp.content.decode("utf-8", "ignore"), (
            f"响应中未包含关键字: {keyword}"
        )
"""


def _build_payload(cases):
    """把 TestCase 渲染为 pytest 所需的数据结构"""
    payload = []
    for case in cases:
        payload.append(
            {
                "id": case.id,
                "path": case.endpoint,
                "method": case.method,
                "params": case.params or {},
                "expected_status": case.expected_status,
                "expected_keywords": case.expected_keywords or [],
                "auth": case.need_auth,
            }
        )
    return payload


def _run_pytest(source_code: str):
    """将源码写入临时文件并用 pytest 执行，返回 (returncode, junit_xml_path)"""
    fd, src_path = tempfile.mkstemp(suffix="_qa_cases.py", prefix="qa_", dir=BASE_DIR)
    xml_path = src_path.replace(".py", "_results.xml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(source_code)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            src_path,
            "--ds",
            "tripgenius.test_settings",
            "-q",
            "--tb=short",
            "--no-header",
            "-p",
            "no:cacheprovider",
            "--junitxml",
            xml_path,
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        return proc.returncode, xml_path, proc.stdout + "\n" + proc.stderr
    finally:
        if os.path.exists(src_path):
            os.unlink(src_path)


def _parse_junit(xml_path: str):
    """解析 JUnit XML -> {case_id: {"status":..., "duration":..., "message":...}}"""
    result_map = {}
    if not os.path.exists(xml_path):
        return result_map
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return result_map

    for tc in tree.getroot().iter("testcase"):
        name = tc.get("name", "")
        if not name.startswith("test_api_case["):
            continue
        case_id = name[len("test_api_case[") : -1]
        duration = float(tc.get("time", 0) or 0)
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")
        if failure is not None or error is not None:
            node = failure if failure is not None else error
            status = "failed"
            message = (node.get("message", "") + "\n" + (node.text or "")).strip()
        elif skipped is not None:
            status, message = "skipped", (skipped.text or "").strip()
        else:
            status, message = "passed", ""
        result_map[case_id] = {"status": status, "duration": duration, "message": message}
    return result_map


def run_execution(execution_id: int):
    """执行一次测试运行（Celery 任务或同步调用入口）"""
    execution = TestExecution.objects.get(id=execution_id)
    execution.status = TestExecution.Status.RUNNING
    execution.started_at = timezone.now()
    execution.save(update_fields=["status", "started_at"])

    queryset = TestCase.objects.filter(status=TestCase.Status.ACTIVE)
    if execution.suite_id:
        queryset = queryset.filter(suite_id=execution.suite_id)
    cases = list(queryset)

    api_cases = [c for c in cases if c.case_type == TestCase.CaseType.API]
    manual_cases = [c for c in cases if c.case_type == TestCase.CaseType.MANUAL]

    # 手动用例在自动执行中标记为跳过
    for case in manual_cases:
        TestCaseResult.objects.create(
            execution=execution,
            case=case,
            case_title=case.title,
            status=TestCaseResult.Status.SKIPPED,
        )

    start = time.time()
    returncode = None
    summary = ""
    result_map = {}
    if api_cases:
        # 注意：这里用 repr() 而非 json.dumps()，保证嵌入的是合法 Python 字面量
        # （json 的 true/false/null 在 Python 源码中不合法）
        source = PYTEST_TEMPLATE.replace(
            "__CASES_JSON__", repr(_build_payload(api_cases))
        )
        try:
            returncode, xml_path, summary = _run_pytest(source)
            result_map = _parse_junit(xml_path)
        except subprocess.TimeoutExpired:
            summary = "执行超时（>600s）"
            returncode = -1
        finally:
            if os.path.exists(xml_path):
                os.unlink(xml_path)
    execution.summary = (summary or "")[:4000]

    # 记录每条接口用例结果
    failed_results = []
    for case in api_cases:
        info = result_map.get(str(case.id))
        if info is None:
            status, duration, message = TestCaseResult.Status.ERROR, 0, "pytest 未收集到该用例（可能是导入/收集阶段异常）"
        else:
            status, duration, message = info["status"], info["duration"], info["message"]
        result = TestCaseResult.objects.create(
            execution=execution,
            case=case,
            case_title=case.title,
            status=status,
            duration=duration,
            log=message[:3000],
        )
        if status in (TestCaseResult.Status.FAILED, TestCaseResult.Status.ERROR):
            failed_results.append(result)

    # AI 失败分析
    for result in failed_results:
        result.analysis = analyze_failure(result.case_title, result.log)
        result.save(update_fields=["analysis"])

    # 汇总统计
    results = list(execution.results.all())
    execution.total = len(results)
    execution.passed = sum(1 for r in results if r.status == TestCaseResult.Status.PASSED)
    execution.failed = sum(
        1 for r in results if r.status in (TestCaseResult.Status.FAILED, TestCaseResult.Status.ERROR)
    )
    execution.skipped = sum(1 for r in results if r.status == TestCaseResult.Status.SKIPPED)
    execution.duration = round(time.time() - start, 2)
    execution.finished_at = timezone.now()
    if execution.total == 0:
        execution.status = TestExecution.Status.ERROR
        execution.summary = "套件中没有可执行的用例"
    elif execution.failed > 0:
        execution.status = TestExecution.Status.FAILED
    elif returncode == 0:
        execution.status = TestExecution.Status.PASSED
    else:
        execution.status = TestExecution.Status.ERROR
    execution.save()

    return {
        "id": execution.id,
        "status": execution.status,
        "total": execution.total,
        "passed": execution.passed,
        "failed": execution.failed,
        "skipped": execution.skipped,
        "duration": execution.duration,
    }
