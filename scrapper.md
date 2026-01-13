# План трансформации Python XX_Auto_Jobs_Applier в мультитенантную систему

**МИНИМАЛЬНЫЕ ИЗМЕНЕНИЯ С FIFO + ID TRACKING:**
- ✅ PostgreSQL + Redis FIFO для задач и результатов
- ✅ Уникальные task_id при создании, result_id при завершении
- ✅ Minimal FastAPI для мониторинга по ID
- ✅ Shared Browser Pool (5-10 браузеров)
- ✅ CLI скрипты с поддержкой ID tracking
- ✅ Минимальные изменения Python логики (только injection точки)

---

## 📋 ОГЛАВЛЕНИЕ ШАГОВ

### ФАЗА 1: Инфраструктура и Database (4-5 часов)
- **Шаг 1.1** - PostgreSQL с shared schema + tenant_id
- **Шаг 1.2** - Redis для FIFO очередей (tasks + results)
- **Шаг 1.3** - Миграции (7 таблиц + task_id/result_id columns)
- **Шаг 1.4** - Repository pattern

### ФАЗА 2: Queue Management с ID Tracking (3-4 часа) ⭐ НОВОЕ
- **Шаг 2.1** - Task Queue с генерацией task_id
- **Шаг 2.2** - Result Queue с генерацией result_id
- **Шаг 2.3** - ID tracking в Redis (task_id ↔ result_id)
- **Шаг 2.4** - Result Consumer

### ФАЗА 3: CLI Management с ID Support (3-4 часа)
- **Шаг 3.1** - CLI скрипт для создания tenant/user
- **Шаг 3.2** - CLI скрипт для загрузки search config
- **Шаг 3.3** - CLI скрипт для запуска задач (возвращает task_id) ⭐
- **Шаг 3.4** - CLI скрипт для мониторинга по task_id ⭐ НОВЫЙ
- **Шаг 3.5** - CLI скрипт для чтения результатов (показывает result_id) ⭐ НОВЫЙ
- **Шаг 3.6** - CLI скрипт для просмотра результатов из PostgreSQL

### ФАЗА 4: Minimal FastAPI (2-3 часа)
- **Шаг 4.1** - Health checks endpoint
- **Шаг 4.2** - Metrics endpoint (Prometheus)
- **Шаг 4.3** - Browser pool status endpoint
- **Шаг 4.4** - Queue stats endpoint
- **Шаг 4.5** - Task status endpoint (/task/{task_id}/status) ⭐ НОВЫЙ
- **Шаг 4.6** - Result endpoint (/result/{result_id}) ⭐ НОВЫЙ

### ФАЗА 5: Адаптация хранилища (5-6 часов)
- **Шаг 5.1** - Storage Adapter (wrapper над YAML логикой)
- **Шаг 5.2** - Repositories для всех сущностей
- **Шаг 5.3** - Browser Session Manager с БД
- **Шаг 5.4** - LLM Cache в БД
- **Шаг 5.5** - Шифрование HH credentials
- **Шаг 5.6** - Добавить task_id в сохранение результатов ⭐

### ФАЗА 6: Browser Pool и Worker (6-8 часов)
- **Шаг 6.1** - Browser Pool Manager (shared pool)
- **Шаг 6.2** - Worker с task_id context ⭐
- **Шаг 6.3** - Интеграция через DI

### ФАЗА 7: Docker (4-5 часов)
- **Шаг 7.1** - Dockerfile для Minimal API
- **Шаг 7.2** - Dockerfile для Worker с Playwright
- **Шаг 7.3** - Docker Compose (PostgreSQL + Redis + Worker)
- **Шаг 7.4** - CLI scripts container

### ФАЗА 8: Testing (опционально, 2-3 часа)
- **Шаг 8.1** - Unit tests для Queue Management
- **Шаг 8.2** - Integration tests для FIFO flow
- **Шаг 8.3** - E2E тест с ID tracking

**Общее время:** 29-38 часов (3.5-5 дней активной разработки)

---

## 📖 ДЕТАЛЬНОЕ ОПИСАНИЕ

---

## 🔄 REDIS QUEUE ARCHITECTURE С ID TRACKING

### Структура очередей Redis

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT QUEUE (Tasks)                          │
└─────────────────────────────────────────────────────────────────┘
tasks:pending                    # LIST - FIFO для входящих задач
├── Format: {
│     "task_id": "550e8400-e29b-41d4-a716-446655440000",  ← UUID v4
│     "tenant_id": "tenant-123",
│     "user_id": "user-456",
│     "type": "job_search_and_apply",
│     "created_at": "2024-01-15T10:30:00Z"
│   }
├── Operations:
│   ├── LPUSH (enqueue) - добавление новых задач
│   └── BRPOP (dequeue) - извлечение worker'ом (блокирующее)

┌─────────────────────────────────────────────────────────────────┐
│                   OUTPUT QUEUES (Results)                       │
└─────────────────────────────────────────────────────────────────┘
results:completed                # LIST - FIFO для успешных результатов
├── Format: {
│     "task_id": "550e8400-e29b-41d4-a716-446655440000",  ← Ссылка
│     "result_id": "661f9511-f3ac-52e5-b827-557766551111", ← NEW UUID
│     "status": "success",
│     "data": {
│       "applications_sent": 15,
│       "vacancies_processed": 50,
│       "duration_minutes": 15
│     },
│     "completed_at": "2024-01-15T10:45:00Z"
│   }

results:failed                   # LIST - FIFO для ошибок
├── Format: {
│     "task_id": "550e8400-e29b-41d4-a716-446655440000",
│     "result_id": "772fa622-g4bd-63f6-c938-668877662222",
│     "status": "failed",
│     "error": "Captcha not solved after 3 attempts",
│     "failed_at": "2024-01-15T10:35:00Z"
│   }

┌─────────────────────────────────────────────────────────────────┐
│              TASK TRACKING (Metadata по ID)                     │
└─────────────────────────────────────────────────────────────────┘
task:{task_id}:status           # STRING - "pending"|"processing"|"completed"|"failed"
├── TTL: 24 hours
├── Example: task:550e8400...:status → "completed"

task:{task_id}:data             # STRING - JSON с полными данными задачи
├── TTL: 24 hours
├── Example: task:550e8400...:data → "{...full task data...}"

task:{task_id}:result_id        # STRING - связь task_id → result_id
├── TTL: 24 hours
├── Example: task:550e8400...:result_id → "661f9511..."
└── Позволяет найти result_id по известному task_id ✅

result:{result_id}:task_id      # STRING - обратная связь result_id → task_id
├── TTL: 24 hours
├── Example: result:661f9511...:task_id → "550e8400..."
└── Позволяет найти task_id по известному result_id ✅

┌─────────────────────────────────────────────────────────────────┐
│                         METADATA                                │
└─────────────────────────────────────────────────────────────────┘
tasks:processing                # HASH - {task_id: metadata}
├── Format: {
│     "550e8400...": {
│       "worker_id": "worker-1",
│       "started_at": "2024-01-15T10:30:05Z"
│     }
│   }
└── Удаляется при завершении задачи

