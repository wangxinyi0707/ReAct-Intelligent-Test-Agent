from rest_framework import serializers

from .models import TestCase, TestCaseResult, TestExecution, TestSuite


class TestSuiteSerializer(serializers.ModelSerializer):
    case_count = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        fields = [
            "id",
            "name",
            "description",
            "case_count",
            "created_by",
            "created_time",
            "update_time",
        ]
        read_only_fields = ["id", "created_by", "created_time", "update_time"]

    def get_case_count(self, obj):
        return obj.cases.filter(status=TestCase.Status.ACTIVE).count()


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = [
            "id",
            "suite",
            "title",
            "description",
            "case_type",
            "priority",
            "status",
            "source",
            "tags",
            "method",
            "endpoint",
            "params",
            "expected_status",
            "expected_keywords",
            "need_auth",
            "created_by",
            "created_time",
            "update_time",
        ]
        read_only_fields = ["id", "created_by", "created_time", "update_time"]


class TestCaseResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseResult
        fields = ["id", "case", "case_title", "status", "duration", "log", "analysis"]


class TestExecutionSerializer(serializers.ModelSerializer):
    results = TestCaseResultSerializer(many=True, read_only=True)
    pass_rate = serializers.SerializerMethodField()

    class Meta:
        model = TestExecution
        fields = [
            "id",
            "name",
            "suite",
            "status",
            "total",
            "passed",
            "failed",
            "skipped",
            "duration",
            "summary",
            "pass_rate",
            "results",
            "created_by",
            "started_at",
            "finished_at",
            "created_time",
        ]
        read_only_fields = [
            "id",
            "status",
            "total",
            "passed",
            "failed",
            "skipped",
            "duration",
            "summary",
            "created_by",
            "started_at",
            "finished_at",
            "created_time",
        ]

    def get_pass_rate(self, obj):
        if obj.total == 0:
            return 0
        return round(obj.passed / obj.total * 100, 2)
