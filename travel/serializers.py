from rest_framework import serializers

from .models import DailySchedule, PackingItem, TravelPlan


class DailyScheduleSerializer(serializers.ModelSerializer):
    """每日行程序列化器"""

    class Meta:
        model = DailySchedule
        fields = ["id", "day", "date", "location", "activities", "transportation", "notes"]
        read_only_fields = ["id"]


class PackingItemSerializer(serializers.ModelSerializer):
    """行李清单序列化器"""

    class Meta:
        model = PackingItem
        fields = ["id", "name", "checked"]
        read_only_fields = ["id"]


class TravelPlanSerializer(serializers.ModelSerializer):
    """旅行计划序列化器，嵌套返回行程与行李"""

    schedules = DailyScheduleSerializer(many=True, read_only=True)
    packing_items = PackingItemSerializer(many=True, read_only=True)

    class Meta:
        model = TravelPlan
        fields = [
            "id",
            "title",
            "destination",
            "start_date",
            "end_date",
            "budget",
            "description",
            "schedules",
            "packing_items",
            "created_time",
            "update_time",
        ]
        read_only_fields = ["id", "created_time", "update_time"]