pool:stats                      # HASH - статистика Browser Pool
├── Format: {
│     "total": 5,
│     "available": 3,
│     "busy": 2
│   }
```

### Flow обработки задач с ID Tracking

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: CLIENT/CLI - Создание задачи                           │
└─────────────────────────────────────────────────────────────────┘
$ python scripts/enqueue_job.py tenant-123 user-456

1. task_id = uuid.uuid4()
   → "550e8400-e29b-41d4-a716-446655440000" ✅ Генерация ID

2. task_data = {
     "task_id": task_id,
     "tenant_id": "tenant-123",
     "user_id": "user-456",
     "type": "job_search_and_apply",
     "created_at": datetime.utcnow().isoformat()
   }

3. Redis Operations:
   ├─> LPUSH tasks:pending (JSON.dumps(task_data))
   ├─> SET task:{task_id}:status "pending" EX 86400
   └─> SET task:{task_id}:data (JSON.dumps(task_data)) EX 86400

4. RETURN task_id
   → Output: "✅ Task enqueued: 550e8400-e29b-41d4-a716-446655440000"


┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: WORKER - Извлечение и обработка                        │
└─────────────────────────────────────────────────────────────────┘
Worker Loop (runs continuously):

1. task_data = BRPOP tasks:pending 5  # Блокирующее чтение, timeout 5s
   → Получил: {"task_id": "550e8400...", ...}

2. Mark as processing:
   ├─> HSET tasks:processing task_id {"worker_id": "worker-1", "started_at": "..."}
   └─> SET task:{task_id}:status "processing" EX 86400

3. Load context from PostgreSQL:
   ├─> search_config = await repos.search_config.get_active(tenant_id, user_id)
   ├─> hh_credentials = await repos.user.get_hh_credentials(tenant_id, user_id)
   └─> browser_session = await repos.browser_session.get_session(tenant_id, user_id)

4. Acquire browser from pool:
   browser = await browser_pool.acquire(timeout=60)

5. Execute existing bot logic:
   result = await run_bot_facade(
       context=TenantContext(tenant_id, user_id, task_id),  ← task_id passed
       browser=browser,
       search_config=search_config,
       credentials=hh_credentials
   )
   → BotFacade, JobApplier, ResumeScraper работают как раньше ✅
   → Только добавлен task_id в логи и в сохранение результатов

6. Release browser:
   await browser_pool.release(browser)


┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: WORKER - Публикация результата                         │
└─────────────────────────────────────────────────────────────────┘
7a. SUCCESS PATH:
    ├─> result_id = uuid.uuid4()
    │   → "661f9511-f3ac-52e5-b827-557766551111" ✅ Новый ID для результата
    │
    ├─> result_data = {
    │     "task_id": task_id,           # ← Связь с задачей
    │     "result_id": result_id,       # ← Уникальный ID результата
    │     "status": "success",
    │     "data": {
    │       "applications_sent": 15,
    │       "vacancies_processed": 50
    │     },
    │     "completed_at": datetime.utcnow().isoformat()
    │   }
    │
    ├─> Redis Operations:
    │   ├─> LPUSH results:completed (JSON.dumps(result_data))
    │   ├─> SET task:{task_id}:status "completed" EX 86400
    │   ├─> SET task:{task_id}:result_id result_id EX 86400    # ← Связь
    │   ├─> SET result:{result_id}:task_id task_id EX 86400    # ← Обратная связь
    │   └─> HDEL tasks:processing task_id
    │
    └─> Worker продолжает цикл (BRPOP следующей задачи)

7b. FAILURE PATH:
    ├─> result_id = uuid.uuid4()
    ├─> error_data = {
    │     "task_id": task_id,
    │     "result_id": result_id,
    │     "status": "failed",
    │     "error": "Browser session expired",
    │     "failed_at": datetime.utcnow().isoformat()
    │   }
    │
    └─> LPUSH results:failed (JSON.dumps(error_data))
        ... (остальные операции аналогичны)


┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: CLIENT - Мониторинг по task_id                         │
└─────────────────────────────────────────────────────────────────┘
$ python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000

1. status = GET task:{task_id}:status
   → "completed"

2. IF status == "completed":
   result_id = GET task:{task_id}:result_id
   → "661f9511-f3ac-52e5-b827-557766551111" ✅ Получили result_id

3. Output:
   📊 Task Status:
      Task ID: 550e8400-e29b-41d4-a716-446655440000
      Status: completed ✅
      Result ID: 661f9511-f3ac-52e5-b827-557766551111
      Created: 2024-01-15T10:30:00Z
      Completed: 2024-01-15T10:45:00Z


┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: CLIENT - Чтение результатов из FIFO                    │
└─────────────────────────────────────────────────────────────────┘
$ python scripts/consume_results.py --mode completed --timeout 60

1. result_data = BRPOP results:completed 60  # Блокирующее чтение
   → Получил: {
       "task_id": "550e8400...",
       "result_id": "661f9511...",
       "status": "success",
       "data": {...}
     }

2. Output:
   📦 Result received:
      Result ID: 661f9511-f3ac-52e5-b827-557766551111
      Task ID: 550e8400-e29b-41d4-a716-446655440000  ✅ Связь
      Status: success
      Data: {...}

3. Можно также найти task_id по result_id:
   task_id = GET result:{result_id}:task_id
   → "550e8400..." ✅ Обратная связь работает
```

### Преимущества двунаправленной связи ID

1. **task_id → result_id**: Клиент получает task_id при enqueue → может мониторить → получает result_id
2. **result_id → task_id**: Result Consumer читает результат с result_id → может найти исходную задачу
3. **FIFO гарантии**: Redis LISTS обеспечивают порядок FIFO через LPUSH/BRPOP
4. **TTL 24 часа**: Автоматическая очистка устаревших метаданных
5. **Независимые очереди**: results:completed и results:failed можно обрабатывать отдельно

---

## 🔍 РЕАЛЬНАЯ АРХИТЕКТУРА XX_Auto_Jobs_Applier

**После изучения проекта `/Users/teraptor/go/src/github.com/XX_Auto_Jobs_Applier`:**

### Фактическая структура проекта:

```
XX_Auto_Jobs_Applier/
├── main.py                           # Единственная точка входа (asyncio.run(main()))
├── src/
│   ├── app_config.py                # Runtime конфиги (MONKEY_MODE, LLM_MODEL, etc.)
│   ├── job_manager/
│   │   ├── bot_facade.py           # 🎯 КЛЮЧЕВОЙ ОРКЕСТРАТОР - координирует все
│   │   ├── job_applier.py          # Основной движок подачи заявок
│   │   ├── playwright_manager.py   # Browser automation (Playwright)
│   │   ├── resume_scraper.py       # Извлечение резюме из HH.ru
│   │   └── search_customizer.py    # Настройка параметров поиска
│   ├── llm/
│   │   ├── llm_manager.py          # GPTAnswerer - LLM интеграция (langchain)
│   │   └── prompts.py              # Промпты для LLM
│   ├── telegram/
│   │   └── telegram_manager.py     # Telegram отчеты + решение капчи
│   ├── views/                      # Pydantic модели (SearchConfig, Secrets, Job, Resume)
│   ├── utils/
│   │   ├── utils.py                # 📝 YAML I/O функции (save_to_yaml, load_yaml)
│   │   └── browser_utils.py        # Playwright helpers
│   └── resume_builder/             # Resume generation (optional)
└── data_folder/
    ├── secrets/secrets.yaml        # HH login/password, LLM API key, Telegram
    ├── search_config/search_config.yaml  # Параметры поиска
    ├── browser_session/hh_state.json     # Playwright session
    └── output/                     # 📊 YAML выходные файлы
        ├── success.yaml            # Успешные заявки
        ├── failed.yaml             # Неудачные заявки
        ├── skipped.yaml            # Пропущенные заявки
        ├── answers.yaml            # Кэш LLM ответов
        └── resume_info.yaml        # Локальная копия резюме
```

### Ключевые компоненты для интеграции:

1. **BotFacade (`job_manager/bot_facade.py`)** - центральный оркестратор
   - Координирует ResumeScraper, SearchCustomizer, JobApplier
   - **ТОЧКА ИНТЕГРАЦИИ:** Сюда инжектим tenant context и repositories

2. **JobApplier (`job_manager/job_applier.py`)** - основной движок
   - Пагинация по страницам вакансий
   - Проверка blacklist, дубликатов
   - LLM scoring (1-100) для определения интереса
   - Генерация cover letters через LLM
   - **ТОЧКА ИНТЕГРАЦИИ:** Заменяем YAML на StorageAdapter

3. **GPTAnswerer (`llm/llm_manager.py`)** - LLM интеграция
   - Поддержка OpenAI, Gemini, GigaChat, Ollama
   - Кэширование ответов (`answers.yaml`)
   - Tracking стоимости вызовов
   - **ТОЧКА ИНТЕГРАЦИИ:** Кэш в PostgreSQL вместо YAML

4. **PlaywrightJobManager** - browser automation
   - Session persistence (`hh_state.json`)
   - **ТОЧКА ИНТЕГРАЦИИ:** Session в PostgreSQL

5. **YAML I/O (`utils/utils.py`)**
   - Функции: `save_to_yaml()`, `load_yaml()`
   - **ТОЧКА ИНТЕГРАЦИИ:** Обернуть в StorageAdapter

### Workflow существующего кода:

```
main.py → BotFacade
├── ResumeScraper.get_resume_info()     [HH.ru → resume_info.yaml]
├── SearchCustomizer.start_search()      [Настройка фильтров]
└── JobApplier.start_applying()
    ├── Loop по страницам (max_applies_num)
    ├── For each vacancy:
    │   ├── Check blacklist
    │   ├── Check duplicates (в success.yaml)
    │   ├── LLM scoring (70+ = interesting)
    │   ├── Generate cover letter (LLM)
    │   ├── Answer questions (LLM)
    │   └── Submit → save to success.yaml
    └── Send Telegram report
```

### Минимальные точки изменения для multi-tenant:

1. **`utils/utils.py`** - обернуть `save_to_yaml()` → `StorageAdapter`
2. **`job_applier.py`** - инжектить `StorageAdapter` вместо прямого YAML
3. **`bot_facade.py`** - добавить tenant_id, user_id параметры
4. **`llm/llm_manager.py`** - кэш ответов в PostgreSQL
5. **Worker** - загружать config из БД, запускать BotFacade

---

## ФАЗА 1: Инфраструктура

### Шаг 1.1 - PostgreSQL (Shared Schema)

**Создаваемые файлы:**
- `src/database/connection.py`
- `alembic.ini`
- `alembic/env.py`

**Структура БД:**

```sql
-- Tenants (корневая таблица)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    hh_login VARCHAR(255),
    hh_password_encrypted TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_tenant_email UNIQUE(tenant_id, email)
);

-- Applications
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vacancy_id VARCHAR(255) NOT NULL,
    vacancy_url TEXT,
    company_name VARCHAR(500),
    position_title VARCHAR(500),
    status VARCHAR(50) NOT NULL,
    cover_letter TEXT,
    error_message TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_tenant_user_vacancy UNIQUE(tenant_id, user_id, vacancy_id)
);

-- Browser Sessions
CREATE TABLE browser_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_state JSONB NOT NULL,
    is_valid BOOLEAN DEFAULT true,
    last_validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_tenant_user_session UNIQUE(tenant_id, user_id)
);

-- Search Configs
CREATE TABLE search_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LLM Cache
CREATE TABLE llm_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cache_key VARCHAR(255) NOT NULL,
    response_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_tenant_cache_key UNIQUE(tenant_id, cache_key)
);

-- Job Tasks (для tracking)
CREATE TABLE job_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    payload JSONB,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_applications_tenant_user ON applications(tenant_id, user_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_browser_sessions_tenant_user ON browser_sessions(tenant_id, user_id);
CREATE INDEX idx_search_configs_active ON search_configs(tenant_id, user_id, is_active);
CREATE INDEX idx_job_tasks_status ON job_tasks(tenant_id, status);
```

