from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from qa.models import TestCase, TestExecution, TestSuite
from qa.serializers import (
    TestCaseSerializer,
    TestExecutionSerializer,
    TestSuiteSerializer,
)
from qa.services import ai_generator, api_scanner
from qa.tasks import agent_test_run, execute_test_run


class TestSuiteViewSet(viewsets.ModelViewSet):
    """测试套件管理"""

    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TestCaseViewSet(viewsets.ModelViewSet):
    """测试用例管理 + AI 生成 + 接口扫描"""

    serializer_class = TestCaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = TestCase.objects.all()
        suite = self.request.query_params.get("suite")
        case_type = self.request.query_params.get("case_type")
        priority = self.request.query_params.get("priority")
        if suite:
            queryset = queryset.filter(suite_id=suite)
        if case_type:
            queryset = queryset.filter(case_type=case_type)
        if priority:
            queryset = queryset.filter(priority=priority)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """根据需求描述 AI 生成测试用例"""
        requirement = request.data.get("requirement", "").strip()
        if not requirement:
            return Response({"error": "缺少 requirement"}, status=status.HTTP_400_BAD_REQUEST)
        count = min(int(request.data.get("count", 5)), 20)
        try:
            cases_data = ai_generator.generate_from_requirement(requirement, count)
        except Exception as exc:
            return Response({"error": f"AI 生成失败: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)

        created = ai_generator.save_cases(
            cases_data, user=request.user, suite=request.data.get("suite"),
            source=TestCase.Source.AI,
        )
        return Response(
            {"created": len(created), "cases": TestCaseSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="generate-from-api")
    def generate_from_api(self, request):
        """根据接口定义 AI 生成测试用例"""
        api = request.data.get("api")
        if not api:
            return Response({"error": "缺少 api 定义"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cases_data = ai_generator.generate_from_api(api)
        except Exception as exc:
            return Response({"error": f"AI 生成失败: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)

        created = ai_generator.save_cases(
            cases_data, user=request.user, suite=request.data.get("suite"),
            source=TestCase.Source.SCAN,
        )
        return Response(
            {"created": len(created), "cases": TestCaseSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="scan")
    def scan(self, request):
        """扫描项目全部 API 接口"""
        return Response({"apis": api_scanner.discover_apis()})


class TestExecutionViewSet(viewsets.ModelViewSet):
    """测试执行管理：创建执行、触发运行、查看结果与统计"""

    queryset = TestExecution.objects.all()
    serializer_class = TestExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestExecution.objects.prefetch_related("results").all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        execution = serializer.save(created_by=request.user)
        return Response(
            self.get_serializer(execution).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        """触发一次测试执行：优先投递 Celery 异步执行，broker 不可用时降级为同步"""
        execution = self.get_object()
        if execution.status == TestExecution.Status.RUNNING:
            return Response({"error": "该执行正在进行中"}, status=status.HTTP_400_BAD_REQUEST)

        async_mode = True
        try:
            execute_test_run.delay(execution.id)
        except Exception:
            # broker 不可用（如本地未启动 Redis）时同步执行
            execute_test_run.apply(args=[execution.id])
            async_mode = False

        execution.refresh_from_db()
        return Response(
            {
                "execution": self.get_serializer(execution).data,
                "async_mode": async_mode,
            }
        )

    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        """对失败用例重新执行 AI 失败分析"""
        from qa.services.failure_analyzer import analyze_failure

        execution = self.get_object()
        failed_results = execution.results.filter(
            status__in=["failed", "error"]
        )
        for result in failed_results:
            result.analysis = analyze_failure(result.case_title, result.log)
            result.save(update_fields=["analysis"])
        return Response({"analyzed": failed_results.count()})

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """测试中心看板统计"""
        executions = TestExecution.objects.order_by("-id")[:10]
        latest = executions.first()
        return Response(
            {
                "total_executions": TestExecution.objects.count(),
                "total_cases": TestCase.objects.filter(
                    status=TestCase.Status.ACTIVE
                ).count(),
                "latest": self.get_serializer(latest).data if latest else None,
                "trend": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "pass_rate": round(e.passed / e.total * 100, 2) if e.total else 0,
                        "status": e.status,
                        "finished_at": e.finished_at,
                    }
                    for e in executions
                ],
            }
        )


class AgentTestRunView(APIView):
    """AI 测试 Agent 入口：输入自然语言测试目标，Agent 自主调用工具完成接口测试"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        goal = (request.data.get("goal") or "").strip()
        if not goal:
            return Response({"error": "缺少 goal"}, status=status.HTTP_400_BAD_REQUEST)

        execution = TestExecution.objects.create(
            name=f"AI Agent: {goal[:30]}",
            suite_id=request.data.get("suite") or None,
            created_by=request.user,
        )

        async_mode = True
        try:
            agent_test_run.delay(execution.id, goal)
        except Exception:
            # broker 不可用时同步执行
            agent_test_run.apply(args=[execution.id, goal])
            async_mode = False

        execution.refresh_from_db()
        return Response(
            {
                "execution": TestExecutionSerializer(execution).data,
                "async_mode": async_mode,
            },
            status=status.HTTP_201_CREATED,
        )
