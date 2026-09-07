from django.core.cache import cache

def plan_cache_key(user_id):
    return f"user:{user_id}:travel_plans"

def get_user_plans_cache(user_id):
    return cache.get(plan_cache_key(user_id))

def set_user_plans_cache(user_id, data, timeout=300):
    cache.set(plan_cache_key(user_id), data, timeout=timeout)

def clear_user_plan_cache(user_id):
    cache.delete(plan_cache_key(user_id))
