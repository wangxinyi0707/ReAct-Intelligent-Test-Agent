from django.contrib import admin
from .models import TravelKnowledge

@admin.register(TravelKnowledge)
class TravelKnowledgeAdmin(admin.ModelAdmin):
    list_display = ["title", "destination", "category", "is_active", "created_time"]
    search_fields = ["title", "destination", "content"]
    list_filter = ["category", "is_active"]
