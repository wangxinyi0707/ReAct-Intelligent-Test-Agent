"""初始化 AI 测试中心演示套件：一键生成核心流程接口测试用例。

用法：
    python manage.py seed_qa
"""
from django.core.management.base import BaseCommand

from qa.models import TestCase, TestSuite

DEMO_CASES = [
    {
        "title": "注册新用户成功",
        "description": "正常注册流程，校验返回成功",
        "priority": "P0",
        "method": "POST",
        "endpoint": "/api/accounts/register/",
        "params": {
            "username": "seed_user",
            "password": "seed_pass_123",
            "email": "seed@example.com",
        },
        "expected_status": 201,
        "expected_keywords": ["注册成功"],
        "need_auth": False,
    },
    {
        "title": "注册缺少密码返回 400",
        "description": "异常输入：未提供密码时接口应拒绝",
        "priority": "P1",
        "method": "POST",
        "endpoint": "/api/accounts/register/",
        "params": {"username": "seed_user_no_pwd", "email": "a@b.com"},
        "expected_status": 400,
        "expected_keywords": ["password"],
        "need_auth": False,
    },
    {
        "title": "登录成功返回 access token",
        "description": "正确账号密码登录，JWT 返回 access 与 refresh",
        "priority": "P0",
        "method": "POST",
        "endpoint": "/api/accounts/login/",
        "params": {"username": "qa_runner", "password": "qa_pass_123"},
        "expected_status": 200,
        "expected_keywords": ["access", "refresh"],
        "need_auth": False,
    },
    {
        "title": "未登录访问计划列表返回 401",
        "description": "鉴权场景：无凭证访问受保护接口应被拒绝",
        "priority": "P1",
        "method": "GET",
        "endpoint": "/api/travel/list/",
        "params": {},
        "expected_status": 401,
        "expected_keywords": ["身份认证"],
        "need_auth": False,
    },
    {
        "title": "创建旅行计划成功",
        "description": "登录后创建一条旅行计划，校验返回计划数据",
        "priority": "P0",
        "method": "POST",
        "endpoint": "/api/travel/create/",
        "params": {
            "title": "东京五日游",
            "destination": "东京",
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
            "budget": 8000,
            "description": "AI 测试中心生成",
        },
        "expected_status": 201,
        "expected_keywords": ["id", "title"],
        "need_auth": True,
    },
    {
        "title": "查询我的旅行计划列表",
        "description": "登录后查询计划列表，返回 plans 字段",
        "priority": "P2",
        "method": "GET",
        "endpoint": "/api/travel/list/",
        "params": {},
        "expected_status": 200,
        "expected_keywords": ["plans"],
        "need_auth": True,
    },
]


class Command(BaseCommand):
    help = "初始化 AI 测试中心演示数据（套件 + 核心流程接口用例）"

    def handle(self, *args, **options):
        suite, _ = TestSuite.objects.get_or_create(
            name="核心业务流程回归",
            defaults={"description": "覆盖注册 / 登录 / 鉴权 / 旅行计划核心流程的接口用例（自动生成）"},
        )
        created = 0
        for item in DEMO_CASES:
            _, is_new = TestCase.objects.update_or_create(
                suite=suite,
                title=item["title"],
                defaults={**item, "case_type": TestCase.CaseType.API, "source": TestCase.Source.SCAN},
            )
            created += int(is_new)
        self.stdout.write(
            self.style.SUCCESS(f"完成：套件「{suite.name}」共 {suite.cases.count()} 条用例，本次新建 {created} 条")
        )