**Код connection.py:**

```python
import asyncpg
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize connection pool"""
        logger.info("Connecting to database...")
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=10,
            max_size=50,
            command_timeout=60
        )
        logger.info("Database connection pool created")

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
```

---

### Шаг 1.2 - Redis Queue Structure

**Создаваемые файлы:**
- `src/queue/redis_client.py`

**Структура Redis:**

```
# Task Queue
browser:tasks:pending          # LIST - FIFO queue для всех задач
browser:tasks:processing       # HASH - {task_id: worker_id}
browser:results:{task_id}      # STRING (JSON), TTL 24h

# Browser Pool
browser:pool:available         # LIST - доступные browser slots
browser:pool:stats             # HASH - статистика использования

# Rate Limiting (опционально)
ratelimit:{tenant_id}:daily    # STRING (counter), TTL 24h
```

**Код redis_client.py:**

```python
import redis.asyncio as redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        logger.info("Connecting to Redis...")
        self.client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20
        )
        logger.info("Redis connected")

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
```

---

### Шаг 1.3 - Миграции

**Создаваемые файлы:**
- `alembic/versions/001_create_tenants.py`
- `alembic/versions/002_create_users.py`
- `alembic/versions/003_create_applications.py`
- `alembic/versions/004_create_browser_sessions.py`
- `alembic/versions/005_create_search_configs.py`
- `alembic/versions/006_create_llm_cache.py`
- `alembic/versions/007_create_job_tasks.py`

Использование Alembic для управления миграциями БД.

---

### Шаг 1.4 - Repository Pattern

**Создаваемые файлы:**
- `src/repositories/base.py`
- `src/repositories/application_repository.py`
- `src/repositories/user_repository.py`
- `src/repositories/search_config_repository.py`
- `src/repositories/browser_session_repository.py`
- `src/repositories/llm_cache_repository.py`

**Код base.py:**

```python
from abc import ABC
import asyncpg

class BaseRepository(ABC):
    """Base repository with tenant awareness"""

    def __init__(self, db_manager):
        self.db = db_manager

    async def _execute(self, query: str, *params):
        """Execute query"""
        async with self.db.pool.acquire() as conn:
            return await conn.execute(query, *params)

    async def _fetchone(self, query: str, *params):
        """Fetch one row"""
        async with self.db.pool.acquire() as conn:
            return await conn.fetchrow(query, *params)

    async def _fetchall(self, query: str, *params):
        """Fetch all rows"""
        async with self.db.pool.acquire() as conn:
            return await conn.fetch(query, *params)
```

**Код application_repository.py:**

```python
from typing import List, Optional
import uuid
from .base import BaseRepository

class ApplicationRepository(BaseRepository):

    async def create(self, tenant_id: str, user_id: str, app_data: dict) -> str:
        """Create application record"""
        app_id = str(uuid.uuid4())

        await self._execute("""
            INSERT INTO applications (
                id, tenant_id, user_id, vacancy_id, vacancy_url,
                company_name, position_title, status, cover_letter, error_message
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            app_id, tenant_id, user_id,
            app_data["vacancy_id"],
            app_data.get("vacancy_url"),
            app_data.get("company_name"),
            app_data.get("position_title"),
            app_data["status"],
            app_data.get("cover_letter"),
            app_data.get("error_message")
        )

        return app_id

    async def get_by_user(self, tenant_id: str, user_id: str,
                         status: Optional[str] = None) -> List[dict]:
        """Get applications for user"""
        query = """
            SELECT * FROM applications
            WHERE tenant_id = $1 AND user_id = $2
        """
        params = [tenant_id, user_id]

        if status:
            query += " AND status = $3"
            params.append(status)

        query += " ORDER BY applied_at DESC"

        rows = await self._fetchall(query, *params)
        return [dict(row) for row in rows]

    async def check_exists(self, tenant_id: str, user_id: str, vacancy_id: str) -> bool:
        """Check if application exists"""
        count = await self._fetchone("""
            SELECT COUNT(*) as cnt FROM applications
            WHERE tenant_id = $1 AND user_id = $2 AND vacancy_id = $3
        """, tenant_id, user_id, vacancy_id)

        return count['cnt'] > 0
```

---

## ФАЗА 2: CLI Management (БЕЗ API!)

### Шаг 2.1 - CLI: Создание tenant/user

**Файл:** `scripts/create_tenant.py`

```python
#!/usr/bin/env python3
import asyncio
import asyncpg
import uuid
from cryptography.fernet import Fernet
import sys
import os

async def create_tenant(name: str, slug: str, db_url: str):
    """Create tenant"""
    tenant_id = str(uuid.uuid4())

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("""
            INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)
        """, tenant_id, name, slug)

        print(f"✅ Tenant created: {tenant_id}")
        print(f"   Name: {name}")
        print(f"   Slug: {slug}")
        return tenant_id
    finally:
        await conn.close()

async def create_user(
    tenant_id: str,
    email: str,
    full_name: str,
    hh_login: str,
    hh_password: str,
    encryption_key: str,
    db_url: str
):
    """Create user with encrypted HH credentials"""
    user_id = str(uuid.uuid4())

    # Encrypt HH password
    cipher = Fernet(encryption_key.encode())
    encrypted_password = cipher.encrypt(hh_password.encode()).decode()

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("""
            INSERT INTO users (id, tenant_id, email, full_name, hh_login, hh_password_encrypted)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, user_id, tenant_id, email, full_name, hh_login, encrypted_password)

        print(f"✅ User created: {user_id}")
        print(f"   Email: {email}")
        print(f"   HH Login: {hh_login}")
        return user_id
    finally:
        await conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_tenant.py <tenant_name> <slug>")
        print("Example: python create_tenant.py 'Company A' 'company-a'")
        sys.exit(1)

    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/autoapplyer")
    asyncio.run(create_tenant(sys.argv[1], sys.argv[2], db_url))
```

**Использование:**
```bash
# Создать тенанта
python scripts/create_tenant.py "Company A" "company-a"

# Создать пользователя
python scripts/create_user.py <tenant_id> user@example.com "John Doe" hh_login hh_password
```

---

### Шаг 2.2 - CLI: Загрузка search config

**Файл:** `scripts/load_search_config.py`

```python
#!/usr/bin/env python3
import asyncio
import asyncpg
import yaml
import uuid
import json
import sys
import os

async def load_search_config(tenant_id: str, user_id: str, config_file: str, db_url: str):
    """Load search config from YAML to DB"""

    # Read YAML
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    config_id = str(uuid.uuid4())

    conn = await asyncpg.connect(db_url)
    try:
        # Deactivate old configs
        await conn.execute("""
            UPDATE search_configs
            SET is_active = false
            WHERE tenant_id = $1 AND user_id = $2
        """, tenant_id, user_id)

        # Insert new config
        await conn.execute("""
            INSERT INTO search_configs (id, tenant_id, user_id, name, config, is_active)
            VALUES ($1, $2, $3, $4, $5, true)
        """, config_id, tenant_id, user_id, config.get("name", "default"), json.dumps(config))

        print(f"✅ Config loaded: {config_id}")
        print(f"   Job title: {config.get('job_title')}")
        print(f"   Max applies: {config.get('max_applies_num')}")
    finally:
        await conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python load_search_config.py <tenant_id> <user_id> <config_file.yaml>")
        sys.exit(1)

    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/autoapplyer")
    asyncio.run(load_search_config(sys.argv[1], sys.argv[2], sys.argv[3], db_url))
```

**Использование:**
```bash
python scripts/load_search_config.py <tenant_id> <user_id> search_config.yaml
```

---

### Шаг 2.3 - CLI: Запуск задачи (→ Redis)

**Файл:** `scripts/enqueue_job.py`

```python
#!/usr/bin/env python3
import asyncio
import redis.asyncio as redis
import json
import uuid
import sys
import os
from datetime import datetime

async def enqueue_job(tenant_id: str, user_id: str, redis_url: str):
    """Enqueue job search task to Redis"""

    task_id = str(uuid.uuid4())

    task_data = {
        "id": task_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "type": "job_search_and_apply",
        "created_at": datetime.utcnow().isoformat()
    }

    client = await redis.from_url(redis_url, decode_responses=True)
    try:
        # Push to queue
        await client.rpush("browser:tasks:pending", json.dumps(task_data))

        print(f"✅ Task enqueued: {task_id}")
        print(f"   Tenant: {tenant_id}")
        print(f"   User: {user_id}")
        print(f"\n📊 Monitor result:")
        print(f"   redis-cli GET browser:results:{task_id}")

        return task_id
    finally:
        await client.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python enqueue_job.py <tenant_id> <user_id>")
        sys.exit(1)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    asyncio.run(enqueue_job(sys.argv[1], sys.argv[2], redis_url))
```

**Использование:**
```bash
# Ручной запуск
python scripts/enqueue_job.py <tenant_id> <user_id>

# Или через cron для автозапуска:
# Каждый день в 9:00
0 9 * * * python scripts/enqueue_job.py <tenant_id> <user_id>
```

---

### Шаг 2.4 - CLI: Просмотр результатов

**Файл:** `scripts/view_applications.py`

