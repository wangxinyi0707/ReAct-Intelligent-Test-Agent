"""AI 模块接口测试：RAG 问答 / 翻译 / 旅行推荐（全部 mock 掉外部 LLM 与向量库）。"""
import pytest
from unittest.mock import patch


@pytest.mark.django_db
class TestAsk:
    def test_ask_returns_answer(self, auth_client, mock_rag):
        resp = auth_client.post(
            "/api/ai/ask/", {"question": "东京有什么景点?"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["answer"] == "东京推荐浅草寺"

    def test_ask_requires_auth(self, anonymous_client):
        assert (
            anonymous_client.post(
                "/api/ai/ask/", {"question": "hi"}, format="json"
            ).status_code
            == 401
        )

    def test_ask_missing_question(self, auth_client):
        resp = auth_client.post("/api/ai/ask/", {}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestTranslate:
    @patch("AI.translator.OpenAIService.chat", return_value="Hello")
    def test_translate(self, mock_chat, auth_client):
        resp = auth_client.post(
            "/api/ai/translate/",
            {"text": "你好", "language": "English"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["translation"] == "Hello"
        mock_chat.assert_called_once()


@pytest.mark.django_db
class TestRecommend:
    @patch("AI.openai_service.OpenAIService.chat", return_value="Day1 西湖 → 灵隐寺")
    def test_recommend(self, mock_chat, auth_client, mock_rag):
        resp = auth_client.post(
            "/api/ai/recommend/",
            {
                "destination": "杭州",
                "days": 3,
                "budget": "5000",
                "preference": "自然风光",
            },
            format="json",
        )
        assert resp.status_code == 200
        assert "西湖" in resp.json()["plan"]

    def test_recommend_invalid_days(self, auth_client):
        resp = auth_client.post(
            "/api/ai/recommend/", {"destination": "杭州", "days": 0}, format="json"
        )
        assert resp.status_code == 400
