from django.urls import path

from .views import TravelPlanViewSet

urlpatterns = [
    path("list/", TravelPlanViewSet.as_view({"get": "list"}), name="plan-list"),
    path("create/", TravelPlanViewSet.as_view({"post": "create"}), name="plan-create"),
    path("<int:pk>/", TravelPlanViewSet.as_view({"get": "retrieve"}), name="plan-detail"),
    path(
        "<int:pk>/update/",
        TravelPlanViewSet.as_view({"put": "update", "patch": "partial_update"}),
        name="plan-update",
    ),
    path(
        "<int:pk>/delete/",
        TravelPlanViewSet.as_view({"delete": "destroy"}),
        name="plan-delete",
    ),
    path(
        "<int:pk>/schedule/add/",
        TravelPlanViewSet.as_view({"post": "schedule"}),
        name="plan-schedule",
    ),
    path(
        "<int:pk>/packing/add/",
        TravelPlanViewSet.as_view({"post": "packing"}),
        name="plan-packing",
    ),
]
