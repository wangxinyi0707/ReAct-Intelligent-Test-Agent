from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/travel/", include("travel.urls")),
    path("api/ai/", include("AI.urls")),
    path("api/qa/", include("qa.urls")),
    path("", TemplateView.as_view(template_name="index.html")),
    path("mgr/ai.html", TemplateView.as_view(template_name="ai.html")),
    path("mgr/travel.html", TemplateView.as_view(template_name="travel.html")),
    path("mgr/qa.html", TemplateView.as_view(template_name="qa.html")),
]
