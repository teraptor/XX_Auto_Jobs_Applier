# XX Auto Jobs Applier - Multi-Tenant Mode

## 🎯 Обзор

Система для автоматического применения на вакансии с поддержкой множества пользователей (multi-tenant).

**Ключевые особенности:**
- ✅ **FIFO очереди** для задач и результатов через Redis
- ✅ **ID tracking**: уникальные `task_id` и `result_id` для каждой операции
- ✅ **Двунаправленная связь**: task_id ↔ result_id
- ✅ **Shared Browser Pool**: эффективное использование ресурсов
- ✅ **Minimal API**: FastAPI для мониторинга
- ✅ **CLI scripts**: управление через командную строку

## 📋 Требования

- Python 3.11+
- Redis 7.0+
- PostgreSQL 15+ (опционально для полной версии)

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install redis asyncio fastapi uvicorn prometheus-client
```

### 2. Запуск Redis

```bash
# Локально
redis-server

# Или через Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### 3. Настройка переменных окружения

```bash
export REDIS_URL="redis://localhost:6379"
```

### 4. Запуск API (опционально)

```bash
python api/main.py

# Или через uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

API будет доступен на `http://localhost:8000`

## 📖 Использование CLI

### Отправка задачи в очередь

```bash
python scripts/enqueue_job.py <tenant_id> <user_id>

# Пример:
python scripts/enqueue_job.py tenant-123 user-456

# Вывод:
# ✅ Task enqueued successfully!
#    Task ID: 550e8400-e29b-41d4-a716-446655440000
#    Status: pending
```

**Что происходит:**
- Генерируется уникальный `task_id` (UUID v4)
- Задача добавляется в FIFO очередь `tasks:pending`
- Метаданные сохраняются в Redis с TTL 24 часа
- Возвращается `task_id` для мониторинга

### Мониторинг задачи

```bash
python scripts/monitor_task.py <task_id>

# Пример:
python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000

# Непрерывный мониторинг (обновление каждые 5 секунд):
python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000 --watch
```

**Вывод:**
```
📊 Task Status:
   Task ID: 550e8400-e29b-41d4-a716-446655440000
   Status: completed ✅
   Result ID: 661f9511-f3ac-52e5-b827-557766551111
   Tenant: tenant-123
   User: user-456
   Created: 2024-01-15 10:30:00
```

### Чтение результатов

#### Вариант A: Блокирующее ожидание

```bash
python scripts/consume_results.py --mode completed --timeout 60

# Ждет до 60 секунд, пока не появится результат
```

#### Вариант B: Пакетное чтение

```bash
python scripts/consume_results.py --mode completed --batch 10

# Читает до 10 результатов сразу
```

#### Вариант C: Непрерывный режим

```bash
python scripts/consume_results.py --mode all --continuous

# Непрерывно читает все результаты (Ctrl+C для остановки)
```

#### Вариант D: Обратная связь (result_id → task_id)

```bash
python scripts/consume_results.py --result-id 661f9511-f3ac-52e5-b827-557766551111

# Вывод:
# ✅ Found task_id for result:
#    Result ID: 661f9511-f3ac-52e5-b827-557766551111
#    Task ID: 550e8400-e29b-41d4-a716-446655440000
```

## 🌐 Использование API

### Проверка здоровья

```bash
curl http://localhost:8000/health

# Response:
# {"status": "healthy", "redis": "up"}
```

### Статистика очередей

```bash
curl http://localhost:8000/queue/stats

# Response:
# {
#   "tasks_pending": 5,
#   "tasks_processing": 2,
#   "results_completed": 12,
#   "results_failed": 1,
#   "total_active": 7
# }
```

### Статус задачи по task_id

```bash
curl http://localhost:8000/task/550e8400-e29b-41d4-a716-446655440000/status

# Response:
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "completed",
#   "result_id": "661f9511-f3ac-52e5-b827-557766551111",
#   "tenant_id": "tenant-123",
#   "user_id": "user-456",
#   "created_at": "2024-01-15T10:30:00Z"
# }
```

### Данные результата по result_id

