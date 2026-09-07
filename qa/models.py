from django.contrib.auth.models import User
from django.db import models


class TestSuite(models.Model):
    """测试套件：一组测试用例的集合，对应一次回归范围"""

    name = models.CharField(max_length=200, verbose_name="套件名称")
    description = models.TextField(blank=True, default="", verbose_name="套件描述")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="创建人"
    )
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["-created_time"]
        verbose_name = "测试套件"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class TestCase(models.Model):
    """测试用例：支持手动 / 接口两种类型，接口用例可被执行引擎自动执行"""

    class CaseType(models.TextChoices):
        MANUAL = "manual", "手动用例"
        API = "api", "接口用例"

    class Priority(models.TextChoices):
        P0 = "P0", "P0-阻塞"
        P1 = "P1", "P1-严重"
        P2 = "P2", "P2-一般"
        P3 = "P3", "P3-轻微"

    class Status(models.TextChoices):
        ACTIVE = "active", "启用"
        DISABLED = "disabled", "停用"

    class Source(models.TextChoices):
        MANUAL = "manual", "手工编写"
        AI = "ai", "AI 生成"
        SCAN = "scan", "接口扫描生成"

    suite = models.ForeignKey(
        TestSuite, on_delete=models.CASCADE, related_name="cases", null=True, blank=True,
        verbose_name="所属套件",
    )
    title = models.CharField(max_length=300, verbose_name="用例标题")
    description = models.TextField(blank=True, default="", verbose_name="用例描述/前置条件")
    case_type = models.CharField(max_length=10, choices=CaseType.choices, default=CaseType.MANUAL)
    priority = models.CharField(max_length=2, choices=Priority.choices, default=Priority.P2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    tags = models.JSONField(default=list, blank=True, verbose_name="标签")

    # ---- 接口用例专用字段：请求与预期 ----
    method = models.CharField(max_length=10, blank=True, default="GET", verbose_name="请求方法")
    endpoint = models.CharField(max_length=500, blank=True, default="", verbose_name="接口路径")
    params = models.JSONField(default=dict, blank=True, verbose_name="请求参数")
    expected_status = models.PositiveIntegerField(null=True, blank=True, verbose_name="预期状态码")
    expected_keywords = models.JSONField(default=list, blank=True, verbose_name="预期响应关键字")
    need_auth = models.BooleanField(default=True, verbose_name="执行前需登录")

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="创建人"
    )
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["-priority", "-created_time"]
        verbose_name = "测试用例"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class TestExecution(models.Model):
    """一次测试执行记录：记录套件的执行结果与统计"""

    class Status(models.TextChoices):
        PENDING = "pending", "待执行"
        RUNNING = "running", "执行中"
        PASSED = "passed", "全部通过"
        FAILED = "failed", "存在失败"
        ERROR = "error", "执行异常"

    name = models.CharField(max_length=200, verbose_name="执行名称")
    suite = models.ForeignKey(
        TestSuite, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="关联套件"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    total = models.IntegerField(default=0, verbose_name="用例总数")
    passed = models.IntegerField(default=0, verbose_name="通过数")
    failed = models.IntegerField(default=0, verbose_name="失败数")
    skipped = models.IntegerField(default=0, verbose_name="跳过数")
    duration = models.FloatField(default=0, verbose_name="耗时(秒)")
    summary = models.TextField(blank=True, default="", verbose_name="执行摘要")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="执行人"
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        ordering = ["-created_time"]
        verbose_name = "测试执行"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class TestCaseResult(models.Model):
    """单条用例的执行结果"""

    class Status(models.TextChoices):
        PASSED = "passed", "通过"
        FAILED = "failed", "失败"
        SKIPPED = "skipped", "跳过"
        ERROR = "error", "异常"

    execution = models.ForeignKey(
        TestExecution, on_delete=models.CASCADE, related_name="results", verbose_name="所属执行"
    )
    case = models.ForeignKey(
        TestCase, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="用例"
    )
    case_title = models.CharField(max_length=300, verbose_name="用例标题")
    status = models.CharField(max_length=10, choices=Status.choices)
    duration = models.FloatField(default=0, verbose_name="耗时(秒)")
    log = models.TextField(blank=True, default="", verbose_name="执行日志/失败信息")
    analysis = models.TextField(blank=True, default="", verbose_name="AI 失败分析")

    class Meta:
        verbose_name = "用例执行结果"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.case_title} - {self.status}"