```python
#!/usr/bin/env python3
import asyncio
import asyncpg
from tabulate import tabulate
import sys
import os

async def view_applications(tenant_id: str, user_id: str, db_url: str, limit: int = 50):
    """View applications from DB"""

    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch("""
            SELECT
                company_name,
                position_title,
                status,
                applied_at
            FROM applications
            WHERE tenant_id = $1 AND user_id = $2
            ORDER BY applied_at DESC
            LIMIT $3
        """, tenant_id, user_id, limit)

        data = [dict(row) for row in rows]

        if not data:
            print("❌ No applications found")
            return

        print(tabulate(data, headers="keys", tablefmt="grid"))

        # Stats
        success = sum(1 for r in data if r['status'] == 'success')
        failed = sum(1 for r in data if r['status'] == 'failed')
        skipped = sum(1 for r in data if r['status'] == 'skipped')

        print(f"\n📊 Stats:")
        print(f"   Success: {success}")
        print(f"   Failed: {failed}")
        print(f"   Skipped: {skipped}")
        print(f"   Total: {len(data)}")

    finally:
        await conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python view_applications.py <tenant_id> <user_id> [limit]")
        sys.exit(1)

    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/autoapplyer")

    asyncio.run(view_applications(sys.argv[1], sys.argv[2], db_url, limit))
```

**Использование:**
```bash
# Последние 50 заявок
python scripts/view_applications.py <tenant_id> <user_id>

# Последние 100 заявок
python scripts/view_applications.py <tenant_id> <user_id> 100
```

---

## ФАЗА 3: Minimal FastAPI (ТОЛЬКО МОНИТОРИНГ)

### Шаг 3.1-3.4 - Health/Metrics API

**Файл:** `api/main.py`

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app, Counter, Gauge
import asyncpg
import redis.asyncio as redis
import os

app = FastAPI(title="AutoApplyer Monitoring")

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
BROWSER_POOL_SIZE = int(os.getenv("BROWSER_POOL_SIZE", "5"))

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Metrics
browser_pool_available = Gauge('browser_pool_available', 'Available browsers')
tasks_pending = Gauge('tasks_pending', 'Pending tasks in queue')
tasks_processing = Gauge('tasks_processing', 'Tasks being processed')

