#!/usr/bin/env python3
"""
CLI скрипт для чтения результатов из FIFO очередей

Использование:
    python scripts/consume_results.py [OPTIONS]

Опции:
    --mode MODE          Режим: completed, failed, или all (по умолчанию: completed)
    --timeout SECONDS    Timeout для блокирующего чтения (по умолчанию: 60)
    --batch NUMBER       Читать до N результатов за раз (по умолчанию: 1)
    --continuous         Непрерывное чтение результатов
    --result-id ID       Найти task_id по известному result_id

Примеры:
    # Ждать один результат из completed (timeout 60 секунд)
    python scripts/consume_results.py --mode completed --timeout 60

    # Прочитать до 10 результатов
    python scripts/consume_results.py --mode completed --batch 10

    # Непрерывное чтение всех результатов
    python scripts/consume_results.py --mode all --continuous

    # Найти task_id по result_id
    python scripts/consume_results.py --result-id 661f9511-f3ac-52e5-b827-557766551111
"""

import asyncio
import sys
import os
from pathlib import Path
import argparse
import json
from datetime import datetime

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


def print_result(result: dict, index: int = None):
    """Выводит результат в читаемом формате"""
    prefix = f"Result {index}:" if index else "📦 Result received:"

    print(f"\n{prefix}")
    print(f"   Result ID: {result.get('result_id', 'N/A')}")
    print(f"   Task ID: {result.get('task_id', 'N/A')}")
    print(f"   Status: {result.get('status', 'N/A')}")

    # Данные результата
    data = result.get('data', {})
    if data:
        print(f"\n   Data:")
        for key, value in data.items():
            print(f"   ├─ {key}: {value}")

    # Время завершения
    completed_at = result.get('completed_at')
    if completed_at:
        print(f"\n   Completed: {format_datetime(completed_at)}")


async def find_task_by_result(result_id: str, redis_url: str):
    """
    Находит task_id по result_id (обратная связь)

    Args:
        result_id: UUID результата
        redis_url: URL Redis сервера
    """
    redis_client = RedisClient(redis_url)
    await redis_client.connect()

    try:
        task_queue = TaskQueue(redis_client.client)

        task_id = await task_queue.get_task_id(result_id)

        if task_id:
            print(f"\n✅ Found task_id for result:")
            print(f"   Result ID: {result_id}")
            print(f"   Task ID: {task_id}")
            print(f"\n💡 Check task details:")
            print(f"   python scripts/monitor_task.py {task_id}")
        else:
            print(f"\n❌ Task not found for result_id: {result_id}")
            print("\nPossible reasons:")
            print("  - Invalid result_id")
            print("  - Result expired (TTL > 24 hours)")

    finally:
        await redis_client.close()


async def consume_results(
    mode: str,
    timeout: int,
    batch: int,
    continuous: bool,
    redis_url: str
):
    """
    Читает результаты из FIFO очередей

    Args:
        mode: "completed", "failed", или "all"
        timeout: Timeout для блокирующего чтения
        batch: Количество результатов для чтения
        continuous: Непрерывный режим
        redis_url: URL Redis сервера
    """
    redis_client = RedisClient(redis_url)
    await redis_client.connect()

    try:
        task_queue = TaskQueue(redis_client.client)

        # Определение очередей для чтения
        if mode == "all":
            queues = ["completed", "failed"]
        else:
            queues = [mode]

        total_consumed = 0
        batch_count = 0

        print(f"\n🔄 Waiting for results (mode={mode}, timeout={timeout}s)...")

        while True:
            result_found = False

            for queue in queues:
                # Чтение из очереди
                result = await task_queue.consume_result(queue, timeout=timeout)

                if result:
                    result_found = True
                    batch_count += 1
                    total_consumed += 1

                    print_result(result, batch_count if batch > 1 else None)

                    # Остановка если достигнут batch size
                    if batch_count >= batch and not continuous:
                        break

            # Остановка если ничего не найдено
            if not result_found and not continuous:
                if total_consumed == 0:
                    print(f"\n⏱️  No results within {timeout} seconds")
                break

            # Остановка если достигнут batch size
            if batch_count >= batch and not continuous:
                print(f"\n✅ Total: {total_consumed} results processed")
                break

            # Сброс batch_count для непрерывного режима
            if continuous and batch_count >= batch:
                print(f"\n✅ Batch completed: {batch_count} results")
                print(f"🔄 Continuing... (Ctrl+C to stop)")
                batch_count = 0

        # Статистика очередей
        stats = await task_queue.get_queue_stats()
        print(f"\n📊 Queue stats:")
        print(f"   Pending tasks: {stats['tasks_pending']}")
        print(f"   Processing: {stats['tasks_processing']}")
        print(f"   Completed results: {stats['results_completed']}")
        print(f"   Failed results: {stats['results_failed']}")

    finally:
        await redis_client.close()


def main():
    """Основная функция CLI"""
    parser = argparse.ArgumentParser(
        description="Consume results from Redis FIFO queues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Wait for one completed result (60s timeout)
  python scripts/consume_results.py --mode completed --timeout 60

  # Read up to 10 results
  python scripts/consume_results.py --mode completed --batch 10

  # Continuous reading
  python scripts/consume_results.py --mode all --continuous

  # Find task_id by result_id
  python scripts/consume_results.py --result-id 661f9511-f3ac-52e5-b827-557766551111
        """
    )

    parser.add_argument(
        "--mode",
        choices=["completed", "failed", "all"],
        default="completed",
        help="Queue mode: completed, failed, or all (default: completed)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Blocking read timeout in seconds (default: 60)"
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=1,
        help="Number of results to read (default: 1)"
    )

    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Continuous mode (read indefinitely)"
    )

    parser.add_argument(
        "--result-id",
        type=str,
        help="Find task_id by result_id (reverse lookup)"
    )

    args = parser.parse_args()

    # Получение Redis URL из переменной окружения
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Запуск асинхронной функции
    try:
        if args.result_id:
            asyncio.run(find_task_by_result(args.result_id, redis_url))
        else:
            asyncio.run(consume_results(
                args.mode,
                args.timeout,
                args.batch,
                args.continuous,
                redis_url
            ))
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation stopped by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
