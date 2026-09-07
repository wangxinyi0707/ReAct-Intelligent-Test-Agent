from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .openai_service import OpenAIService
from .prompt import build_plan_prompt
from .rag_service import get_rag_service
from .translator import Translator


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000)


class TranslateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)
    language = serializers.CharField(max_length=50)


class RecommendSerializer(serializers.Serializer):
    destination = serializers.CharField(max_length=200)
    days = serializers.IntegerField(min_value=1, max_value=60)
    budget = serializers.CharField(max_length=100, required=False, default="")
    preference = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class AskView(APIView):
    """RAG 知识问答：检索知识库并结合大模型回答"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = get_rag_service().ask(serializer.validated_data["question"])
        return Response({"answer": answer})


class TranslateView(APIView):
    """文本翻译：相同输入走 Redis 缓存，避免重复调用大模型"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TranslateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = Translator().translate(
            serializer.validated_data["text"],
            serializer.validated_data["language"],
        )
        return Response({"translation": result})


class RecommendView(APIView):
    """智能旅行方案推荐：RAG 检索目的地知识后生成旅行计划"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RecommendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        rag = get_rag_service()
        knowledge = "\n".join(rag.search(data["destination"]))
        prompt = build_plan_prompt(
            data["destination"],
            data["days"],
            data["budget"],
            data.get("preference", ""),
            knowledge,
        )
        answer = OpenAIService().chat(prompt)
        return Response({"plan": answer})
