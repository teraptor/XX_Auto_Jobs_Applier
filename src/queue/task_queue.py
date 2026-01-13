"""
Task Queue с FIFO и ID tracking

Генерирует уникальные task_id при enqueue и result_id при публикации результатов.
Поддерживает двунаправленную связь task_id ↔ result_id через Redis.
FIFO гарантии через Redis LISTS (LPUSH/BRPOP).
"""

import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Task queue с FIFO и ID tracking

    Основные возможности:
    - Генерирует уникальный task_id при enqueue
    - Генерирует уникальный result_id при публикации результата
    - Поддерживает двунаправленную связь task_id ↔ result_id
    - FIFO гарантии через Redis LISTS (LPUSH/BRPOP)
    - TTL 24 часа для всех метаданных
    """

    TASKS_PENDING = "tasks:pending"
    RESULTS_COMPLETED = "results:completed"
    RESULTS_FAILED = "results:failed"
    TASKS_PROCESSING = "tasks:processing"

    def __init__(self, redis_client, worker_id: str = None):
        """
        Инициализация Task Queue

        Args:
            redis_client: Redis client (redis.asyncio.Redis)
            worker_id: Уникальный ID worker'а (генерируется автоматически если не указан)
        """
        self.redis = redis_client
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"

    async def enqueue_task(
        self,
        tenant_id: str,
        user_id: str,
        task_type: str = "job_search_and_apply",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Создает задачу с уникальным task_id и добавляет в FIFO очередь

        Args:
            tenant_id: ID тенанта
            user_id: ID пользователя
            task_type: Тип задачи (по умолчанию "job_search_and_apply")
            metadata: Дополнительные метаданные для задачи

        Returns:
            task_id (str): UUID v4 для отслеживания задачи

        Example:
            >>> task_id = await queue.enqueue_task("tenant-123", "user-456")
            >>> print(task_id)
            550e8400-e29b-41d4-a716-446655440000
        """
        task_id = str(uuid.uuid4())  # ✅ Генерация уникального ID

        task_data = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "type": task_type,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        # Добавление в FIFO очередь (LPUSH = добавление в начало)
        await self.redis.lpush(
            self.TASKS_PENDING,
            json.dumps(task_data)
        )

        # Сохранение метаданных с TTL 24 часа (86400 секунд)
        await self.redis.setex(
            f"task:{task_id}:status",
            86400,
            "pending"
        )
        await self.redis.setex(
            f"task:{task_id}:data",
            86400,
            json.dumps(task_data)
        )

        logger.info(
            f"Task enqueued: {task_id} "
            f"(tenant={tenant_id}, user={user_id}, type={task_type})"
        )

        return task_id  # ✅ Возвращаем ID клиенту

    async def dequeue_task(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Извлекает задачу из FIFO очереди (блокирующее чтение)

        Args:
            timeout: Максимальное время ожидания в секундах

        Returns:
            task_data с task_id или None если очередь пуста

        Example:
            >>> task = await queue.dequeue_task(timeout=10)
            >>> if task:
            >>>     print(f"Processing task {task['task_id']}")
        """
        # BRPOP = блокирующее извлечение с конца (FIFO порядок)
        result = await self.redis.brpop(self.TASKS_PENDING, timeout=timeout)

        if result:
            _, task_json = result
            task_data = json.loads(task_json)
            task_id = task_data["task_id"]

            # Обновление статуса на "processing"
            await self.redis.setex(
                f"task:{task_id}:status",
                86400,
                "processing"
            )

            # Сохранение метаданных о worker'е
            processing_metadata = {
                "worker_id": self.worker_id,
                "started_at": datetime.utcnow().isoformat()
            }
            await self.redis.hset(
                self.TASKS_PROCESSING,
                task_id,
                json.dumps(processing_metadata)
            )

            logger.info(f"Task dequeued: {task_id} by worker {self.worker_id}")
            return task_data

        return None

    async def publish_result(
        self,
        task_id: str,
        result_data: Dict[str, Any],
        status: str = "success"
    ) -> str:
        """
        Публикует результат с новым result_id в FIFO очередь

        Args:
            task_id: ID исходной задачи
            result_data: Данные результата
            status: "success" или "failed"

        Returns:
            result_id (str): UUID v4 для отслеживания результата

        Example:
            >>> result_id = await queue.publish_result(
            >>>     task_id="550e8400-...",
            >>>     result_data={"applications_sent": 15},
            >>>     status="success"
            >>> )
        """
        result_id = str(uuid.uuid4())  # ✅ Генерация нового result_id

        output = {
            "task_id": task_id,           # ✅ Связь с задачей
            "result_id": result_id,       # ✅ Уникальный ID результата
            "status": status,
            "data": result_data,
            "completed_at": datetime.utcnow().isoformat()
        }

        # Выбор очереди в зависимости от статуса
        queue = (
            self.RESULTS_COMPLETED
            if status == "success"
            else self.RESULTS_FAILED
        )

        # Публикация в FIFO очередь результатов
        await self.redis.lpush(queue, json.dumps(output))

        # Обновление метаданных
        final_status = "completed" if status == "success" else "failed"
        await self.redis.setex(
            f"task:{task_id}:status",
            86400,
            final_status
        )

        # ✅ Двунаправленная связь task_id ↔ result_id
        await self.redis.setex(
            f"task:{task_id}:result_id",
            86400,
            result_id
        )
        await self.redis.setex(
            f"result:{result_id}:task_id",
            86400,
            task_id
        )

        # Удаление из списка обрабатываемых
        await self.redis.hdel(self.TASKS_PROCESSING, task_id)

        logger.info(
            f"Result published: result_id={result_id}, "
            f"task_id={task_id}, status={status}"
        )

        return result_id

    async def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Получает статус задачи по ID

        Args:
            task_id: UUID задачи

        Returns:
            "pending" | "processing" | "completed" | "failed" | None

        Example:
            >>> status = await queue.get_task_status("550e8400-...")
            >>> print(status)  # "completed"
        """
        status = await self.redis.get(f"task:{task_id}:status")
        return status.decode() if status else None

    async def get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает полные данные задачи по ID

        Args:
            task_id: UUID задачи

        Returns:
            Dict с данными задачи или None
        """
        data = await self.redis.get(f"task:{task_id}:data")
        return json.loads(data.decode()) if data else None

    async def get_result_id(self, task_id: str) -> Optional[str]:
        """
        Получает result_id по task_id

        Args:
            task_id: UUID задачи

        Returns:
            result_id или None если задача не завершена

        Example:
            >>> result_id = await queue.get_result_id("550e8400-...")
            >>> print(result_id)  # "661f9511-..."
        """
        result_id = await self.redis.get(f"task:{task_id}:result_id")
        return result_id.decode() if result_id else None

    async def get_task_id(self, result_id: str) -> Optional[str]:
        """
        Получает task_id по result_id (обратная связь)

        Args:
            result_id: UUID результата

        Returns:
            task_id или None

        Example:
            >>> task_id = await queue.get_task_id("661f9511-...")
            >>> print(task_id)  # "550e8400-..."
        """
        task_id = await self.redis.get(f"result:{result_id}:task_id")
        return task_id.decode() if task_id else None

    async def consume_result(
        self,
        queue: str = "completed",
        timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Читает результат из FIFO очереди (блокирующее чтение)

        Args:
            queue: "completed" или "failed"
            timeout: Максимальное время ожидания в секундах

        Returns:
            result_data с task_id и result_id или None

        Example:
            >>> result = await queue.consume_result("completed", timeout=60)
            >>> if result:
            >>>     print(f"Task {result['task_id']} → Result {result['result_id']}")
        """
        queue_key = (
            self.RESULTS_COMPLETED
            if queue == "completed"
            else self.RESULTS_FAILED
        )

        result = await self.redis.brpop(queue_key, timeout=timeout)

        if result:
            _, result_json = result
            result_data = json.loads(result_json)

            logger.info(
                f"Result consumed: result_id={result_data['result_id']}, "
                f"task_id={result_data['task_id']}, queue={queue}"
            )
            return result_data

        return None

    async def get_queue_stats(self) -> Dict[str, int]:
        """
        Получает статистику всех очередей

        Returns:
            Dict со счетчиками для каждой очереди

        Example:
            >>> stats = await queue.get_queue_stats()
            >>> print(f"Pending: {stats['tasks_pending']}")
        """
        return {
            "tasks_pending": await self.redis.llen(self.TASKS_PENDING),
            "tasks_processing": await self.redis.hlen(self.TASKS_PROCESSING),
            "results_completed": await self.redis.llen(self.RESULTS_COMPLETED),
            "results_failed": await self.redis.llen(self.RESULTS_FAILED)
        }

    async def get_processing_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Получает список всех обрабатываемых задач

        Returns:
            Dict где ключ = task_id, значение = metadata

        Example:
            >>> tasks = await queue.get_processing_tasks()
            >>> for task_id, metadata in tasks.items():
            >>>     print(f"{task_id}: worker={metadata['worker_id']}")
        """
        processing = await self.redis.hgetall(self.TASKS_PROCESSING)
        return {
            k.decode(): json.loads(v.decode())
            for k, v in processing.items()
        }

    async def clear_queue(self, queue_name: str) -> int:
        """
        Очищает указанную очередь (использовать осторожно!)

        Args:
            queue_name: Имя очереди для очистки

        Returns:
            Количество удаленных элементов

        Warning:
            Эта операция необратима!
        """
        count = await self.redis.llen(queue_name)
        await self.redis.delete(queue_name)
        logger.warning(f"Queue {queue_name} cleared: {count} items removed")
        return count
