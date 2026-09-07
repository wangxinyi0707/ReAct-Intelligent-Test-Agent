"""旅行计划模块接口测试：CRUD / 权限隔离 / 行程与行李。"""
import pytest

from test.factories import (
    TravelPlanFactory,
    UserFactory,
)
from travel.models import DailySchedule, PackingItem, TravelPlan


@pytest.fixture
def plan_payload():
    return {
        "title": "日本七日游",
        "destination": "东京",
        "start_date": "2026-01-01",
        "end_date": "2026-01-07",
        "budget": 5000,
        "description": "自由行",
    }


@pytest.mark.django_db
class TestCreatePlan:
    def test_create_plan_success(self, auth_client, plan_payload):
        resp = auth_client.post("/api/travel/create/", plan_payload, format="json")
        assert resp.status_code == 201
        assert TravelPlan.objects.filter(title="日本七日游").count() == 1
        assert resp.json()["id"] is not None

    def test_create_plan_requires_auth(self, anonymous_client, plan_payload):
        assert (
            anonymous_client.post("/api/travel/create/", plan_payload, format="json").status_code
            == 401
        )

    def test_create_plan_invalid_date(self, auth_client, plan_payload):
        plan_payload["start_date"] = "not-a-date"
        resp = auth_client.post("/api/travel/create/", plan_payload, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestListPlans:
    def test_list_returns_own_plans(self, auth_client, user):
        TravelPlanFactory.create_batch(3, user=user)
        resp = auth_client.get("/api/travel/list/")
        assert resp.status_code == 200
        assert len(resp.json()["plans"]) == 3

    def test_list_does_not_leak_other_users_plans(self, auth_client, user):
        TravelPlanFactory.create(user=user)
        other = UserFactory.create(username="otheruser")
        TravelPlanFactory.create(user=other, title="别人的计划")
        resp = auth_client.get("/api/travel/list/")
        titles = [p["title"] for p in resp.json()["plans"]]
        assert "别人的计划" not in titles

    def test_list_requires_auth(self, anonymous_client):
        assert anonymous_client.get("/api/travel/list/").status_code == 401


@pytest.mark.django_db
class TestPlanDetail:
    def test_detail(self, auth_client, user):
        plan = TravelPlanFactory.create(user=user)
        resp = auth_client.get(f"/api/travel/{plan.id}/")
        assert resp.status_code == 200
        assert resp.json()["id"] == plan.id

    def test_detail_of_others_plan_404(self, auth_client):
        other = UserFactory.create(username="otheruser")
        plan = TravelPlanFactory.create(user=other)
        assert auth_client.get(f"/api/travel/{plan.id}/").status_code == 404


@pytest.mark.django_db
class TestUpdateDelete:
    def test_update_plan(self, auth_client, user):
        plan = TravelPlanFactory.create(user=user)
        resp = auth_client.patch(
            f"/api/travel/{plan.id}/update/",
            {"title": "新标题", "destination": "大阪"},
            format="json",
        )
        assert resp.status_code == 200
        plan.refresh_from_db()
        assert plan.title == "新标题"

    def test_delete_plan(self, auth_client, user):
        plan = TravelPlanFactory.create(user=user)
        resp = auth_client.delete(f"/api/travel/{plan.id}/delete/")
        assert resp.status_code == 204
        assert TravelPlan.objects.count() == 0


@pytest.mark.django_db
class TestScheduleAndPacking:
    def test_add_schedule(self, auth_client, user):
        plan = TravelPlanFactory.create(user=user)
        resp = auth_client.post(
            f"/api/travel/{plan.id}/schedule/add/",
            {
                "day": 1,
                "date": "2026-01-01",
                "location": "浅草寺",
                "activities": "参观、拍照",
                "transportation": "地铁",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert DailySchedule.objects.filter(plan=plan).count() == 1

    def test_add_packing(self, auth_client, user):
        plan = TravelPlanFactory.create(user=user)
        resp = auth_client.post(
            f"/api/travel/{plan.id}/packing/add/", {"name": "护照"}, format="json"
        )
        assert resp.status_code == 201
        assert PackingItem.objects.filter(plan=plan).count() == 1

    def test_schedule_others_plan_404(self, auth_client):
        other = UserFactory.create(username="otheruser")
        plan = TravelPlanFactory.create(user=other)
        resp = auth_client.post(
            f"/api/travel/{plan.id}/schedule/add/",
            {"day": 1, "date": "2026-01-01", "location": "x", "activities": "y"},
            format="json",
        )
        assert resp.status_code == 404
