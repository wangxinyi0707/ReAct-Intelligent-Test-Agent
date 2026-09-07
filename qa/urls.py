from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentTestRunView, TestCaseViewSet, TestExecutionViewSet, TestSuiteViewSet

router = DefaultRouter()
router.register("suites", TestSuiteViewSet, basename="qa-suite")
router.register("cases", TestCaseViewSet, basename="qa-case")
router.register("executions", TestExecutionViewSet, basename="qa-execution")

urlpatterns = [
    path("", include(router.urls)),
    path("agent/run/", AgentTestRunView.as_view(), name="qa-agent-run"),
]