async def check_db() -> bool:
    """Check database connection"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        return True
    except:
        return False

async def check_redis() -> bool:
    """Check Redis connection"""
    try:
        client = await redis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
        await client.close()
        return True
    except:
        return False

@app.get("/health")
async def health():
    """Health check"""
    db_ok = await check_db()
    redis_ok = await check_redis()

    status = "healthy" if (db_ok and redis_ok) else "unhealthy"

    return {
        "status": status,
        "database": "up" if db_ok else "down",
        "redis": "up" if redis_ok else "down"
    }

@app.get("/pool/status")
async def pool_status():
    """Browser pool status"""
    client = await redis.from_url(REDIS_URL, decode_responses=True)
    try:
        available = await client.llen("browser:pool:available")
        processing = await client.hlen("browser:tasks:processing")

        # Update metrics
        browser_pool_available.set(available)

        return {
            "pool_size": BROWSER_POOL_SIZE,
            "available": available,
            "busy": BROWSER_POOL_SIZE - available,
            "tasks_processing": processing
        }
    finally:
        await client.close()

@app.get("/queue/stats")
async def queue_stats():
    """Queue statistics"""
    client = await redis.from_url(REDIS_URL, decode_responses=True)
    try:
        pending = await client.llen("browser:tasks:pending")
        processing = await client.hlen("browser:tasks:processing")

        # Update metrics
        tasks_pending.set(pending)
        tasks_processing.set(processing)

        return {
            "pending": pending,
            "processing": processing,
            "total": pending + processing
        }
    finally:
        await client.close()

@app.get("/")
async def root():
    """API Info"""
    return {
        "name": "AutoApplyer Multi-Tenant",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "pool_status": "/pool/status",
            "queue_stats": "/queue/stats"
        }
    }
```

**Результат:** Minimal API только для мониторинга, без бизнес-логики.

---

## ФАЗА 4: Адаптация хранилища

### Шаг 4.1 - Storage Adapter

**Файл:** `src/adapters/storage_adapter.py`

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class StorageAdapter:
    """
    Adapter: Existing YAML logic → PostgreSQL

    Минимальные изменения в существующем коде:
    БЫЛО: yaml.dump(data, file)
    СТАЛО: await storage_adapter.save_success(data)
    """

    def __init__(self, repos: dict, tenant_id: str, user_id: str):
        self.repos = repos
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def save_success(self, application_data: dict):
        """
        Was: success.yaml
        Now: PostgreSQL applications table with status='success'
        """
        try:
            await self.repos['application'].create(
                self.tenant_id,
                self.user_id,
                {
                    "vacancy_id": application_data.get("vacancy_id"),
                    "vacancy_url": application_data.get("vacancy_url"),
                    "company_name": application_data.get("company"),
                    "position_title": application_data.get("title"),
                    "status": "success",
                    "cover_letter": application_data.get("cover_letter")
                }
            )
            logger.info(f"Application saved: {application_data.get('vacancy_id')}")
        except Exception as e:
            logger.error(f"Failed to save application: {e}")

    async def save_failed(self, application_data: dict, error: str):
        """
        Was: failed.yaml
        Now: PostgreSQL with status='failed'
        """
        try:
            await self.repos['application'].create(
                self.tenant_id,
                self.user_id,
                {
                    "vacancy_id": application_data.get("vacancy_id"),
                    "vacancy_url": application_data.get("vacancy_url"),
                    "company_name": application_data.get("company"),
                    "position_title": application_data.get("title"),
                    "status": "failed",
                    "error_message": error
                }
            )
            logger.warning(f"Failed application saved: {application_data.get('vacancy_id')}")
        except Exception as e:
            logger.error(f"Failed to save failed application: {e}")

    async def save_skipped(self, application_data: dict):
        """
        Was: skipped.yaml
        Now: PostgreSQL with status='skipped'
        """
        try:
            await self.repos['application'].create(
                self.tenant_id,
                self.user_id,
                {
                    "vacancy_id": application_data.get("vacancy_id"),
                    "vacancy_url": application_data.get("vacancy_url"),
                    "company_name": application_data.get("company"),
                    "position_title": application_data.get("title"),
                    "status": "skipped"
                }
            )
            logger.debug(f"Skipped application saved: {application_data.get('vacancy_id')}")
        except Exception as e:
            logger.error(f"Failed to save skipped application: {e}")

    async def check_already_applied(self, vacancy_id: str) -> bool:
        """
        Was: check in YAML files
        Now: check in PostgreSQL
        """
        try:
            return await self.repos['application'].check_exists(
                self.tenant_id,
                self.user_id,
                vacancy_id
            )
        except Exception as e:
            logger.error(f"Failed to check application: {e}")
            return False
```

**Интеграция в существующий код:**

```python
# В job_applier.py или аналогичном файле

# БЫЛО (старый код):
with open("data_folder/output/success.yaml", 'a') as f:
    yaml.dump(application_data, f)

# СТАЛО (новый код - одна строка):
await self.storage_adapter.save_success(application_data)
```

---

### Шаг 4.2-4.5 - Repositories

Создаются repositories для всех сущностей:
- `user_repository.py` - users, HH credentials
- `search_config_repository.py` - search configs
- `browser_session_repository.py` - browser sessions
- `llm_cache_repository.py` - LLM cache

Аналогично `application_repository.py` из Фазы 1.

---

## ФАЗА 5: Browser Pool и Worker

### Шаг 5.1 - Browser Pool Manager

**Файл:** `src/browser/pool.py`

```python
import asyncio
from playwright.async_api import async_playwright, Browser
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class BrowserPool:
    """
    Browser pool для эффективного использования ресурсов

    Вместо создания нового браузера для каждого тенанта,
    используем пул из N браузеров, которые переиспользуются.
    """

    def __init__(self, size: int = 5, headless: bool = True):
        self.size = size
        self.headless = headless
        self.browsers: List[Browser] = []
        self.available: asyncio.Queue[Browser] = asyncio.Queue()
        self._initialized = False
        self.playwright = None

    async def initialize(self):
        """Initialize browser pool"""
        if self._initialized:
            return

        logger.info(f"Initializing browser pool (size={self.size}, headless={self.headless})")

        self.playwright = await async_playwright().start()

        for i in range(self.size):
            browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            self.browsers.append(browser)
            await self.available.put(browser)
            logger.info(f"Browser {i+1}/{self.size} initialized")

        self._initialized = True
        logger.info("Browser pool ready")

    async def acquire(self, timeout: float = 60.0) -> Browser:
        """
        Get browser from pool (blocking if all busy)

        Если все браузеры заняты, ждет освобождения.
        Timeout - максимальное время ожидания.
        """
        try:
            browser = await asyncio.wait_for(
                self.available.get(),
                timeout=timeout
            )
            logger.debug(f"Browser acquired (available: {self.available.qsize()}/{self.size})")
            return browser
        except asyncio.TimeoutError:
            raise Exception(f"Timeout waiting for available browser after {timeout}s")

    async def release(self, browser: Browser):
        """Return browser to pool"""
        await self.available.put(browser)
        logger.debug(f"Browser released (available: {self.available.qsize()}/{self.size})")

    async def close_all(self):
        """Close all browsers in pool"""
        logger.info("Closing all browsers in pool")
        for browser in self.browsers:
            await browser.close()

        if self.playwright:
            await self.playwright.stop()

        self._initialized = False
        logger.info("Browser pool closed")

    def get_stats(self) -> dict:
        """Get pool statistics"""
        available_count = self.available.qsize()
        busy_count = self.size - available_count

        return {
            "total": self.size,
            "available": available_count,
            "busy": busy_count,
            "utilization": (busy_count / self.size * 100) if self.size > 0 else 0
        }
```

---

### Шаг 5.2 - Task Queue с ID Generation и Tracking

**Файл:** `src/queue/task_queue.py`

```python
import json
import uuid
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TaskQueue:
    """
    Task queue с FIFO и ID tracking

    - Генерирует уникальный task_id при enqueue
    - Генерирует уникальный result_id при публикации результата
    - Поддерживает двунаправленную связь task_id ↔ result_id
    - FIFO гарантии через Redis LISTS (LPUSH/BRPOP)
    """

    TASKS_PENDING = "tasks:pending"
    RESULTS_COMPLETED = "results:completed"
    RESULTS_FAILED = "results:failed"
    TASKS_PROCESSING = "tasks:processing"

    def __init__(self, redis_client, worker_id: str = None):
        self.redis = redis_client
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"

    async def enqueue_task(
        self,
        tenant_id: str,
        user_id: str,
        task_type: str = "job_search_and_apply"
    ) -> str:
        """
        Создает задачу с уникальным task_id и добавляет в FIFO

        Returns:
            task_id (str): UUID v4 для отслеживания
        """
        task_id = str(uuid.uuid4())  # ✅ Генерация уникального ID

        task_data = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "type": task_type,
            "created_at": datetime.utcnow().isoformat()
        }

        # Добавление в FIFO очередь (LPUSH = добавление в начало)
        await self.redis.client.lpush(
            self.TASKS_PENDING,
            json.dumps(task_data)
        )

        # Сохранение метаданных с TTL 24 часа
        await self.redis.client.setex(
            f"task:{task_id}:status",
            86400,
            "pending"
        )
        await self.redis.client.setex(
            f"task:{task_id}:data",
            86400,
            json.dumps(task_data)
        )

        logger.info(f"Task enqueued: {task_id} (tenant={tenant_id}, user={user_id})")

        return task_id  # ✅ Возвращаем ID клиенту

    async def dequeue_task(self, timeout: int = 5) -> Optional[dict]:
        """
        Извлекает задачу из FIFO очереди (блокирующее чтение)

        Args:
            timeout: Максимальное время ожидания в секундах

        Returns:
            task_data с task_id или None если очередь пуста
        """
        # BRPOP = блокирующее извлечение с конца (FIFO порядок)
        result = await self.redis.client.brpop(self.TASKS_PENDING, timeout=timeout)

        if result:
            _, task_json = result
            task_data = json.loads(task_json)
            task_id = task_data["task_id"]

            # Обновление статуса на "processing"
            await self.redis.client.setex(
                f"task:{task_id}:status",
                86400,
                "processing"
            )

            # Сохранение метаданных о worker'е
            await self.redis.client.hset(
                self.TASKS_PROCESSING,
                task_id,
                json.dumps({
                    "worker_id": self.worker_id,
                    "started_at": datetime.utcnow().isoformat()
                })
            )

            logger.info(f"Task dequeued: {task_id} by worker {self.worker_id}")
            return task_data

        return None

    async def publish_result(
        self,
        task_id: str,
        result_data: dict,
        status: str = "success"
    ):
        """
        Публикует результат с новым result_id в FIFO очередь

        Args:
            task_id: ID исходной задачи
            result_data: Данные результата
            status: "success" или "failed"
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
        await self.redis.client.lpush(queue, json.dumps(output))

        # Обновление метаданных
        await self.redis.client.setex(
            f"task:{task_id}:status",
            86400,
            "completed" if status == "success" else "failed"
        )

        # ✅ Двунаправленная связь task_id ↔ result_id
        await self.redis.client.setex(
            f"task:{task_id}:result_id",
            86400,
            result_id
        )
        await self.redis.client.setex(
            f"result:{result_id}:task_id",
            86400,
            task_id
        )

        # Удаление из списка обрабатываемых
        await self.redis.client.hdel(self.TASKS_PROCESSING, task_id)

        logger.info(
            f"Result published: result_id={result_id}, "
            f"task_id={task_id}, status={status}"
        )

    async def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Получает статус задачи по ID

        Returns:
            "pending" | "processing" | "completed" | "failed" | None
        """
        status = await self.redis.client.get(f"task:{task_id}:status")
        return status.decode() if status else None

    async def get_result_id(self, task_id: str) -> Optional[str]:
        """
        Получает result_id по task_id

        Returns:
            result_id или None если задача не завершена
        """
        result_id = await self.redis.client.get(f"task:{task_id}:result_id")
        return result_id.decode() if result_id else None

    async def get_task_id(self, result_id: str) -> Optional[str]:
        """
        Получает task_id по result_id (обратная связь)

        Returns:
            task_id или None
        """
        task_id = await self.redis.client.get(f"result:{result_id}:task_id")
        return task_id.decode() if task_id else None

    async def consume_result(
        self,
        queue: str = "completed",
        timeout: int = 5
    ) -> Optional[dict]:
        """
        Читает результат из FIFO очереди (блокирующее чтение)

        Args:
            queue: "completed" или "failed"
            timeout: Максимальное время ожидания

        Returns:
            result_data с task_id и result_id или None
        """
        queue_key = (
            self.RESULTS_COMPLETED
            if queue == "completed"
            else self.RESULTS_FAILED
        )

        result = await self.redis.client.brpop(queue_key, timeout=timeout)

        if result:
            _, result_json = result
            result_data = json.loads(result_json)

            logger.info(
                f"Result consumed: result_id={result_data['result_id']}, "
                f"task_id={result_data['task_id']}"
            )
            return result_data

        return None

    async def get_queue_stats(self) -> dict:
        """Получает статистику очередей"""
        return {
            "tasks_pending": await self.redis.client.llen(self.TASKS_PENDING),
            "tasks_processing": await self.redis.client.hlen(self.TASKS_PROCESSING),
            "results_completed": await self.redis.client.llen(self.RESULTS_COMPLETED),
            "results_failed": await self.redis.client.llen(self.RESULTS_FAILED)
        }
```

---

### Шаг 5.3 - Worker

**Файл:** `src/workers/browser_worker.py`

```python
import asyncio
import logging
from datetime import datetime
from src.browser.pool import BrowserPool
from src.queue.task_queue import TaskQueue
from src.adapters.storage_adapter import StorageAdapter

logger = logging.getLogger(__name__)

class BrowserWorker:
    """
    Worker для обработки задач из Redis очереди

    Получает задачи, выполняет их используя существующую Python логику,
    сохраняет результаты в PostgreSQL.
    """

    def __init__(
        self,
        worker_id: str,
        browser_pool: BrowserPool,
        task_queue: TaskQueue,
        db_manager,
        repositories: dict
    ):
        self.worker_id = worker_id
        self.browser_pool = browser_pool
        self.task_queue = task_queue
        self.db = db_manager
        self.repos = repositories
        self._running = False

    async def start(self):
        """Start worker loop"""
        self._running = True
        logger.info(f"Worker {self.worker_id} started")

        while self._running:
            try:
                # Get next task from queue
                task = await self.task_queue.dequeue(timeout=5)

                if not task:
                    # No tasks available, continue loop
                    continue

                logger.info(f"Worker {self.worker_id} processing task {task['id']}")

                # Process task
                await self._process_task(task)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}", exc_info=True)
                await asyncio.sleep(5)

        logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self):
        """Stop worker"""
        self._running = False

    async def _process_task(self, task: dict):
        """
        Process single task

        Минимальные изменения существующего кода:
        - Получаем browser из pool
        - Создаем storage adapter
        - Запускаем существующую логику
        - Возвращаем browser в pool
        """
        tenant_id = task["tenant_id"]
        user_id = task["user_id"]
        task_id = task["id"]

        browser = None
        context = None

        try:
            # Get browser from pool
            browser = await self.browser_pool.acquire()

            # Create browser context
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            # Create storage adapter
            storage = StorageAdapter(self.repos, tenant_id, user_id)

            # Run existing job search logic
            result = await self._run_job_search(
                context,
                tenant_id,
                user_id,
                storage
            )

            # Mark task as completed
            await self.task_queue.complete(task_id, result)

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self.task_queue.fail(task_id, str(e))

        finally:
            # Cleanup
            if context:
                await context.close()

            if browser:
                await self.browser_pool.release(browser)

    async def _run_job_search(
        self,
        context,
        tenant_id: str,
        user_id: str,
        storage: StorageAdapter
    ) -> dict:
        """
        Run existing Python job search logic

        ЗДЕСЬ МИНИМАЛЬНЫЕ ИЗМЕНЕНИЯ СУЩЕСТВУЮЩЕГО КОДА:
        1. Загружаем конфиги из БД (вместо YAML)
        2. Передаем storage adapter (вместо file writes)
        3. Остальная логика БЕЗ ИЗМЕНЕНИЙ
        """

        # 1. Load search config from DB
        search_config = await self._load_search_config(tenant_id, user_id)
        if not search_config:
            raise ValueError("No active search config found")

        # 2. Load HH credentials from DB
        hh_login, hh_password = await self._load_hh_credentials(tenant_id, user_id)
        if not hh_login or not hh_password:
            raise ValueError("HH credentials not found")

        # 3. Load browser session from DB
        session_state = await self._load_browser_session(tenant_id, user_id)

        # 4. Run existing bot logic
        # (здесь вызываем существующий код из main.py)
        # Передаем:
        # - context (Playwright)
        # - search_config (из БД)
        # - storage (вместо YAML)
        # - hh_login, hh_password

        # Заглушка для примера:
        applications_sent = 0
        # ... здесь будет вызов существующей логики

        # 5. Save browser session back to DB
        await self._save_browser_session(tenant_id, user_id, context)

        return {
            "status": "completed",
            "applications_sent": applications_sent,
            "completed_at": datetime.utcnow().isoformat()
        }

    async def _load_search_config(self, tenant_id: str, user_id: str) -> dict:
        """Load active search config from DB"""
        row = await self.repos['search_config'].get_active(tenant_id, user_id)
        return row['config'] if row else None

    async def _load_hh_credentials(self, tenant_id: str, user_id: str) -> tuple:
        """Load and decrypt HH credentials"""
        return await self.repos['user'].get_hh_credentials(tenant_id, user_id)

    async def _load_browser_session(self, tenant_id: str, user_id: str) -> dict:
        """Load browser session state"""
        return await self.repos['browser_session'].get_session(tenant_id, user_id)

    async def _save_browser_session(self, tenant_id: str, user_id: str, context):
        """Save browser session state"""
        state = await context.storage_state()
        await self.repos['browser_session'].save_session(tenant_id, user_id, state)
```

---

### Шаг 5.4 - Dependency Injection

**Файл:** `src/container.py`

```python
from src.database.connection import DatabaseManager
from src.queue.redis_client import RedisClient
from src.browser.pool import BrowserPool
from src.queue.task_queue import TaskQueue
from src.repositories.application_repository import ApplicationRepository
from src.repositories.user_repository import UserRepository
from src.repositories.search_config_repository import SearchConfigRepository
from src.repositories.browser_session_repository import BrowserSessionRepository
from src.repositories.llm_cache_repository import LLMCacheRepository

class Container:
    """Dependency injection container"""

    def __init__(self, config):
        self.config = config

        # Infrastructure
        self.db = DatabaseManager(config.DATABASE_URL)
        self.redis = RedisClient(config.REDIS_URL)
        self.browser_pool = BrowserPool(
            size=config.BROWSER_POOL_SIZE,
            headless=config.BROWSER_HEADLESS
        )

        # Queues
        self.task_queue = TaskQueue(self.redis)

        # Repositories
        self.repositories = {
            'application': ApplicationRepository(self.db),
            'user': UserRepository(self.db),
            'search_config': SearchConfigRepository(self.db),
            'browser_session': BrowserSessionRepository(self.db),
            'llm_cache': LLMCacheRepository(self.db)
        }

    async def initialize(self):
        """Initialize all components"""
        await self.db.connect()
        await self.redis.connect()
        await self.browser_pool.initialize()

    async def close(self):
        """Close all connections"""
        await self.browser_pool.close_all()
        await self.redis.close()
        await self.db.close()
```

---

## ФАЗА 6: Docker

### Шаг 6.1 - Dockerfile.api (Minimal)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy only API code
COPY api/ ./api/
COPY src/monitoring/ ./src/monitoring/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Шаг 6.2 - Dockerfile.worker (with Playwright)

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

RUN apt-get update && \
    apt-get install -y build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Playwright
FROM python:3.11-slim as playwright

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget ca-certificates fonts-liberation \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libgbm1 libgtk-3-0 \
    libnss3 libxcomposite1 libxdamage1 libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

RUN playwright install chromium

# Stage 3: Final
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ca-certificates fonts-liberation libasound2 \
    libatk-bridge2.0-0 libgtk-3-0 libnss3 \
    libxcomposite1 libxdamage1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=playwright /opt/venv /opt/venv
COPY --from=playwright /root/.cache/ms-playwright /home/worker/.cache/ms-playwright

ENV PATH="/opt/venv/bin:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH=/home/worker/.cache/ms-playwright

WORKDIR /app
COPY . .

RUN groupadd -r worker && useradd -r -g worker worker
RUN chown -R worker:worker /app /home/worker

USER worker

CMD ["python", "-m", "src.workers.browser_worker"]
```

---

### Шаг 6.3 - docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: autoapplyer-postgres
    environment:
      POSTGRES_DB: autoapplyer
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - autoapplyer-network

  redis:
    image: redis:7-alpine
    container_name: autoapplyer-redis
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - autoapplyer-network

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: autoapplyer-api
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/autoapplyer
      REDIS_URL: redis://redis:6379
      BROWSER_POOL_SIZE: 5
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - autoapplyer-network
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/autoapplyer
      REDIS_URL: redis://redis:6379
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      BROWSER_HEADLESS: true
      BROWSER_POOL_SIZE: 5
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - autoapplyer-network
    restart: unless-stopped
    deploy:
      replicas: 3

  cli:
    build:
      context: .
      dockerfile: Dockerfile.worker
    container_name: autoapplyer-cli
    entrypoint: ["/bin/bash"]
    stdin_open: true
    tty: true
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/autoapplyer
      REDIS_URL: redis://redis:6379
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
    volumes:
      - ./scripts:/app/scripts
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - autoapplyer-network

volumes:
  postgres-data:
  redis-data:

networks:
  autoapplyer-network:
    driver: bridge
```

**Использование CLI через Docker:**

```bash
# Создать тенанта
docker compose run --rm cli python scripts/create_tenant.py "Company A" "company-a"

# Создать пользователя
docker compose run --rm cli python scripts/create_user.py <tenant_id> user@example.com

# Загрузить конфиг
docker compose run --rm cli python scripts/load_search_config.py <tenant_id> <user_id> search_config.yaml

# Запустить задачу
docker compose run --rm cli python scripts/enqueue_job.py <tenant_id> <user_id>

# Посмотреть результаты
docker compose run --rm cli python scripts/view_applications.py <tenant_id> <user_id>
```

---

### Шаг 6.4 - .dockerignore

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
ENV/

.pytest_cache/
.coverage
htmlcov/
*.log

.vscode/
.idea/
*.swp

.git/
.gitignore
.github/

data_folder/output/
data_folder/browser_session/
*.yaml
!requirements*.yaml

README.md
docs/
*.md

docker-compose*.yml
Dockerfile*
.dockerignore
```

---

## ФАЗА 7: CI/CD

### Шаг 7.1 - GitHub Actions: Tests

**Файл:** `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Install Playwright
        run: |
          playwright install chromium
          playwright install-deps chromium

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
        run: |
          alembic upgrade head

      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
          ENCRYPTION_KEY: test-encryption-key-32-bytes!!
          BROWSER_HEADLESS: true
        run: |
          pytest tests/unit -v --cov=src --cov-report=xml --cov-report=html

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
          ENCRYPTION_KEY: test-encryption-key-32-bytes!!
          BROWSER_HEADLESS: true
        run: |
          pytest tests/integration -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: unittests

      - name: Lint with ruff
        run: |
          ruff check src/ api/ scripts/

      - name: Type check with mypy
        run: |
          mypy src/ api/
```

---

### Шаг 7.2 - GitHub Actions: Docker Build

**Файл:** `.github/workflows/docker-build.yml`

```yaml
name: Docker Build and Push

on:
  push:
    branches: [main]
    tags: ['v*']
  release:
    types: [published]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME_API: ${{ github.repository }}/api
  IMAGE_NAME_WORKER: ${{ github.repository }}/worker

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata for API
        id: meta-api
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME_API }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.api
          push: true
          tags: ${{ steps.meta-api.outputs.tags }}
          labels: ${{ steps.meta-api.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Extract metadata for Worker
        id: meta-worker
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME_WORKER }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push Worker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.worker
          push: true
          tags: ${{ steps.meta-worker.outputs.tags }}
          labels: ${{ steps.meta-worker.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

### Шаг 7.3 - Deployment Automation

**Файл:** `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /app/autoapplyer

            # Pull latest images
            docker compose pull

            # Run migrations
            docker compose run --rm cli alembic upgrade head

            # Restart services
            docker compose up -d --no-deps api worker

            # Health check
            sleep 10
            curl -f http://localhost:8000/health || exit 1

            # Cleanup
            docker image prune -f

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: |
            Deployment to ${{ github.event.inputs.environment }}
            Status: ${{ job.status }}
            Commit: ${{ github.sha }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

### Шаг 7.4 - Environment Configuration

**Файл:** `.env.example`

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autoapplyer

# Redis
REDIS_URL=redis://localhost:6379

# Security
ENCRYPTION_KEY=your-fernet-encryption-key-here

# Browser Pool
BROWSER_POOL_SIZE=5
BROWSER_HEADLESS=true

# Logging
LOG_LEVEL=INFO
```

**Файл:** `scripts/generate_encryption_key.py`

```python
#!/usr/bin/env python3
from cryptography.fernet import Fernet

# Generate new Fernet key
key = Fernet.generate_key()
print(f"ENCRYPTION_KEY={key.decode()}")
```

---

## ФАЗА 8: Тестирование

### Шаг 8.1 - Unit Tests

**Файл:** `tests/unit/test_storage_adapter.py`

```python
import pytest
from src.adapters.storage_adapter import StorageAdapter

@pytest.mark.asyncio
async def test_save_success(mock_repos):
    adapter = StorageAdapter(mock_repos, "tenant1", "user1")

    data = {
        "vacancy_id": "123",
        "company": "Test Company",
        "title": "Python Developer"
    }

    await adapter.save_success(data)

    # Verify repository was called
    assert mock_repos['application'].create.called
```

---

### Шаг 8.2 - Integration Tests

**Файл:** `tests/integration/test_worker.py`

```python
import pytest
from src.workers.browser_worker import BrowserWorker

@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_processes_task(test_db, test_redis, browser_pool):
    # Enqueue test task
    task_id = await test_redis.enqueue({
        "id": "test-task-1",
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "job_search_and_apply"
    })

    # Run worker
    worker = BrowserWorker("worker1", browser_pool, test_redis, test_db, {})
    await worker._process_task(task)

    # Verify result
    result = await test_redis.get_result(task_id)
    assert result["status"] == "completed"
```

---

### Шаг 8.3 - E2E Tests

**Файл:** `tests/e2e/test_full_flow.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_job_search_flow():
    """Test complete flow: enqueue → worker → database"""

    # 1. Setup tenant/user
    tenant_id = await create_test_tenant()
    user_id = await create_test_user(tenant_id)

    # 2. Load config
    await load_test_config(tenant_id, user_id)

    # 3. Enqueue task
    task_id = await enqueue_test_task(tenant_id, user_id)

    # 4. Wait for completion
    result = await wait_for_result(task_id, timeout=60)

    # 5. Verify applications in DB
    apps = await get_applications(tenant_id, user_id)
    assert len(apps) > 0
```

---

### Шаг 8.4 - Load Testing

**Файл:** `tests/load/locustfile.py`

```python
from locust import HttpUser, task, between

class MonitoringUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def check_health(self):
        self.client.get("/health")

    @task(2)
    def check_pool_status(self):
        self.client.get("/pool/status")

    @task(1)
    def check_queue_stats(self):
        self.client.get("/queue/stats")
```

**Запуск:**
```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
```

---

## ФАЗА 9: Миграция данных

### Шаг 9.1 - Скрипт миграции YAML → PostgreSQL

**Файл:** `scripts/migrate_yaml_to_db.py`

```python
#!/usr/bin/env python3
import asyncio
import asyncpg
import yaml
import json
from pathlib import Path

async def migrate_applications(tenant_id: str, user_id: str, db_url: str):
    """Migrate applications from YAML to PostgreSQL"""

    conn = await asyncpg.connect(db_url)

    try:
        # Migrate success.yaml
        success_file = Path("data_folder/output/success.yaml")
        if success_file.exists():
            with open(success_file) as f:
                applications = yaml.safe_load(f) or []

            for app in applications:
                await conn.execute("""
                    INSERT INTO applications (tenant_id, user_id, vacancy_id, status)
                    VALUES ($1, $2, $3, 'success')
                    ON CONFLICT DO NOTHING
                """, tenant_id, user_id, app.get("vacancy_id"))

            print(f"✅ Migrated {len(applications)} successful applications")

        # Migrate failed.yaml
        failed_file = Path("data_folder/output/failed.yaml")
        if failed_file.exists():
            with open(failed_file) as f:
                applications = yaml.safe_load(f) or []

            for app in applications:
                await conn.execute("""
                    INSERT INTO applications (tenant_id, user_id, vacancy_id, status)
                    VALUES ($1, $2, $3, 'failed')
                    ON CONFLICT DO NOTHING
                """, tenant_id, user_id, app.get("vacancy_id"))

            print(f"✅ Migrated {len(applications)} failed applications")

        # Migrate skipped.yaml
        skipped_file = Path("data_folder/output/skipped.yaml")
        if skipped_file.exists():
            with open(skipped_file) as f:
                applications = yaml.safe_load(f) or []

            for app in applications:
                await conn.execute("""
                    INSERT INTO applications (tenant_id, user_id, vacancy_id, status)
                    VALUES ($1, $2, $3, 'skipped')
                    ON CONFLICT DO NOTHING
                """, tenant_id, user_id, app.get("vacancy_id"))

            print(f"✅ Migrated {len(applications)} skipped applications")

    finally:
        await conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python migrate_yaml_to_db.py <tenant_id> <user_id>")
        sys.exit(1)

    asyncio.run(migrate_applications(sys.argv[1], sys.argv[2], "postgresql://..."))
```

---

### Шаг 9.2 - Верификация

**Файл:** `scripts/verify_migration.py`

```python
#!/usr/bin/env python3
import asyncio
import asyncpg

async def verify_migration(tenant_id: str, user_id: str, db_url: str):
    """Verify data migration"""

    conn = await asyncpg.connect(db_url)

    try:
        # Count applications
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM applications
            WHERE tenant_id = $1 AND user_id = $2
        """, tenant_id, user_id)

        print(f"📊 Total applications: {count}")

        # Stats by status
        stats = await conn.fetch("""
            SELECT status, COUNT(*) as cnt
            FROM applications
            WHERE tenant_id = $1 AND user_id = $2
            GROUP BY status
        """, tenant_id, user_id)

        for row in stats:
            print(f"   {row['status']}: {row['cnt']}")

    finally:
        await conn.close()
