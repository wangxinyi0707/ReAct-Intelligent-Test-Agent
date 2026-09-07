"""pytest 公共 fixtures。"""
import pytest


def _make_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    """普通用户（已登录态可直接 force_authenticate）"""
    from test.factories import UserFactory

    return UserFactory.create()


@pytest.fixture
def auth_client(db, user):
    """DRF APIClient：直接注入认证（Session 认证），适用于业务接口测试"""
    client = _make_client()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anonymous_client(db):
    """未登录的 APIClient"""
    return _make_client()


@pytest.fixture
def jwt_client(db):
    """通过真实登录接口获取 JWT，并用 Bearer token 访问的客户端"""
    from test.factories import UserFactory

    UserFactory.create(username="jwttester")
    client = _make_client()
    resp = client.post(
        "/api/accounts/login/",
        {"username": "jwttester", "password": "pass12345"},
        format="json",
    )
    assert resp.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.json()['access']}")
    return client


@pytest.fixture
def mock_rag(monkeypatch):
    """屏蔽 RAGService：避免加载 embedding 模型与访问 Chroma"""
    class FakeRAG:
        def ask(self, question):
            return "东京推荐浅草寺"

        def search(self, destination):
            return ["杭州西湖非常著名"]

    def fake_get():
        return FakeRAG()

    monkeypatch.setattr("AI.views.get_rag_service", fake_get)
    return FakeRAG()
