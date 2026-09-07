"""用户模块接口测试：注册 / 登录(JWT) / 资料 / 登出。"""
import pytest
from rest_framework.test import APIClient

from test.factories import UserFactory

REGISTER_URL = "/api/accounts/register/"
LOGIN_URL = "/api/accounts/login/"
PROFILE_URL = "/api/accounts/profile/"
LOGOUT_URL = "/api/accounts/logout/"


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, anonymous_client):
        resp = anonymous_client.post(
            REGISTER_URL,
            {"username": "newbie", "password": "pass12345", "email": "newbie@test.com"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["message"] == "注册成功"
        assert resp.json()["user"]["username"] == "newbie"

    def test_register_duplicate_username(self, db, anonymous_client, user):
        resp = anonymous_client.post(
            REGISTER_URL,
            {"username": user.username, "password": "pass12345"},
            format="json",
        )
        assert resp.status_code == 400

    def test_register_short_password(self, anonymous_client):
        resp = anonymous_client.post(
            REGISTER_URL,
            {"username": "weak", "password": "123"},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_jwt_tokens(self, db):
        UserFactory.create(username="jwtuser")
        resp = APIClient().post(
            LOGIN_URL, {"username": "jwtuser", "password": "pass12345"}, format="json"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data and "refresh" in data

    def test_login_wrong_password(self, db, anonymous_client):
        UserFactory.create(username="jwtuser")
        resp = anonymous_client.post(
            LOGIN_URL, {"username": "jwtuser", "password": "wrong-password"}, format="json"
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestProfile:
    def test_profile_requires_auth(self, anonymous_client):
        assert anonymous_client.get(PROFILE_URL).status_code == 401

    def test_profile_with_jwt(self, jwt_client):
        resp = jwt_client.get(PROFILE_URL)
        assert resp.status_code == 200
        assert resp.json()["username"] == "jwttester"

    def test_update_profile(self, auth_client):
        resp = auth_client.put(
            PROFILE_URL,
            {"nickname": "阿飞", "travel_style": "美食打卡", "budget_level": "穷游"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["profile"]["nickname"] == "阿飞"


@pytest.mark.django_db
class TestLogout:
    def test_logout_blacklists_refresh_token(self, jwt_client):
        login_resp = jwt_client.post(
            LOGIN_URL, {"username": "jwttester", "password": "pass12345"}, format="json"
        )
        refresh = login_resp.json()["refresh"]
        resp = jwt_client.post(LOGOUT_URL, {"refresh": refresh}, format="json")
        assert resp.status_code == 200
        # 已被黑名单的 refresh 无法再刷新 access
        refresh_resp = jwt_client.post(
            "/api/accounts/login/refresh/", {"refresh": refresh}, format="json"
        )
        assert refresh_resp.status_code == 401

    def test_logout_missing_refresh(self, auth_client):
        resp = auth_client.post(LOGOUT_URL, {}, format="json")
        assert resp.status_code == 400
