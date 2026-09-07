"""factory_boy 数据工厂：让测试数据构造简洁、可读。"""
import factory
from django.contrib.auth.models import User

from qa.models import TestCase, TestExecution, TestSuite
from travel.models import DailySchedule, PackingItem, TravelPlan


class UserFactory(factory.django.DjangoModelFactory):
    __test__ = False  # 避免 pytest 当作测试类收集

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    password = factory.PostGenerationMethodCall("set_password", "pass12345")
    email = factory.Faker("email")

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        """与生产注册流程保持一致：用户创建后自动生成资料"""
        from accounts.models import UserProfile

        UserProfile.objects.get_or_create(user=self)


class TravelPlanFactory(factory.django.DjangoModelFactory):
    __test__ = False

    class Meta:
        model = TravelPlan

    user = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence", nb_words=3)
    destination = factory.Faker("city")
    start_date = "2026-10-01"
    end_date = "2026-10-05"
    budget = 5000
    description = "factory 生成"


class DailyScheduleFactory(factory.django.DjangoModelFactory):
    __test__ = False

    class Meta:
        model = DailySchedule

    plan = factory.SubFactory(TravelPlanFactory)
    day = 1
    date = "2026-10-01"
    location = factory.Faker("city")
    activities = "参观景点"


class PackingItemFactory(factory.django.DjangoModelFactory):
    __test__ = False

    class Meta:
        model = PackingItem

    plan = factory.SubFactory(TravelPlanFactory)
    name = "护照"


class TestSuiteFactory(factory.django.DjangoModelFactory):
    __test__ = False

    class Meta:
        model = TestSuite

    name = factory.Sequence(lambda n: f"套件{n}")
    description = "factory 生成"


class TestCaseFactory(factory.django.DjangoModelFactory):
    __test__ = False

    class Meta:
        model = TestCase

    suite = factory.SubFactory(TestSuiteFactory)
    title = factory.Sequence(lambda n: f"测试用例{n}")
    case_type = TestCase.CaseType.MANUAL
    priority = TestCase.Priority.P2
    source = TestCase.Source.MANUAL


class ApiTestCaseFactory(TestCaseFactory):
    """接口用例工厂"""

    case_type = TestCase.CaseType.API
    method = "GET"
    endpoint = "/api/travel/list/"
    params = {}
    expected_status = 200
    expected_keywords = ["plans"]
    need_auth = True


class TestExecutionFactory(factory.django.DjangoModelFactory):
    __test__ = False

    class Meta:
        model = TestExecution

    name = factory.Sequence(lambda n: f"执行{n}")
    suite = factory.SubFactory(TestSuiteFactory)
    created_by = factory.SubFactory(UserFactory)
