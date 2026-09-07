from django.contrib import admin

from .models import TestCase, TestCaseResult, TestExecution, TestSuite


@admin.register(TestSuite)
class TestSuiteAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "case_count", "created_by", "created_time"]

    @admin.display(description="用例数")
    def case_count(self, obj):
        return obj.cases.count()


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "case_type", "priority", "status", "source", "suite"]
    list_filter = ["case_type", "priority", "status", "source"]
    search_fields = ["title", "endpoint"]


@admin.register(TestExecution)
class TestExecutionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "status", "total", "passed", "failed", "skipped", "finished_at"]


@admin.register(TestCaseResult)
class TestCaseResultAdmin(admin.ModelAdmin):
    list_display = ["id", "execution", "case_title", "status", "duration"]
    list_filter = ["status"]
