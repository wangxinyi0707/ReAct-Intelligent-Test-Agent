from django.db import models
from django.contrib.auth.models import User

class TravelPlan(models.Model):
    """用户旅行计划"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="travel_plans")
    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, default="")
    created_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_time"]

    def __str__(self):
        return self.title


class DailySchedule(models.Model):
    """每日行程"""
    plan = models.ForeignKey(TravelPlan, on_delete=models.CASCADE, related_name="schedules")
    day = models.IntegerField()
    date = models.DateField()
    location = models.CharField(max_length=200)
    activities = models.TextField()
    transportation = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.plan.title}-Day{self.day}"


class PackingItem(models.Model):
    """行李清单"""
    plan = models.ForeignKey(TravelPlan, on_delete=models.CASCADE, related_name="packing_items")
    name = models.CharField(max_length=100)
    checked = models.BooleanField(default=False)

    def __str__(self):
        return self.name
