from django.contrib import admin
from .models import UserProfile
@admin.register(UserProfile)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "travel_style",
        "budget_level",
        "language",
        "created_time"
    ]
    list_filter = ('travel_style','created_time')
    search_fields = ('user__username','travel_style')
    ordering = ('-created_time','budget_level')