```

---

## Итоговая структура проекта

```
project/
├── .github/
│   └── workflows/
│       ├── test.yml
│       ├── docker-build.yml
│       └── deploy.yml
│
├── api/
│   └── main.py                    # Minimal FastAPI (health/metrics only)
│
├── src/
│   ├── database/
│   │   └── connection.py
│   ├── queue/
│   │   ├── redis_client.py
│   │   └── task_queue.py
│   ├── browser/
│   │   └── pool.py
│   ├── repositories/
│   │   ├── base.py
│   │   ├── application_repository.py
│   │   ├── user_repository.py
│   │   ├── search_config_repository.py
│   │   ├── browser_session_repository.py
│   │   └── llm_cache_repository.py
│   ├── adapters/
│   │   └── storage_adapter.py    # Wrapper над YAML логикой
│   ├── workers/
│   │   └── browser_worker.py     # Worker для обработки задач
│   ├── monitoring/
│   │   └── metrics.py
│   ├── container.py               # DI container
│   └── [existing code - minimal changes]
│       ├── job_manager/
│       ├── resume/
│       ├── llm/
│       └── utils/
│
├── scripts/
│   ├── create_tenant.py           # CLI: создание тенанта
│   ├── create_user.py             # CLI: создание пользователя
│   ├── load_search_config.py      # CLI: загрузка конфига
│   ├── enqueue_job.py             # CLI: запуск задачи
│   ├── view_applications.py       # CLI: просмотр результатов
│   ├── migrate_yaml_to_db.py      # Миграция данных
│   └── verify_migration.py        # Верификация миграции
│
├── alembic/
│   ├── versions/
│   │   ├── 001_create_tenants.py
│   │   ├── 002_create_users.py
│   │   ├── 003_create_applications.py
│   │   ├── 004_create_browser_sessions.py
│   │   ├── 005_create_search_configs.py
│   │   ├── 006_create_llm_cache.py
│   │   └── 007_create_job_tasks.py
│   └── env.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── load/
│
├── Dockerfile.api                 # Minimal API
├── Dockerfile.worker              # Worker с Playwright
├── docker-compose.yml             # Полный стек
├── .dockerignore
├── .env.example
├── requirements.txt
├── requirements-api.txt
├── requirements-dev.txt
└── alembic.ini
```

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────┐
│                  CLI Scripts (Management)                    │
│  create_tenant | create_user | load_config | enqueue_job    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                      Redis Queue                             │
│              browser:tasks:pending (LIST)                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ (dequeue)
┌─────────────────────────────────────────────────────────────┐
│                Worker Pool (3 replicas)                      │
│    Worker 1  |  Worker 2  |  Worker 3                        │
│         ↓            ↓            ↓                           │
│      Browser Pool (5 browsers shared)                        │
│         ↓            ↓            ↓                           │
│   Existing Python Logic (minimal changes)                    │
│         ↓            ↓            ↓                           │
│    Storage Adapter → PostgreSQL                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│             Minimal API (port 8000)                          │
│  /health | /metrics | /pool/status | /queue/stats           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL                                │
│  tenants | users | applications | sessions | configs | cache │
└─────────────────────────────────────────────────────────────┘
```

