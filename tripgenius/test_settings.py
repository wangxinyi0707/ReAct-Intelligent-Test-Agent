"""测试专用配置：使用 SQLite + 内存缓存 + Celery 同步执行，保证单机可运行、可复现。

用法：
    pytest --ds tripgenius.test_settings
    或设置环境变量 DJANGO_SETTINGS_MODULE=tripgenius.test_settings
"""
import os
import tempfile

from .settings import *  # noqa: F401,F403

# 测试数据库使用 SQLite 内存库，避免依赖本地 MySQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# 测试缓存使用本地内存缓存，避免依赖 Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Session 落库（SQLite），配合 Django test Client 的登录能力
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Celery 同步执行：delay() 直接在当前进程执行，不依赖 broker
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Chroma 向量库指向临时目录，避免测试污染 rag_data/
os.environ.setdefault("CHROMA_PATH", os.path.join(tempfile.gettempdir(), "tripgenius_test_chroma"))

# 关闭可能导致外部依赖的日志写盘
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "level": "WARNING",
        }
    },
}
