#!/usr/bin/env python3
"""
CLI скрипт для отправки задачи в Redis FIFO очередь

Использование:
    python scripts/enqueue_job.py <tenant_id> <user_id>

Пример:
    python scripts/enqueue_job.py tenant-123 user-456

Возвращает:
    task_id для мониторинга задачи
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем родительскую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.queue.redis_client import RedisClient
from src.queue.task_queue import TaskQueue


async def enqueue_job(tenant_id: str, user_id: str, redis_url: str):
    """
    Отправляет задачу в Redis очередь и возвращает task_id

    Args:
        tenant_id: ID тенанта
        user_id: ID пользователя
        redis_url: URL Redis сервера
    """
    # Подключение к Redis
    redis_client = RedisClient(redis_url)
    await redis_client.connect()

    try:
        # Создание Task Queue
        task_queue = TaskQueue(redis_client.client)

        # Отправка задачи в очередь
        task_id = await task_queue.enqueue_task(
            tenant_id=tenant_id,
            user_id=user_id,
            task_type="job_search_and_apply"
        )

        # Вывод результата
        print(f"\n✅ Task enqueued successfully!")
        print(f"   Task ID: {task_id}")
        print(f"   Tenant: {tenant_id}")
        print(f"   User: {user_id}")
        print(f"   Status: pending")
        print(f"\n📊 Monitor with:")
        print(f"   python scripts/monitor_task.py {task_id}")
        print(f"\n   Or via API:")
        print(f"   curl http://localhost:8000/task/{task_id}/status")

        return task_id

    finally:
        await redis_client.close()


def main():
    """Основная функция CLI"""
    if len(sys.argv) < 3:
        print("❌ Error: Missing arguments")
        print("\nUsage:")
        print("  python scripts/enqueue_job.py <tenant_id> <user_id>")
        print("\nExample:")
        print("  python scripts/enqueue_job.py tenant-123 user-456")
        sys.exit(1)

    tenant_id = sys.argv[1]
    user_id = sys.argv[2]

    # Получение Redis URL из переменной окружения
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Запуск асинхронной функции
    try:
        task_id = asyncio.run(enqueue_job(tenant_id, user_id, redis_url))
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
