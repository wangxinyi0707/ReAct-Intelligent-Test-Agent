import os

from celery import Celery

# 设置 Django 默认配置模块，供 Celery 加载
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tripgenius.settings")

app = Celery("tripgenius")

# 从 Django settings 读取以 CELERY_ 开头的配置
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现各 app 下的 tasks.py
app.autodiscover_tasks()
