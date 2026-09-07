from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """用户扩展信息"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    # 用户旅行偏好
    preferred_destinations = models.TextField(blank=True, default="")
    travel_style = models.CharField(max_length=100, default="自由行")
    budget_level = models.CharField(max_length=50, default="普通")
    language = models.CharField(max_length=20, default="中文")
    created_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username