```bash
curl http://localhost:8000/result/661f9511-f3ac-52e5-b827-557766551111

# Response:
# {
#   "result_id": "661f9511-f3ac-52e5-b827-557766551111",
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "completed"
# }
```

### Обратная связь: result_id → task_id

```bash
curl http://localhost:8000/result/661f9511-f3ac-52e5-b827-557766551111/task

# Response:
# {
#   "result_id": "661f9511-f3ac-52e5-b827-557766551111",
#   "task_id": "550e8400-e29b-41d4-a716-446655440000"
# }
```

## 🏗️ Архитектура

### Redis Queue Structure

```
INPUT QUEUE (Tasks):
├── tasks:pending              # FIFO для входящих задач
│   └── {"task_id": "uuid", "tenant_id": "...", "user_id": "..."}

OUTPUT QUEUES (Results):
├── results:completed          # FIFO для успешных результатов
│   └── {"task_id": "uuid", "result_id": "uuid", "data": {...}}
└── results:failed             # FIFO для ошибок
    └── {"task_id": "uuid", "result_id": "uuid", "error": "..."}

METADATA (ID Tracking):
├── task:{task_id}:status      # "pending"|"processing"|"completed"|"failed"
├── task:{task_id}:data        # Полные данные задачи
├── task:{task_id}:result_id   # Связь task_id → result_id
└── result:{result_id}:task_id # Обратная связь result_id → task_id
```

### Flow обработки

```
1. CLIENT отправляет задачу
   └─> task_id = enqueue_task()
   └─> LPUSH tasks:pending

2. WORKER извлекает задачу
   └─> task = BRPOP tasks:pending
   └─> SET task:{task_id}:status "processing"
   └─> Выполнение через BotFacade (existing logic)

3. WORKER публикует результат
   └─> result_id = uuid.uuid4()
   └─> LPUSH results:completed
   └─> SET task:{task_id}:result_id
   └─> SET result:{result_id}:task_id

4. CLIENT получает результат
   └─> result = BRPOP results:completed
   └─> Связь task_id ↔ result_id доступна
```

## 📊 Мониторинг

### Prometheus Metrics

API экспортирует метрики в формате Prometheus:

```bash
curl http://localhost:8000/metrics
```

**Доступные метрики:**
- `tasks_enqueued_total` - Всего задач отправлено
- `tasks_completed_total` - Всего задач завершено успешно
- `tasks_failed_total` - Всего задач завершено с ошибкой
- `tasks_pending` - Текущее количество ожидающих задач
- `tasks_processing` - Текущее количество обрабатываемых задач

### Логирование

Все компоненты используют Python logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🔧 Настройка

### Переменные окружения

```bash
# Redis
export REDIS_URL="redis://localhost:6379"

# API (опционально)
export API_HOST="0.0.0.0"
export API_PORT="8000"

# Worker (опционально)
export WORKER_ID="worker-1"
export BROWSER_POOL_SIZE="5"
```

### Redis Configuration

Рекомендуемые настройки Redis для production:

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## 🐛 Отладка

### Проверка очередей Redis

```bash
# Подключение к Redis CLI
redis-cli

# Проверка размера очередей
LLEN tasks:pending
LLEN results:completed
LLEN results:failed

# Просмотр задач в обработке
HGETALL tasks:processing

# Проверка статуса задачи
GET task:550e8400-e29b-41d4-a716-446655440000:status

# Просмотр данных задачи
GET task:550e8400-e29b-41d4-a716-446655440000:data
```

### Очистка очередей (development)

```bash
# ВНИМАНИЕ: Удаляет все данные!
redis-cli FLUSHDB
```

## 📚 Документация

Полная документация по архитектуре и реализации находится в:
- `scrapper.md` - Детальный план миграции
- `docs/` - Дополнительная документация (если есть)

## 🤝 Вклад

Для внесения изменений:

1. Создайте feature branch
2. Внесите изменения
3. Добавьте тесты
4. Создайте pull request

## 📄 Лицензия

[Укажите лицензию проекта]

## 🔗 Полезные ссылки

- [Redis LISTS Documentation](https://redis.io/docs/data-types/lists/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)

---

**Версия:** 2.0.0
**Дата обновления:** 2024-01-15
**Статус:** Active Development
