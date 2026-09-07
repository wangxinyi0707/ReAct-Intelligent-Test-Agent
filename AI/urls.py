from django.urls import path

from . import views

urlpatterns = [
    path("ask/", views.AskView.as_view(), name="ai-ask"),
    path("translate/", views.TranslateView.as_view(), name="ai-translate"),
    path("recommend/", views.RecommendView.as_view(), name="ai-recommend"),
]