---

## Ключевые изменения в существующем коде

**МИНИМАЛЬНЫЕ изменения - только injection точки:**

### 1. Вместо YAML файлов:

```python
# БЫЛО (старый код):
with open("data_folder/output/success.yaml", 'a') as f:
    yaml.dump(application_data, f)

# СТАЛО (новый код):
await storage_adapter.save_success(application_data)
```

### 2. Загрузка конфигов:

```python
# БЫЛО:
with open("data_folder/search_config/search_config.yaml") as f:
    config = yaml.safe_load(f)

# СТАЛО:
config = await config_repo.get_active(tenant_id, user_id)
```

### 3. HH credentials:

```python
# БЫЛО:
with open("data_folder/secrets/secrets.yaml") as f:
    secrets = yaml.safe_load(f)
hh_login = secrets["hh_login"]
hh_password = secrets["hh_password"]

# СТАЛО:
hh_login, hh_password = await user_repo.get_hh_credentials(tenant_id, user_id)
```

### 4. Browser session:

```python
# БЫЛО:
storage_state = "data_folder/browser_session/hh_state.json"

# СТАЛО:
storage_state = await session_repo.get_session(tenant_id, user_id)
```

**Вся остальная логика (Playwright, LLM, job apply) остается БЕЗ ИЗМЕНЕНИЙ.**

---

## 📋 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ CLI С ID TRACKING

### 1. Создание тенанта и пользователя

