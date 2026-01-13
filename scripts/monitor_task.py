#!/usr/bin/env python3
"""
CLI скрипт для мониторинга статуса задачи по task_id

Использование:
    python scripts/monitor_task.py <task_id> [--watch]

Примеры:
    python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000
    python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000 --watch

Опции:
    --watch     Непрерывный мониторинг с обновлением каждые 5 секунд
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Добавляем родительскую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.queue.redis_client import RedisClient
from src.queue.task_queue import TaskQueue


def format_datetime(iso_string: str) -> str:
    """Форматирует ISO datetime в читаемый формат"""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_string


def calculate_duration(created_at: str, completed_at: str) -> str:
    """Вычисляет длительность между двумя timestamps"""
    try:
        start = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        end = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
        duration = end - start

        minutes = int(duration.total_seconds() / 60)
        seconds = int(duration.total_seconds() % 60)

        if minutes > 0:
            return f"{minutes} min {seconds} sec"
        else:
            return f"{seconds} sec"
    except:
        return "N/A"


async def monitor_task(task_id: str, redis_url: str, watch: bool = False):
    """
    Проверяет статус задачи по task_id

    Args:
        task_id: UUID задачи
        redis_url: URL Redis сервера
        watch: Режим непрерывного мониторинга
    """
    # Подключение к Redis
    redis_client = RedisClient(redis_url)
    await redis_client.connect()

    try:
        task_queue = TaskQueue(redis_client.client)

        while True:
            # Очистка экрана в режиме watch
            if watch:
                os.system('clear' if os.name == 'posix' else 'cls')

            # Получение статуса
            status = await task_queue.get_task_status(task_id)

            if not status:
                print(f"\n❌ Task not found: {task_id}")
                print("\nPossible reasons:")
                print("  - Invalid task_id")
                print("  - Task expired (TTL > 24 hours)")
                print("  - Task never created")
                return

            # Получение данных задачи
            task_data = await task_queue.get_task_data(task_id)

            # Статус эмодзи
            status_emoji = {
                "pending": "⏳",
                "processing": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(status, "❓")

            print(f"\n📊 Task Status:")
            print(f"   Task ID: {task_id}")
            print(f"   Status: {status} {status_emoji}")

            if task_data:
                print(f"   Tenant: {task_data.get('tenant_id', 'N/A')}")
                print(f"   User: {task_data.get('user_id', 'N/A')}")
                print(f"   Type: {task_data.get('type', 'N/A')}")
                print(f"   Created: {format_datetime(task_data.get('created_at', 'N/A'))}")

            # Информация о processing
            if status == "processing":
                processing_tasks = await task_queue.get_processing_tasks()
                if task_id in processing_tasks:
                    metadata = processing_tasks[task_id]
                    print(f"   Worker: {metadata.get('worker_id', 'N/A')}")
                    print(f"   Started: {format_datetime(metadata.get('started_at', 'N/A'))}")

            # Информация о результате
            if status in ["completed", "failed"]:
                result_id = await task_queue.get_result_id(task_id)

                if result_id:
                    print(f"   Result ID: {result_id}")

                if task_data and status == "completed":
                    created_at = task_data.get('created_at')
                    # Попытка получить время завершения из метаданных
                    # В реальной реализации нужно сохранять completed_at
                    print(f"   Duration: (check result for details)")

            # Дополнительная информация
            if status == "completed":
                print(f"\n💡 Get result details:")
                result_id = await task_queue.get_result_id(task_id)
                if result_id:
                    print(f"   python scripts/consume_results.py --result-id {result_id}")
                    print(f"   curl http://localhost:8000/result/{result_id}")

            elif status == "failed":
                print(f"\n⚠️  Check error details in failed results queue")

            # Выход из цикла если не в режиме watch
            if not watch:
                break

            # Обновление статуса в режиме watch
            if status in ["completed", "failed"]:
                print(f"\n✓ Task finished")
                break

            print(f"\n🔄 Updating in 5 seconds... (Ctrl+C to stop)")
            await asyncio.sleep(5)

    finally:
        await redis_client.close()


def main():
    """Основная функция CLI"""
    if len(sys.argv) < 2:
        print("❌ Error: Missing task_id")
        print("\nUsage:")
        print("  python scripts/monitor_task.py <task_id> [--watch]")
        print("\nExamples:")
        print("  python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000")
        print("  python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000 --watch")
        sys.exit(1)

    task_id = sys.argv[1]
    watch = "--watch" in sys.argv

    # Получение Redis URL из переменной окружения
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Запуск асинхронной функции
    try:
        asyncio.run(monitor_task(task_id, redis_url, watch))
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring stopped by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
