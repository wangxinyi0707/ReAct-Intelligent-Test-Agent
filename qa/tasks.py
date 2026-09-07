from celery import shared_task

from qa.services.executor import run_execution
from qa.services.test_agent import run_agent_execution


@shared_task(bind=True)
def execute_test_run(self, execution_id: int):
    """异步执行测试运行：由 Redis/Celery worker 消费"""
    return run_execution(execution_id)


@shared_task(bind=True)
def agent_test_run(self, execution_id: int, goal: str):
    """异步执行 AI 测试 Agent：模型自主调用工具完成接口测试"""
    return run_agent_execution(execution_id, goal).id
