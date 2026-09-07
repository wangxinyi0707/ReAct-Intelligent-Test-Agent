"""AI 测试中心模块测试：数据模型 / API / AI 生成 / 接口扫描 / 执行引擎。

注意：Django 模型类以别名导入，避免 pytest 将其当作测试类收集。
"""
from unittest.mock import patch

import pytest

from qa.models import TestCase as QaTestCase
from qa.models import TestCaseResult as QaTestCaseResult
from qa.models import TestExecution as QaTestExecution
from qa.services.executor import run_execution
from test.factories import (
    ApiTestCaseFactory,
    TestCaseFactory,
    TestExecutionFactory,
    TestSuiteFactory,
)


def build_junit(case_statuses, path):
    """根据 {case_id: (status, message)} 生成 JUnit XML 文件"""
    lines = ['<?xml version="1.0" encoding="utf-8"?><testsuite>']
    for case_id, (status, message) in case_statuses.items():
        attrs = f'name="test_api_case[{case_id}]" time="0.01"'
        if status == "passed":
            lines.append(f"<testcase {attrs}/>")
        elif status == "skipped":
            lines.append(f'<testcase {attrs}><skipped message="skip"/></testcase>')
        else:
            lines.append(f'<testcase {attrs}><failure message="{message}">{message}</failure></testcase>')
    lines.append("</testsuite>")
    path.write_text("\n".join(lines), encoding="utf-8")


@pytest.mark.django_db
class TestQaModels:
    def test_create_suite_and_cases(self):
        suite = TestSuiteFactory.create(name="回归")
        case = TestCaseFactory.create(suite=suite, title="登录")
        assert suite.cases.count() == 1
        assert str(case) == "登录"

    def test_create_api_case(self):
        case = ApiTestCaseFactory.create(endpoint="/api/travel/list/")
        assert case.case_type == QaTestCase.CaseType.API
        assert case.expected_status == 200


@pytest.mark.django_db
class TestQaCaseApi:
    def test_cases_require_auth(self, anonymous_client):
        assert anonymous_client.get("/api/qa/cases/").status_code == 401

    def test_create_case(self, auth_client):
        resp = auth_client.post(
            "/api/qa/cases/",
            {
                "title": "查询计划列表",
                "case_type": "api",
                "method": "GET",
                "endpoint": "/api/travel/list/",
                "expected_status": 200,
                "expected_keywords": ["plans"],
            },
            format="json",
        )
        assert resp.status_code == 201
        assert QaTestCase.objects.filter(title="查询计划列表").count() == 1

    def test_list_case_filter_by_type(self, auth_client):
        TestCaseFactory.create(case_type="manual")
        ApiTestCaseFactory.create()
        resp = auth_client.get("/api/qa/cases/", {"case_type": "api"})
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["case_type"] == "api"

    def test_toggle_case_status(self, auth_client):
        case = TestCaseFactory.create()
        resp = auth_client.patch(
            f"/api/qa/cases/{case.id}/",
            {"status": "disabled"},
            format="json",
        )
        assert resp.status_code == 200
        case.refresh_from_db()
        assert case.status == "disabled"


