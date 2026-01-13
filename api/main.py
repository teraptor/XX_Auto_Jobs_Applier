"""
Minimal FastAPI для мониторинга и управления задачами

Endpoints:
- GET /health - Health check
- GET /metrics - Prometheus metrics
- GET /queue/stats - Статистика очередей
- GET /task/{task_id}/status - Статус задачи по ID
- GET /result/{result_id} - Данные результата по ID
- GET /result/{result_id}/task - Найти task_id по result_id
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app, Counter, Gauge
import os
import sys
from pathlib import Path

# Добавляем родительскую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.queue.redis_client import RedisClient
from src.queue.task_queue import TaskQueue

# Инициализация FastAPI
app = FastAPI(
    title="XX Auto Jobs Applier - Multi-Tenant",
    version="2.0.0",
    description="Minimal API для мониторинга задач с FIFO + ID tracking"
)

# Environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Global Redis client
redis_client = None
task_queue = None

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Metrics
tasks_enqueued_total = Counter('tasks_enqueued_total', 'Total tasks enqueued')
tasks_completed_total = Counter('tasks_completed_total', 'Total tasks completed')
tasks_failed_total = Counter('tasks_failed_total', 'Total tasks failed')
tasks_pending_gauge = Gauge('tasks_pending', 'Number of pending tasks')
tasks_processing_gauge = Gauge('tasks_processing', 'Number of tasks being processed')


@app.on_event("startup")
async def startup_event():
    """Подключение к Redis при старте"""
    global redis_client, task_queue

    redis_client = RedisClient(REDIS_URL)
    await redis_client.connect()
    task_queue = TaskQueue(redis_client.client, worker_id="api")


@app.on_event("shutdown")
async def shutdown_event():
    """Закрытие соединения с Redis"""
    if redis_client:
        await redis_client.close()


@app.get("/")
async def root():
    """API информация"""
    return {
        "name": "XX Auto Jobs Applier Multi-Tenant",
        "version": "2.0.0",
        "features": [
            "FIFO queue для задач",
            "FIFO queue для результатов",
            "ID tracking (task_id ↔ result_id)",
            "Shared Browser Pool",
            "PostgreSQL + Redis"
        ],
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "queue_stats": "/queue/stats",
            "task_status": "/task/{task_id}/status",
            "result_data": "/result/{result_id}",
            "result_to_task": "/result/{result_id}/task"
        }
    }


@app.get("/health")
async def health():
    """
    Health check

    Проверяет доступность Redis
    """
    redis_ok = await redis_client.health_check()

    if not redis_ok:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return {
        "status": "healthy",
        "redis": "up"
    }


@app.get("/queue/stats")
async def queue_stats():
    """
    Статистика очередей

    Возвращает количество задач в каждой очереди
    """
    stats = await task_queue.get_queue_stats()

    # Update Prometheus metrics
    tasks_pending_gauge.set(stats['tasks_pending'])
    tasks_processing_gauge.set(stats['tasks_processing'])

    return {
        "tasks_pending": stats['tasks_pending'],
        "tasks_processing": stats['tasks_processing'],
        "results_completed": stats['results_completed'],
        "results_failed": stats['results_failed'],
        "total_active": stats['tasks_pending'] + stats['tasks_processing']
    }


@app.get("/task/{task_id}/status")
async def task_status(task_id: str):
    """
    Получить статус задачи по task_id

    Args:
        task_id: UUID задачи

    Returns:
        JSON с информацией о задаче

    Example:
        GET /task/550e8400-e29b-41d4-a716-446655440000/status
    """
    # Получение статуса
    status = await task_queue.get_task_status(task_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    # Базовая информация
    response = {
        "task_id": task_id,
        "status": status
    }

    # Данные задачи
    task_data = await task_queue.get_task_data(task_id)
    if task_data:
        response["tenant_id"] = task_data.get("tenant_id")
        response["user_id"] = task_data.get("user_id")
        response["type"] = task_data.get("type")
        response["created_at"] = task_data.get("created_at")

    # Result ID если задача завершена
    if status in ["completed", "failed"]:
        result_id = await task_queue.get_result_id(task_id)
        if result_id:
            response["result_id"] = result_id

    # Worker info если в обработке
    if status == "processing":
        processing_tasks = await task_queue.get_processing_tasks()
        if task_id in processing_tasks:
            metadata = processing_tasks[task_id]
            response["worker_id"] = metadata.get("worker_id")
            response["started_at"] = metadata.get("started_at")

    return response


@app.get("/result/{result_id}")
async def result_data(result_id: str):
    """
    Получить данные результата по result_id

    Args:
        result_id: UUID результата

    Returns:
        JSON с данными результата

    Example:
        GET /result/661f9511-f3ac-52e5-b827-557766551111
    """
    # Найти task_id по result_id
    task_id = await task_queue.get_task_id(result_id)

    if not task_id:
        raise HTTPException(
            status_code=404,
            detail=f"Result not found: {result_id}"
        )

    # Получить статус задачи
    status = await task_queue.get_task_status(task_id)

    # Базовая информация
    response = {
        "result_id": result_id,
        "task_id": task_id,
        "status": status
    }

    # Примечание: полные данные результата находятся в FIFO очереди
    # Здесь возвращаем только метаданные из Redis
    return response


@app.get("/result/{result_id}/task")
async def result_to_task(result_id: str):
    """
    Найти task_id по result_id (обратная связь)

    Args:
        result_id: UUID результата

    Returns:
        JSON с task_id

    Example:
        GET /result/661f9511-f3ac-52e5-b827-557766551111/task
    """
    task_id = await task_queue.get_task_id(result_id)

    if not task_id:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found for result: {result_id}"
        )

    return {
        "result_id": result_id,
        "task_id": task_id
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик ошибок"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