```bash
# Создать тенанта
$ python scripts/create_tenant.py "Company A" "company-a"

✅ Tenant created: tenant-123
   Name: Company A
   Slug: company-a

# Создать пользователя
$ python scripts/create_user.py tenant-123 user@company-a.com "John Doe" hh_login hh_password

✅ User created: user-456
   Email: user@company-a.com
   HH Login: hh_login
```

### 2. Загрузка search config

```bash
$ python scripts/load_search_config.py tenant-123 user-456 search_config.yaml

✅ Config loaded: config-789
   Job title: Python Developer
   Max applies: 50
```

### 3. Отправка задачи (получение task_id)

```bash
$ python scripts/enqueue_job.py tenant-123 user-456

✅ Task enqueued successfully!
   Task ID: 550e8400-e29b-41d4-a716-446655440000  ← Сохраните для мониторинга
   Status: pending

   Monitor with:
   python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000

   Or via API:
   curl http://localhost:8000/task/550e8400-e29b-41d4-a716-446655440000/status
```

### 4. Мониторинг статуса по task_id

```bash
$ python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000

📊 Task Status:
   Task ID: 550e8400-e29b-41d4-a716-446655440000
   Status: processing ⏳
   Started: 2024-01-15T10:30:05Z
   Worker: worker-1

# Через несколько минут
$ python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000

📊 Task Status:
   Task ID: 550e8400-e29b-41d4-a716-446655440000
   Status: completed ✅
   Result ID: 661f9511-f3ac-52e5-b827-557766551111  ← Новый ID результата
   Created: 2024-01-15T10:30:00Z
   Completed: 2024-01-15T10:45:00Z
   Duration: 15 minutes
```

### 5. Чтение результатов из FIFO (получение result_id)

#### Вариант A: Блокирующий режим (ожидание результата)

```bash
$ python scripts/consume_results.py --mode completed --timeout 300

Waiting for results (timeout: 300s)...

📦 Result received:
   Result ID: 661f9511-f3ac-52e5-b827-557766551111  ← ID результата
   Task ID: 550e8400-e29b-41d4-a716-446655440000    ← Связь с задачей
   Status: success

   Data:
   ├─ Applications sent: 15
   ├─ Vacancies processed: 50
   ├─ Skipped: 12
   ├─ Failed: 3
   └─ Duration: 15 minutes

   Details saved to PostgreSQL
```

#### Вариант B: Пакетное чтение (несколько результатов)

```bash
$ python scripts/consume_results.py --mode completed --batch 10

📦 Reading up to 10 results...

Result 1/3:
   Result ID: 661f9511-f3ac-52e5-b827-557766551111
   Task ID: 550e8400-e29b-41d4-a716-446655440000
   Applications: 15

Result 2/3:
   Result ID: 772fa622-g4bd-63f6-c938-668877662222
   Task ID: 883gb733-h5ce-74g7-d049-779988773333
   Applications: 8

Result 3/3:
   Result ID: 994hc844-i6df-85h8-e150-880099884444
   Task ID: 115id955-j7eg-96i9-f261-991100995555
   Applications: 22

✅ Total: 3 results processed
```

#### Вариант C: Чтение ошибок

```bash
$ python scripts/consume_results.py --mode failed --timeout 60

📦 Result received:
   Result ID: aabbccdd-1122-3344-5566-778899aabbcc
   Task ID: ffeeddcc-9988-7766-5544-332211ffeedd
   Status: failed

   Error: Browser session expired after 3 reconnection attempts
   Failed at: 2024-01-15T10:35:42Z

   Details saved to PostgreSQL for debugging
```

### 6. Просмотр результатов из PostgreSQL

```bash
$ python scripts/view_applications.py tenant-123 user-456 --last 50

┌────────────┬──────────────────┬──────────────────┬─────────┬─────────────────────┐
│ Task ID    │ Company          │ Position         │ Status  │ Applied At          │
├────────────┼──────────────────┼──────────────────┼─────────┼─────────────────────┤
│ 550e8400...│ Google           │ Python Developer │ success │ 2024-01-15 10:45:00 │
│ 550e8400...│ Meta             │ Backend Engineer │ success │ 2024-01-15 10:43:12 │
│ 550e8400...│ Amazon           │ SDE II           │ skipped │ 2024-01-15 10:41:55 │
│ 550e8400...│ Netflix          │ Sr. Developer    │ success │ 2024-01-15 10:40:33 │
└────────────┴──────────────────┴──────────────────┴─────────┴─────────────────────┘

📊 Stats:
   Task ID: 550e8400-e29b-41d4-a716-446655440000
   Success: 15
   Failed: 3
   Skipped: 12
   Total: 30
```

### 7. Использование API endpoints

#### Проверка статуса по task_id

```bash
$ curl http://localhost:8000/task/550e8400-e29b-41d4-a716-446655440000/status

{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result_id": "661f9511-f3ac-52e5-b827-557766551111",
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:00Z",
  "duration_seconds": 900
}
```

#### Получение данных результата по result_id

```bash
$ curl http://localhost:8000/result/661f9511-f3ac-52e5-b827-557766551111

{
  "result_id": "661f9511-f3ac-52e5-b827-557766551111",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "data": {
    "applications_sent": 15,
    "vacancies_processed": 50,
    "skipped": 12,
    "failed": 3
  },
  "completed_at": "2024-01-15T10:45:00Z"
}
```

#### Обратная связь: найти task_id по result_id

```bash
$ curl http://localhost:8000/result/661f9511-f3ac-52e5-b827-557766551111/task

{
  "result_id": "661f9511-f3ac-52e5-b827-557766551111",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"  ← Обратная связь
}
```

#### Статистика очередей

```bash
$ curl http://localhost:8000/queue/stats

{
  "tasks_pending": 5,
  "tasks_processing": 2,
  "results_completed": 12,
  "results_failed": 1,
  "pool": {
    "total": 5,
    "available": 3,
    "busy": 2,
    "utilization": 40.0
  }
}
```

### 8. Полный цикл работы (от создания до результата)

```bash
# 1. Создание инфраструктуры (один раз)
python scripts/create_tenant.py "Company A" "company-a"
# → tenant_id: tenant-123

python scripts/create_user.py tenant-123 john@company-a.com "John Doe" hh_login hh_pass
# → user_id: user-456

# 2. Загрузка конфигурации
python scripts/load_search_config.py tenant-123 user-456 search_config.yaml
# → config_id: config-789

# 3. Отправка задачи
python scripts/enqueue_job.py tenant-123 user-456
# → task_id: 550e8400-e29b-41d4-a716-446655440000 ✅ Сохранить!

# 4. Мониторинг (опционально)
python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000
# → Status: processing → completed
# → result_id: 661f9511-f3ac-52e5-b827-557766551111 ✅ Получен!

# 5. Получение результата
python scripts/consume_results.py --mode completed --timeout 60
# → Получен результат с result_id и task_id
# → Данные: 15 applications sent

# 6. Просмотр деталей в БД
python scripts/view_applications.py tenant-123 user-456
# → Таблица со всеми заявками по task_id
```

### 9. Автоматизация через cron

```bash
# Ежедневная отправка задач в 9:00
0 9 * * * python /app/scripts/enqueue_job.py tenant-123 user-456 >> /var/log/enqueue.log 2>&1

# Чтение результатов каждые 15 минут
*/15 * * * * python /app/scripts/consume_results.py --mode completed --batch 10 >> /var/log/results.log 2>&1

# Проверка ошибок каждый час
0 * * * * python /app/scripts/consume_results.py --mode failed --batch 5 >> /var/log/errors.log 2>&1
```

### 10. Docker Compose использование

```bash
# Запуск всего стека
docker compose up -d

# Проверка логов worker'а
docker compose logs -f worker

# Создание тенанта через CLI контейнер
docker compose run --rm cli python scripts/create_tenant.py "Company A" "company-a"

# Отправка задачи
docker compose run --rm cli python scripts/enqueue_job.py tenant-123 user-456

# Мониторинг
docker compose run --rm cli python scripts/monitor_task.py 550e8400-e29b-41d4-a716-446655440000

# Чтение результатов
docker compose run --rm cli python scripts/consume_results.py --mode completed --timeout 60

# Остановка
docker compose down
```

---

## Время выполнения

| Фаза | Описание | Время |
|------|----------|-------|
| 1 | Инфраструктура (БД, Redis) | 4-5ч |
| 2 | CLI Scripts | 2-3ч |
| 3 | Minimal API | 1-2ч |
| 4 | Адаптеры хранилища | 5-6ч |
| 5 | Browser Pool & Worker | 6-8ч |
| 6 | Docker | 4-5ч |
| 7 | CI/CD | 3-4ч |
| 8 | Тесты | 4-5ч |
| 9 | Миграция | 2-3ч |

**Общее время: 31-41 час (~1 неделя активной разработки)**

---

## Приоритеты реализации

**Критичные (для MVP):**
1. ✅ Фаза 1 - Инфраструктура
2. ✅ Фаза 2 - CLI Scripts
3. ✅ Фаза 4 - Адаптеры
4. ✅ Фаза 5 - Worker & Pool
5. ✅ Фаза 6 - Docker

**Важные:**
6. ✅ Фаза 3 - Minimal API
7. ✅ Фаза 8 - Тестирование

**Опциональные (можно позже):**
8. 🟡 Фаза 7 - CI/CD
9. 🟡 Фаза 9 - Миграция данных

---

## Готовность к старту

План готов! Можно начинать с Фазы 1: создание базовой инфраструктуры.