@pytest.mark.django_db
class TestQaAiGeneration:
    @patch("qa.services.ai_generator.call_llm_json")
    def test_generate_from_requirement(self, mock_llm, auth_client):
        mock_llm.return_value = [
            {
                "title": "登录成功",
                "description": "正常登录",
                "case_type": "api",
                "priority": "P0",
                "method": "POST",
                "endpoint": "/api/accounts/login/",
                "params": {"username": "u", "password": "p"},
                "expected_status": 200,
                "expected_keywords": ["access"],
                "tags": ["登录"],
            }
        ]
        resp = auth_client.post(
            "/api/qa/cases/generate/",
            {"requirement": "用户登录接口", "count": 1},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["created"] == 1
        case = QaTestCase.objects.get()
        assert case.source == QaTestCase.Source.AI
        assert case.endpoint == "/api/accounts/login/"

    @patch("qa.services.ai_generator.call_llm_json")
    def test_generate_from_api(self, mock_llm, auth_client):
        mock_llm.return_value = [
            {"title": "未登录返回401", "case_type": "api", "method": "GET",
             "endpoint": "/api/travel/list/", "expected_status": 401,
             "expected_keywords": ["authentication"], "priority": "P1"}
        ]
        resp = auth_client.post(
            "/api/qa/cases/generate-from-api/",
            {"api": {"name": "plan-list", "path": "/api/travel/list/", "methods": ["GET"]}},
            format="json",
        )
        assert resp.status_code == 201
        assert QaTestCase.objects.filter(source=QaTestCase.Source.SCAN).count() == 1

    def test_generate_requires_requirement(self, auth_client):
        resp = auth_client.post("/api/qa/cases/generate/", {}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestQaApiScan:
    def test_scan_discovers_apis(self, auth_client):
        resp = auth_client.get("/api/qa/cases/scan/")
        assert resp.status_code == 200
        apis = resp.json()["apis"]
        paths = [a["path"] for a in apis]
        assert "/api/accounts/register/" in paths
        assert "/api/travel/list/" in paths


@pytest.mark.django_db
class TestQaExecution:
    def test_run_execution_stats_and_analysis(self, db, user, tmp_path, monkeypatch):
        suite = TestSuiteFactory.create(name="回归")
        ok_case = ApiTestCaseFactory.create(suite=suite, title="通过用例")
        bad_case = ApiTestCaseFactory.create(
            suite=suite, title="失败用例", endpoint="/api/travel/create/",
            method="POST", expected_status=201, expected_keywords=["id"],
        )
        TestCaseFactory.create(suite=suite, title="手动用例")
        execution = TestExecutionFactory.create(name="第一轮", suite=suite, created_by=user)

        xml_path = tmp_path / "results.xml"
        build_junit(
            {ok_case.id: ("passed", ""), bad_case.id: ("failed", "期望状态码 500")},
            xml_path,
        )
        monkeypatch.setattr(
            "qa.services.executor._run_pytest",
            lambda src: (1, str(xml_path), "fake summary"),
        )
        monkeypatch.setattr(
            "qa.services.executor.analyze_failure",
            lambda title, log: '{"root_cause": "mock", "severity": "high"}',
        )

        result = run_execution(execution.id)

        execution.refresh_from_db()
        assert execution.total == 3
        assert execution.passed == 1
        assert execution.failed == 1
        assert execution.skipped == 1
        assert execution.status == QaTestExecution.Status.FAILED
        assert result["duration"] >= 0

        bad_result = execution.results.get(case=bad_case)
        assert bad_result.status == QaTestCaseResult.Status.FAILED
        assert "mock" in bad_result.analysis

    def test_run_execution_all_passed(self, db, user, tmp_path, monkeypatch):
        suite = TestSuiteFactory.create(name="通过套件")
        case = ApiTestCaseFactory.create(suite=suite)
        execution = TestExecutionFactory.create(name="全通过", suite=suite, created_by=user)

        xml_path = tmp_path / "results.xml"
        build_junit({case.id: ("passed", "")}, xml_path)
        monkeypatch.setattr(
            "qa.services.executor._run_pytest",
            lambda src: (0, str(xml_path), "ok"),
        )
        monkeypatch.setattr("qa.services.executor.analyze_failure", lambda *a: "")

        run_execution(execution.id)
        execution.refresh_from_db()
        assert execution.status == QaTestExecution.Status.PASSED
        assert execution.passed == 1

    def test_run_execution_no_cases(self, db, user):
        execution = TestExecutionFactory.create(name="空套件", suite=None, created_by=user)
        run_execution(execution.id)
        execution.refresh_from_db()
        assert execution.status == QaTestExecution.Status.ERROR
        assert "没有可执行" in execution.summary

    @patch("qa.views.execute_test_run")
    def test_run_action_view(self, mock_task, auth_client, user):
        suite = TestSuiteFactory.create(name="接口回归")
        ApiTestCaseFactory.create_batch(2, suite=suite)
        execution = TestExecutionFactory.create(name="待执行", suite=suite, created_by=user)
        resp = auth_client.post(f"/api/qa/executions/{execution.id}/run/")
        assert resp.status_code == 200
        mock_task.delay.assert_called_once_with(execution.id)

    def test_stats(self, auth_client, user):
        suite = TestSuiteFactory.create(name="回归")
        ApiTestCaseFactory.create_batch(2, suite=suite)
        TestExecutionFactory.create(name="历史执行", suite=suite, created_by=user)
        resp = auth_client.get("/api/qa/executions/stats/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cases"] == 2
        assert data["total_executions"] == 1


@pytest.mark.django_db
class TestQaAgent:
    """AI 测试 Agent：工具分发 / HTTP 后端 / 结果落库 / API 入口"""

    def test_dispatch_scan_apis(self):
        from qa.services.test_agent import TestAgent

        result = TestAgent()._dispatch("scan_apis", {})
        paths = [a["path"] for a in result["apis"]]
        assert "/api/travel/list/" in paths

    def test_dispatch_unknown_tool(self):
        from qa.services.test_agent import TestAgent

        result = TestAgent()._dispatch("no_such_tool", {})
        assert "error" in result

    def test_http_service_login_and_request(self, monkeypatch):
        """Agent HTTP 后端：auth=True 自动登录携带 Bearer；auth=False 不携带（可测未授权场景）"""
        from qa.services.test_agent import AgentHTTPService

        calls = {}

        class FakeLoginResp:
            status_code = 200

            def json(self):
                return {"access": "fake-token", "refresh": "x"}

        class FakeApiResp:
            status_code = 200

            def json(self):
                return {"plans": []}

        def fake_post(url, json=None, timeout=None):
            calls["login_url"] = url
            return FakeLoginResp()

        def fake_request(method, url, **kwargs):
            calls.setdefault("headers_list", []).append(kwargs.get("headers", {}))
            return FakeApiResp()

        monkeypatch.setattr("qa.services.test_agent.requests.post", fake_post)
        monkeypatch.setattr("qa.services.test_agent.requests.request", fake_request)

        svc = AgentHTTPService()
        svc.execute_request("GET", "/api/travel/list/", auth=True)
        assert "/api/accounts/login/" in calls["login_url"]
        assert calls["headers_list"][0]["Authorization"] == "Bearer fake-token"

        # auth=False 时不自动登录、不携带 token
        svc.execute_request("GET", "/api/travel/list/", auth=False)
        assert "Authorization" not in calls["headers_list"][1]

    def test_run_agent_execution_saves_results(self, db, user, monkeypatch):
        from qa.models import TestCaseResult
        from qa.services.test_agent import run_agent_execution

        execution = TestExecutionFactory.create(name="Agent 任务", created_by=user)
        fixed_report = {
            "status": "failed",
            "summary": "注册成功、未登录401符合预期，创建计划缺少参数返回400",
            "results": [
                {"test": "注册新用户返回201", "status": "passed", "detail": "201 注册成功"},
                {"test": "未登录访问计划列表返回401", "status": "passed", "detail": "401"},
                {"test": "创建计划缺少标题返回400", "status": "failed", "detail": "实际返回201"},
            ],
            "passed": 2,
            "failed": 1,
        }
        monkeypatch.setattr(
            "qa.services.test_agent.TestAgent.run", lambda self, goal: fixed_report
        )

        run_agent_execution(execution.id, "验证注册登录流程")

        execution.refresh_from_db()
        assert execution.total == 3
        assert execution.passed == 2
        assert execution.failed == 1
        assert execution.status == QaTestExecution.Status.FAILED
        assert execution.results.filter(status=TestCaseResult.Status.FAILED).count() == 1

    @patch("qa.views.agent_test_run")
    def test_agent_run_view(self, mock_task, auth_client):
        resp = auth_client.post(
            "/api/qa/agent/run/",
            {"goal": "验证注册→登录流程"},
            format="json",
        )
        assert resp.status_code == 201
        execution_id = resp.json()["execution"]["id"]
        assert mock_task.delay.called
        assert mock_task.delay.call_args.args[0] == execution_id

    def test_agent_run_requires_goal(self, auth_client):
        resp = auth_client.post("/api/qa/agent/run/", {}, format="json")
        assert resp.status_code == 400
