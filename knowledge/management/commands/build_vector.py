from django.core.management.base import BaseCommand
from knowledge.models import TravelKnowledge
from AI.rag_service import get_rag_service

class Command(BaseCommand):
    help = "构建旅游知识RAG向量库"

    def handle(self, *args, **kwargs):
        self.stdout.write("开始构建RAG知识库...")
        queryset = TravelKnowledge.objects.filter(is_active=True)
        documents = []
        for item in queryset:
            text = f"""
标题：{item.title}
目的地：{item.destination}
类别：{item.category}
详细信息：{item.content}
"""
            documents.append(text)

        if not documents:
            self.stdout.write(self.style.WARNING("没有知识数据"))
            return

        rag = get_rag_service()
        count = rag.add_documents(documents)
        self.stdout.write(self.style.SUCCESS(f"成功生成 {count} 个向量"))
