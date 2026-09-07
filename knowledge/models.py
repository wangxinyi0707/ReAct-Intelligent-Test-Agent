from django.db import models

class TravelKnowledge(models.Model):
    """RAG旅游知识库数据"""
    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=100)
    category = models.CharField(max_length=100, default="景点")
    content = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_time"]

    def __str__(self):
        return self.title
