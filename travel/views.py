from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .cache import clear_user_plan_cache, get_user_plans_cache, set_user_plans_cache
from .models import DailySchedule, PackingItem, TravelPlan
from .serializers import TravelPlanSerializer


class TravelPlanViewSet(viewsets.ModelViewSet):
    """
    旅行计划 CRUD：
    - list   GET    /api/travel/list/
    - create POST   /api/travel/create/
    - detail GET    /api/travel/{pk}/
    - update PUT    /api/travel/{pk}/update/
    - delete DELETE /api/travel/{pk}/delete/
    - schedule POST /api/travel/{pk}/schedule/add/
    - packing  POST /api/travel/{pk}/packing/add/
    """

    serializer_class = TravelPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 只允许访问自己的计划；prefetch_related 消除序列化时的 N+1 查询
        return TravelPlan.objects.filter(user=self.request.user).prefetch_related(
            "schedules", "packing_items"
        )

    def perform_create(self, serializer):
        plan = serializer.save(user=self.request.user)
        clear_user_plan_cache(self.request.user.id)
        return plan

    def perform_update(self, serializer):
        serializer.save()
        clear_user_plan_cache(self.request.user.id)

    def perform_destroy(self, instance):
        instance.delete()
        clear_user_plan_cache(self.request.user.id)

    def list(self, request, *args, **kwargs):
        # 缓存旁路模式：读缓存 -> 未命中查库并回写
        user_id = request.user.id
        cached = get_user_plans_cache(user_id)
        if cached is not None:
            return Response({"plans": cached})

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        set_user_plans_cache(user_id, serializer.data, timeout=300)
        return Response({"plans": serializer.data})

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        """给计划新增每日行程"""
        plan = self.get_object()
        schedule = DailySchedule.objects.create(
            plan=plan,
            day=request.data.get("day"),
            date=request.data.get("date"),
            location=request.data.get("location"),
            activities=request.data.get("activities"),
            transportation=request.data.get("transportation", ""),
        )
        clear_user_plan_cache(request.user.id)
        return Response(
            {"id": schedule.id, "day": schedule.day, "location": schedule.location},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def packing(self, request, pk=None):
        """给计划新增行李清单项"""
        plan = self.get_object()
        item = PackingItem.objects.create(plan=plan, name=request.data.get("name"))
        clear_user_plan_cache(request.user.id)
        return Response(
            {"id": item.id, "name": item.name, "checked": item.checked},
            status=status.HTTP_201_CREATED,
        )
