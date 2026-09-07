"""接口扫描服务：自动解析 Django URLconf，发现项目全部 API 及其参数结构。

亮点：除了常规的路径/方法发现，还会尝试从 DRF 视图类的 serializer_class
提取请求字段，为 AI 生成接口用例提供真实参数结构。
"""
from django.urls import get_resolver


def _resolve_methods(callback) -> list:
    allowed = getattr(callback, "allowed_methods", None)
    if allowed:
        return sorted(m for m in allowed if m in {"GET", "POST", "PUT", "PATCH", "DELETE"})
    # 普通函数视图无法静态判断，默认放开常用方法
    return ["GET", "POST"]


def _resolve_serializer_fields(callback) -> list:
    view_class = getattr(callback, "view_class", None)
    if view_class is None:
        return []
    serializer_class = getattr(view_class, "serializer_class", None)
    if serializer_class is None:
        return []
    try:
        return list(serializer_class().fields.keys())
    except Exception:
        return []


def _resolve_need_auth(callback) -> bool:
    view_class = getattr(callback, "view_class", None)
    if view_class is None:
        return False
    from rest_framework.permissions import AllowAny

    permissions = getattr(view_class, "permission_classes", ())
    for perm in permissions:
        if issubclass(perm, AllowAny):
            return False
    return True


def discover_apis() -> list:
    """遍历 URLconf，返回项目全部 /api/ 接口清单"""
    resolver = get_resolver()
    apis = []

    def walk(patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):  # include() 的嵌套路由
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
                continue
            name = pattern.name
            if not name:
                continue
            path = prefix + str(pattern.pattern)
            if not path.startswith("api/"):
                continue
            callback = pattern.callback
            apis.append(
                {
                    "name": name,
                    "path": "/" + path,
                    "methods": _resolve_methods(callback),
                    "fields": _resolve_serializer_fields(callback),
                    "need_auth": _resolve_need_auth(callback),
                    "module": getattr(callback, "__module__", ""),
                }
            )

    walk(resolver.url_patterns)
    # 去重（同一 path 可能因同名 pattern 重复收集）
    seen, unique = set(), []
    for api in apis:
        key = (api["path"], tuple(api["methods"]))
        if key not in seen:
            seen.add(key)
            unique.append(api)
    return unique
