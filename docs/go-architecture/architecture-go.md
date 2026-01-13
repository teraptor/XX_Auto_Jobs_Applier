# Архитектура проекта XX Auto Jobs Applier (Go Implementation)

## Оглавление
1. [Обзор архитектуры](#обзор-архитектуры)
2. [Сравнение с Python версией](#сравнение-с-python-версией)
3. [Компоненты системы](#компоненты-системы)
4. [Схема архитектуры](#схема-архитектуры)
5. [Потоки данных](#потоки-данных)
6. [Модель данных](#модель-данных)
7. [Масштабирование](#масштабирование)
8. [Безопасность](#безопасность)
9. [Deployment](#deployment)
10. [Конфигурационные параметры](#конфигурационные-параметры)

---

## Обзор архитектуры

XX Auto Jobs Applier (Go) - это микросервисная архитектура с монолитным Core и распределёнными Workers для автоматизации поиска работы на hh.ru.

### Ключевые отличия от Python версии

| Аспект | Python (текущая) | Go (целевая) |
|--------|------------------|--------------|
| **Архитектура** | Монолит | Монолитный Core + распределённые Workers |
| **Пользователи** | Один локальный | Multi-tenant (10,000+ MAU) |
| **Масштабирование** | Вертикальное | Горизонтальное (workers) |
| **UI** | CLI | Web Frontend (Vue3) |
| **Хранение** | Локальные YAML файлы | PostgreSQL + Redis |
| **Монетизация** | Нет | Подписки через ЮКассу |
| **Deployment** | Локальная машина | Docker Compose |

### Технологический стек

**Backend:**
- **Core:** Go (ChiRouter)
- **Workers:** Go + Selenium (chromedp/rod)
- **Database:** PostgreSQL 15+
- **Cache/Queue:** Redis 7+
- **Message Broker:** Redis Streams/FIFO

**Frontend:**
- Vue.js (SPA)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- Prometheus + Grafana (мониторинг)

**External APIs:**
- hh.ru API (OAuth 2.0)
- LLM: Gemini, OpenAI, GigaChat
- Telegram Bot API
- ЮКасса API

---

## Сравнение с Python версией

### Миграция компонентов

| Python компонент | Go компонент | Примечания |
|------------------|--------------|------------|
| `main.py` | `core` service | API Gateway, Orchestrator |
| `JobApplier` | `hh.worker` | Распределённые воркеры |
| `ResumeScraper` | `core` service  (User module) | Централизованно в Core |
| `GPTAnswerer` | `core` service | Централизованно в Core |
| `HeadHunterAPI` | `hh.worker` (client) | В каждом воркере |
| `Authenticator` | `hh.worker` (selenium) | Chromedp/Rod |
| `BotFacade` | `core` service  (Orchestrator) | Координация задач |
| `TelegramManager` | `telegram` service | Централизованно в Core |
| `resume_builder` | `core` service  | Часть LLM сервиса |
| YAML файлы | PostgreSQL таблицы | Реляционная БД |
| `answers.yaml` | `llm_cache` таблица | С TTL |
| `success.yaml` | `applications` таблица | С full history |
---

## Компоненты системы

### 1. Frontend (Web UI)

**Технологии:** Vue.js + TypeScript

**Основные страницы:**

#### 1.1. Landing Page (`/`)
- Информация о сервисе
- Регистрация/вход

#### 1.2. Регистрация/Авторизация (`/auth`)
- Login/Password
- OAuth через Telegram
- OAuth через hh.ru
- 3-дневный триал автоматически после привязки карты

#### 1.3. Dashboard (`/dashboard`)
- Статистика откликов (сегодня, неделя, месяц)
- График активности
- Дата подписки
- Последние отклики
- Приглашения на собеседования (highlights)

#### 1.4. Настройка поиска (`/search-config`)
- Все параметры из `search_config.yaml`
- Ключевые слова, исключения
- География, зарплата, опыт
- Расписание (когда запускать)
- Лимиты (макс откликов/день)

#### 1.5. История откликов (`/applications`)
- Таблица всех откликов
- Фильтры (дата, компания, статус)
- Детали вакансии
- Сопроводительные письма
- История диалогов с HR

#### 1.6. Собеседования (`/interviews`)
- Назначенные собеседования
- Календарь
- Напоминания
- Сообщения от работодателей

#### 1.7. Вакансии (`/vacancies`)
- Рекомендованные вакансии по профилю
- Оценка соответствия (от LLM)

#### 1.8. Подписка (`/billing`)
- Текущий план (триал/1мес/2мес/3мес)
- Дата окончания
- Оплата через ЮКассу
- История платежей
- Остановка подписки

#### 1.9. Настройки (`/settings`)
- Резюме (загрузка/редактирование автоматически при oAuth hh.ru)
- Уведомления (Telegram)
- Интеграции (hh.ru токены)
- Безопасность

**API взаимодействие:**
```
Frontend <--REST/GraphQL--> Core API
Frontend <--WebSocket--> Core (real-time updates)
```

---

### 2. Core (Монолитный Go сервис)

**Ответственность:**
- API Gateway для Frontend
- User Management (регистрация, авторизация, сессии)
- Orchestrator (создание и распределение задач)
- Billing & Analytics
- Интеграция с внешними сервисами

**Модули Core:**

#### 2.1. API Gateway
```go
// HTTP REST API
GET    /api/v1/users/me
POST   /api/v1/auth/login
POST   /api/v1/auth/register
POST   /api/v1/auth/oauth/telegram
POST   /api/v1/auth/oauth/hh

GET    /api/v1/applications
POST   /api/v1/applications/:id/messages

GET    /api/v1/vacancies
GET    /api/v1/interviews

GET    /api/v1/search-config
PUT    /api/v1/search-config

POST   /api/v1/billing/subscribe
POST   /api/v1/billing/cancel
GET    /api/v1/billing/history

```

#### 2.2. User Management

**Функции:**
- Регистрация (email + password hash)
- OAuth интеграция (Telegram, hh.ru)
- JWT токены для аутентификации
- Управление подписками (trial → paid)
- Rate limiting на пользователя

**Структура:**
```go
type User struct {
    ID              int64
    Email           string
    PasswordHash    string
    TelegramID      *int64
    HHUserID        *string
    SubscriptionPlan string // "trial", "1month", "2month", "3month"
    SubscriptionEnd  time.Time
    TrialEnd        time.Time
    CreatedAt       time.Time
    IsActive        bool
}
```

#### 2.3. Orchestrator

**Задачи:**
1. Создание job для каждого активного пользователя
2. Проверка лимитов (не превышен ли дневной лимит откликов)
3. Помещение задач в Redis Queue
4. Мониторинг выполнения через `hh.scheduler`

**Режимы работы (настраиваются в конфигурации):**

| Режим | Описание | Использование |
|-------|----------|---------------|
| **Обычный режим** | LLM фильтрует вакансии (порог 70/100), отправляет отклики | Production для пользователей |
| **MONKEY_MODE** | Откликаемся на ВСЕ вакансии без фильтрации LLM | Тестирование, массовые отклики |
| **RESUME_MODE** | Генерация резюме под вакансию (HTML/PDF), без откликов | Создание резюме для портфолио |
| **COVER_LETTER_MODE** | Генерация сопроводительных писем, без откликов | Тестирование качества LLM |
| **SKILL_STAT_MODE** | Сбор статистики по навыкам из вакансий | Аналитика рынка труда |

**Параметры:**
- `JOB_IS_INTERESTING_THRESH = 70` - порог оценки LLM (0-100)
- `MINIMUM_WAIT_TIME_SEC = 10` - минимальное время между откликами
- `RAISE_RESUME = true` - поднимать резюме в поиске (не чаще 1 раз в 4 часа)

**Логика:**
```
Каждые N минут (настраиваемо):
1. Получить список активных пользователей (subscription не истекла)
2. Для каждого пользователя:
   a. Проверить search_config (расписание)
   b. Проверить лимиты (applications сегодня < max_applies_num)
   c. Создать Job { user_id, search_params, resume_data, mode }
   d. Поместить Job в Redis Queue
3. Логировать статистику
```

#### 2.4. Billing

**Функции:**
- Интеграция с ЮКасса API
- Создание платежей
- Webhook обработка (подтверждение оплаты)
- Продление подписки
- Отмена подписки (soft delete)
- Подсчёт расходов на LLM (для аналитики)

**Процесс оплаты:**
```
1. Пользователь выбирает тариф (1/2/3 месяца)
2. Core создаёт Payment в ЮКасса
3. Пользователь перенаправляется на страницу оплаты
4. ЮКасса отправляет webhook на /api/v1/billing/webhook
5. Core обновляет subscription_end в БД
6. Уведомление пользователю (email/telegram)
```

#### 2.5. Analytics

**Метрики:**
- Количество пользователей (всего, активных, trial, paid)
- Отклики (всего, успешных, пропущенных, failed)
- Расходы на LLM (по пользователям, по задачам)
- Загрузка workers
- Конверсия (trial → paid)

**Хранение:**
- PostgreSQL (детальные данные)
- Prometheus (метрики для графиков)

---

### 3. HH.Scheduler (Планировщик задач)

**Ответственность:**
- Чтение задач из Redis Queue (FIFO)
- Распределение задач между `hh.workers`
- Балансировка нагрузки
- Мониторинг состояния workers

**Алгоритм распределения:**
```
1. Получить Job из Redis Queue
2. Выбрать worker по критериям:
   - Минимальная нагрузка (активных задач)
   - Разный IP (для обхода rate limits hh.ru)
   - Доступность (healthcheck)
3. Отправить Job в очередь конкретного worker
4. Логировать назначение
```

**Структура Job:**
```go
type Job struct {
    ID             string
    UserID         int64
    SearchConfig   SearchConfig
    ResumeData     Resume
    MaxApplies     int
    CreatedAt      time.Time
    AssignedWorker string // IP воркера
    
    // Режимы работы
    MonkeyMode         bool   // Откликаться на все вакансии без фильтрации
    ResumeMode         bool   // Генерация резюме без откликов
    CoverLetterMode    bool   // Генерация писем без откликов
    SkillStatMode      bool   // Сбор статистики по навыкам
    
    // Параметры
    InterestThreshold  int    // Порог оценки LLM (по умолчанию 70)
    MinWaitTimeSec     int    // Минимальное время между откликами
    RaiseResume        bool   // Поднимать резюме в поиске
}
```

**Redis структура:**
```
Queue: jobs:pending (FIFO)
Queue: jobs:worker1 (задачи для worker 192.168.0.1)
Queue: jobs:worker2 (задачи для worker 192.168.0.2)
Queue: jobs:worker3 (задачи для worker 192.168.0.3)

Hash: workers:status
  - worker1: { ip: "192.168.0.1", active_jobs: 3, last_seen: timestamp }
  - worker2: { ip: "192.168.0.2", active_jobs: 1, last_seen: timestamp }
  - worker3: { ip: "192.168.0.3", active_jobs: 5, last_seen: timestamp }
```

---

### 4. HH.Worker (Распределённые воркеры)

**Количество:** Минимум 2, масштабируемо

**IP адреса:** Разные (192.168.0.1, 0.2, 0.3, ...) для обхода rate limits

**Ответственность:**
- Получение Job из своей Redis очереди
- Поиск вакансий через hh.ru API
- Обработка каждой вакансии
- Сохранение результатов в БД
- Отчёт о выполнении

**Технологии:**
- Go + chromedp/rod (Selenium аналог)
- HTTP client для hh.ru API
- gRPC/HTTP client для LLM сервиса

**Процесс обработки вакансии:**

```
1. Получить список вакансий (hh.ru API /vacancies)
2. Для каждой вакансии:
   
   a. Проверка дубликатов
      - Запрос в БД: applications WHERE user_id AND vacancy_id
      - Если есть → пропустить
   
   b. Проверка черного списка
      - job_blacklist из search_config
   
   c. Получить детали вакансии
      - API GET /vacancies/{id}
   
   d. Оценка соответствия
      - Если MONKEY_MODE = true:
        * ПРОПУСТИТЬ фильтрацию LLM
        * Откликаться на ВСЕ вакансии без анализа соответствия
        * Переход сразу к шагу (e) - ответы на вопросы
      
      - Если MONKEY_MODE = false (обычный режим):
        * Запрос к LLM сервису: job_is_interesting(vacancy, resume)
        * Получить оценку 1-100
        * Порог: JOB_IS_INTERESTING_THRESH = 70 (настраиваемый)
        * Если оценка >= 70 → вакансия ИНТЕРЕСНА, продолжить
        * Если оценка < 70 → сохранить в applications (status=skipped, skip_reason=low_score), ПРОПУСТИТЬ
   
   e. Ответы на вопросы работодателя
      - Для каждого вопроса:
        * Проверить LLM кэш (через LLM сервис)
        * Если нет → запрос к LLM
        * Если требуется Selenium (test_required) → открыть браузер
   
   f. Генерация сопроводительного письма
      - Если fixed_cover_letter → использовать готовое
      - Иначе → запрос к LLM сервису
   
   g. Отправка отклика
      - API POST /negotiations
      - Передать ответы и письмо
   
   h. Сохранение результата
      - INSERT в applications (status=success/failed)
      - Логирование
   
   i. Проверка лимитов
      - Если достигнут max_applies → завершить Job

3. Отчёт в Core
   - Количество обработанных вакансий
   - Успешных откликов
   - Ошибок
```

**Selenium использование:**
```go
// Только когда hh.ru требует ответить на вопросы через веб-форму
if err.Type == "test_required" {
    ctx, cancel := chromedp.NewContext(context.Background())
    defer cancel()
    
    // 1. Открыть страницу вакансии
    // 2. Авторизоваться (если нужно)
    // 3. Найти форму с вопросами
    // 4. Заполнить ответы (от LLM)
    // 5. Отправить
    // 6. Обработать CAPTCHA (через Telegram, если появится)
}
```

**Healthcheck:**
```go
// Каждые 30 секунд обновлять статус в Redis
redis.HSet("workers:status", workerID, {
    IP: "192.168.0.1",
    ActiveJobs: len(currentJobs),
    LastSeen: time.Now(),
})
```

---

### 5. LLM Service (Микросервис для AI)

**Ответственность:**
- Proxy к различным LLM провайдерам (Gemini, OpenAI, GigaChat)
- Управление промптами
- Кэширование ответов в БД
- Анонимизация/деанонимизация личных данных
- Подсчёт стоимости запросов
- Resume Builder (генерация HTML/PDF резюме)

**Конфигурация по умолчанию:**
- **Провайдер:** Google Gemini
- **Модель:** `gemini-2.0-flash` (оптимальная по цене/качеству)
- **Temperature:** `0.4` (баланс между креативностью и строгостью)
  - Низкая температура (0.0-0.5): строгое следование промпту, меньше галлюцинаций
  - Высокая температура (0.6-1.0): более креативные ответы, но больше выдумок

**Альтернативные модели:**
- OpenAI: `gpt-4o-mini` (быстрый, доступный)
- OpenAI: `gpt-4o` (мощный, дорогой)
- GigaChat (Сбер): русскоязычная модель
- Ollama: локальные модели (бесплатно, но медленнее)

**API:**
```go
// gRPC или HTTP REST
POST /llm/v1/job_is_interesting
POST /llm/v1/answer_question
POST /llm/v1/generate_cover_letter
POST /llm/v1/summarize_text
POST /llm/v1/generate_resume
```

#### 5.1. Кэширование
```go
// Перед запросом к LLM
func (s *LLMService) AnswerQuestion(ctx context.Context, question, resume string) (string, error) {
    // 1. Создать hash ключ (question + resume hash)
    cacheKey := generateCacheKey(question, resume)
    
    // 2. Проверить кэш в БД
    cached, err := s.db.GetLLMCache(cacheKey)
    if err == nil {
        return cached.Answer, nil
    }
    
    // 3. Запрос к LLM
    answer, tokens, err := s.llmClient.Generate(prompt)
    
    // 4. Сохранить в кэш
    s.db.SaveLLMCache(cacheKey, answer, tokens, cost)
    
    return answer, nil
}
```

#### 5.2. Анонимизация
```go
func (s *LLMService) AnonymizeResume(resume Resume) Resume {
    anonymized := resume
    anonymized.FullName = "Иван Иванов"
    anonymized.Email = "example@example.com"
    anonymized.Phone = "+7 (900) 000-00-00"
    // ... остальные поля из DUMMY_PERSONAL_INFO
    return anonymized
}

func (s *LLMService) DeanonymizeText(text string, originalResume Resume) string {
    replaced := text
    replaced = strings.ReplaceAll(replaced, "Иван Иванов", originalResume.FullName)
    replaced = strings.ReplaceAll(replaced, "example@example.com", originalResume.Email)
    // ...
    return replaced
}
```

#### 5.3. Подсчёт стоимости
```go
type LLMCall struct {
    UserID        int64
    Model         string // "gemini-2.0-flash", "gpt-4o-mini"
    InputTokens   int
    OutputTokens  int
    CostUSD       float64
    Timestamp     time.Time
    PromptType    string // "job_is_interesting", "cover_letter"
}

// После каждого запроса
func (s *LLMService) LogCall(call LLMCall) {
    // 1. Рассчитать стоимость из PRICE_DICT
    cost := calculateCost(call.Model, call.InputTokens, call.OutputTokens)
    
    // 2. Сохранить в БД
    s.db.InsertLLMCall(call)
    
    // 3. Обновить metrics для Billing
    s.metrics.LLMCost.Add(cost)
}
```

#### 5.4. Resume Builder
```go
func (s *LLMService) GenerateResume(userID int64, vacancyID string, style string) ([]byte, error) {
    // 1. Получить данные пользователя и вакансии
    resume := s.db.GetUserResume(userID)
    vacancy := s.db.GetVacancy(vacancyID)
    
    // 2. Запрос к LLM (адаптация резюме под вакансию)
    adaptedResume := s.llmClient.AdaptResume(resume, vacancy)
    
    // 3. Применить CSS стиль
    htmlContent := s.applyStyle(adaptedResume, style)
    
    // 4. Конвертировать HTML → PDF (chromedp)
    pdfBytes := s.convertToPDF(htmlContent)
    
    // 5. Сохранить в БД
    s.db.SaveGeneratedResume(userID, vacancyID, pdfBytes)
    
    return pdfBytes, nil
}
```

**Провайдеры LLM:**
```go
type LLMProvider interface {
    Generate(prompt string) (response string, tokens TokenUsage, err error)
}

// Реализации
type GeminiProvider struct { ... }
type OpenAIProvider struct { ... }
type GigaChatProvider struct { ... }

// Фабрика
func NewLLMProvider(providerType string, apiKey string) LLMProvider {
    switch providerType {
    case "gemini":
        return NewGeminiProvider(apiKey)
    case "openai":
        return NewOpenAIProvider(apiKey)
    case "gigachat":
        return NewGigaChatProvider(apiKey)
    }
}
```

**MVP vs Post-MVP:**
- **MVP:** LLM сервис монолитный, workers вызывают напрямую
- **Post-MVP:** LLM как отдельный HTTP/gRPC API, для масштабирования

---

### 6. Telegram Service (Микросервис для уведомлений)

**Ответственность:**
- OAuth авторизация через Telegram
- Уведомления о приглашениях на собеседования
- Обработка CAPTCHA (интерактивно)
- Интерактивные команды бота

**Telegram Bot (один на всех пользователей):**

**Команды:**
```
/start - Регистрация/привязка аккаунта
/status - Статус подписки и откликов
/stop - Остановить отклики (pause)
/resume - Возобновить отклики
/stats - Статистика за сегодня/неделю
/help - Помощь
```

**Уведомления:**
```go
// 1. Приглашение на собеседование
msg := fmt.Sprintf(`
🎉 Новое приглашение на собеседование!

Компания: %s
Вакансия: %s
Дата: %s
Контакт: %s

Подробнее: %s
`, interview.CompanyName, interview.VacancyTitle, interview.Date, interview.Contact, interview.URL)

s.bot.SendMessage(user.TelegramID, msg)

// 2. CAPTCHA (как в Python версии)
msg := "⚠️ Требуется решить капчу для продолжения работы"
s.bot.SendPhoto(user.TelegramID, captchaImage, msg)

// Ожидание ответа пользователя
captchaSolution := s.bot.WaitForMessage(user.TelegramID, timeout)

// 3. Уведомления о завершении подписки
msg := fmt.Sprintf("⏰ Ваша подписка заканчивается через 3 дня. Продлите в личном кабинете: %s", dashboardURL)
s.bot.SendMessage(user.TelegramID, msg)
```

**OAuth через Telegram:**
```go
// Пользователь нажимает "Login with Telegram" на фронте
// Frontend перенаправляет на Telegram Login Widget
// Telegram возвращает user data на callback URL

POST /api/v1/auth/oauth/telegram
{
    "id": 123456789,
    "first_name": "Ivan",
    "username": "ivan_dev",
    "auth_date": 1698765432,
    "hash": "..."
}

// Core проверяет подпись, создаёт/обновляет пользователя
```

**API для внутренних сервисов:**
```go
POST /telegram/v1/send_notification
{
    "user_id": 123,
    "type": "interview",
    "data": { ... }
}

POST /telegram/v1/request_captcha_solution
{
    "user_id": 123,
    "image_base64": "...",
    "timeout": 300
}
```

---

### 7. YooKassa Integration (в Core)

**Ответственность:**
- Создание платежей в ЮКасса
- Обработка webhooks (подтверждение оплаты)
- Хранение истории платежей

#### 7.1. Создание платежа
```go
func (s *YooKassaService) CreatePayment(userID int64, plan string) (string, error) {
    // 1. Определить сумму по тарифу
    amount := s.getPlanPrice(plan) // 1month → 500₽, 2month → 900₽, 3month → 1200₽
    
    // 2. Создать платёж в ЮКасса API
    payment, err := s.client.CreatePayment(yookassa.Payment{
        Amount: yookassa.Amount{
            Value:    amount,
            Currency: "RUB",
        },
        Description: fmt.Sprintf("Подписка на %s", plan),
        Metadata: map[string]interface{}{
            "user_id": userID,
            "plan":    plan,
        },
        Confirmation: yookassa.Confirmation{
            Type:      "redirect",
            ReturnURL: "https://yourapp.com/billing/success",
        },
    })
    
    // 3. Сохранить в БД (pending)
    s.db.InsertPayment(Payment{
        UserID:      userID,
        YKPaymentID: payment.ID,
        Amount:      amount,
        Plan:        plan,
        Status:      "pending",
    })
    
    // 4. Вернуть URL для перенаправления пользователя
    return payment.Confirmation.ConfirmationURL, nil
}
```

#### 7.2. Webhook обработка
```go
POST /api/v1/billing/webhook (от ЮКасса)

func (s *YooKassaService) HandleWebhook(notification yookassa.Notification) {
    // 1. Проверить подпись
    if !s.verifySignature(notification) {
        return
    }
    
    // 2. Получить платёж из БД
    payment := s.db.GetPaymentByYKID(notification.Object.ID)
    
    // 3. Обновить статус
    if notification.Event == "payment.succeeded" {
        payment.Status = "succeeded"
        s.db.UpdatePayment(payment)
        
        // 4. Продлить подписку пользователя
        user := s.db.GetUser(payment.UserID)
        user.SubscriptionPlan = payment.Plan
        user.SubscriptionEnd = calculateEndDate(payment.Plan) // +1/2/3 месяца
        s.db.UpdateUser(user)
        
        // 5. Отправить уведомление
        s.telegram.SendNotification(user.ID, "subscription_activated", payment)
    }
}
```

---

## Схема архитектуры

### Высокоуровневая диаграмма

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USERS (10,000+ MAU)                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Frontend (React/Vue SPA)                        │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐          │
│  │Dashboard │ Search   │Applications│ Billing │Settings │          │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST API / WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       CORE (Go Monolith)                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  API Gateway    │  │ User Management │  │  Orchestrator   │    │
│  │  (Gin/Echo)     │  │  (Auth/OAuth)   │  │  (Job Creator)  │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐                         │
│  │    Billing      │  │   Analytics     │                         │
│  │  (ЮКасса API)   │  │  (Metrics)      │                         │
│  └─────────────────┘  └─────────────────┘                         │
└───────┬─────────────┬─────────────┬─────────────┬──────────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
   ┌────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐
   │YooKassa│   │ LLM Svc │   │Telegram │   │HH.Sched  │
   │  API   │   │ Service │   │ Service │   │Scheduler │
   └────────┘   └────┬────┘   └────┬────┘   └────┬─────┘
                     │             │             │
                     ▼             ▼             ▼
                ┌────────┐    ┌────────┐    ┌────────┐
                │api.llm │    │api.tg  │    │ Redis  │
                │(Gemini)│    │        │    │ Queue  │
                └────────┘    └────────┘    └────┬───┘
                                                  │
                     ┌────────────────────────────┼──────────────┐
                     ▼                            ▼              ▼
              ┌─────────────┐            ┌─────────────┐  ┌─────────────┐
              │  HH Worker  │            │  HH Worker  │  │  HH Worker  │
              │192.168.0.1  │            │192.168.0.2  │  │192.168.0.3  │
              │             │            │             │  │             │
              │ +Selenium   │            │ +Selenium   │  │ +Selenium   │
              └──────┬──────┘            └──────┬──────┘  └──────┬──────┘
                     │                          │                │
                     └──────────────┬───────────┴────────────────┘
                                    ▼
                              ┌──────────┐
                              │  api.hh  │
                              │ (hh.ru)  │
                              └──────────┘

                     ┌────────────────────────────┐
                     │      PostgreSQL DB         │
                     │  ┌──────────────────────┐  │
                     │  │ users                │  │
                     │  │ search_configs       │  │
                     │  │ applications         │  │
                     │  │ vacancies            │  │
                     │  │ interviews           │  │
                     │  │ llm_cache            │  │
                     │  │ llm_calls            │  │
                     │  │ payments             │  │
                     │  │ hr_messages          │  │
                     │  └──────────────────────┘  │
                     └────────────────────────────┘
```

---

## Потоки данных

### Поток 1: Регистрация пользователя

```
┌──────────┐
│  User    │
└────┬─────┘
     │
     │ 1. Заполняет форму регистрации
     ▼
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │
       │ 2. POST /api/v1/auth/register
       │    { email, password, hh_tokens }
       ▼
┌──────────────────┐
│   Core API       │
│  User Management │
└──────┬───────────┘
       │
       │ 3. Валидация данных
       │ 4. Hash password (bcrypt)
       │ 5. INSERT users (trial=3 дня)
       ▼
┌──────────────┐
│ PostgreSQL   │
└──────┬───────┘
       │
       │ 6. Возврат user_id
       ▼
┌──────────────────┐
│   Core API       │
└──────┬───────────┘
       │
       │ 7. Генерация JWT токена
       │ 8. Response { token, user }
       ▼
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │
       │ 9. Сохранить token в localStorage
       │ 10. Redirect → /dashboard
       ▼
┌──────────┐
│Dashboard │
└──────────┘
```

---

### Поток 2: Полный цикл обработки вакансии

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. ИНИЦИАЛИЗАЦИЯ (каждые N минут)                                │
└──────────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────┐
│ Core Orchestrator│
└──────┬───────────┘
       │
       │ 1.1. SELECT * FROM users WHERE subscription_end > NOW()
       │ 1.2. Для каждого user:
       │      - Получить search_config
       │      - Проверить лимиты (applications today < max)
       │      - Создать Job
       ▼
┌──────────────────┐
│  Redis Queue     │
│  jobs:pending    │
└──────┬───────────┘
       │
       │ FIFO
       ▼
┌──────────────────┐
│  HH.Scheduler    │
└──────┬───────────┘
       │
       │ 2.1. Выбрать worker (по загрузке + IP)
       │ 2.2. Отправить Job в jobs:worker{N}
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. ОБРАБОТКА ЗАДАЧИ (HH Worker)                                  │
└──────────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────┐
│   HH Worker      │
└──────┬───────────┘
       │
       │ 3.1. Получить Job из Redis
       ▼
┌──────────────────┐
│    hh.ru API     │
│ GET /vacancies   │
└──────┬───────────┘
       │
       │ 3.2. Список вакансий (20-50 шт)
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. ДЛЯ КАЖДОЙ ВАКАНСИИ                                           │
└──────────────────────────────────────────────────────────────────┘
   │
   ├─→ 4.1. Проверка дубликатов (PostgreSQL)
   │   SELECT FROM applications WHERE user_id AND vacancy_id
   │   Если есть → SKIP
   │
   ├─→ 4.2. Получить детали (hh.ru API)
   │   GET /vacancies/{id}
   │
   ├─→ 4.3. Оценка соответствия
   │   ┌──────────────────┐
   │   │   LLM Service    │
   │   │ job_is_interesting│
   │   └──────┬───────────┘
   │          │
   │          │ Проверить llm_cache
   │          │ Если нет → запрос к Gemini
   │          │ Сохранить в llm_cache
   │          ▼
   │   Оценка: 75/100 (> 70 порог JOB_IS_INTERESTING_THRESH)
   │   Вакансия ИНТЕРЕСНА → продолжить обработку
   │   
   │   Если оценка < 70:
   │   → Сохранить в applications (status=skipped, skip_reason=low_score)
   │   → Пропустить вакансию, перейти к следующей
   │
   ├─→ 4.4. Ответы на вопросы работодателя
   │   Для каждого вопроса:
   │   ┌──────────────────┐
   │   │   LLM Service    │
   │   │ answer_question  │
   │   └──────┬───────────┘
   │          │
   │          │ Проверить llm_cache
   │          │ Если нет → запрос к LLM
   │          ▼
   │   Список ответов
   │
   │   Если test_required:
   │   ┌──────────────────┐
   │   │   Selenium       │
   │   │   (chromedp)     │
   │   └──────┬───────────┘
   │          │
   │          │ Открыть страницу
   │          │ Заполнить форму
   │          │ Обработать CAPTCHA (через Telegram)
   │          ▼
   │   Отклик отправлен
   │
   ├─→ 4.5. Генерация сопроводительного письма
   │   Если fixed_cover_letter:
   │       Использовать готовое
   │   Иначе:
   │   ┌──────────────────┐
   │   │   LLM Service    │
   │   │ generate_cover   │
   │   └──────┬───────────┘
   │          │
   │          │ Запрос к LLM
   │          │ Деанонимизация
   │          ▼
   │   Сопроводительное письмо
   │
   ├─→ 4.6. Отправка отклика
   │   ┌──────────────────┐
   │   │   hh.ru API      │
   │   │POST /negotiations│
   │   └──────┬───────────┘
   │          │
   │          │ vacancy_id
   │          │ resume_id
   │          │ cover_letter
   │          │ answers[]
   │          ▼
   │   Result: success/error
   │
   └─→ 4.7. Сохранение результата
       ┌──────────────────┐
       │   PostgreSQL     │
       │  applications    │
       └──────┬───────────┘
              │
              │ INSERT (user_id, vacancy_id, status, cover_letter, created_at)
              ▼
       Логирование

┌──────────────────────────────────────────────────────────────────┐
│ 5. ЗАВЕРШЕНИЕ JOB                                                │
└──────────────────────────────────────────────────────────────────┘
   │
   ├─→ Обновить статус в Redis (workers:status)
   ├─→ Отчёт в Core (через API или Redis pub/sub)
   └─→ Логирование метрик (Prometheus)
```

---

### Поток 3: Обработка платежа

```
┌──────────┐
│  User    │
└────┬─────┘
     │
     │ 1. Выбирает тариф (1 месяц)
     ▼
┌─────────────┐
│  Frontend   │
│  /billing   │
└──────┬──────┘
       │
       │ 2. POST /api/v1/billing/subscribe
       │    { plan: "1month" }
       ▼
┌──────────────────┐
│   Core Billing   │
└──────┬───────────┘
       │
       │ 3. Создать Payment в БД (status=pending)
       │ 4. POST api.youkassa/payments
       ▼
┌──────────────────┐
│  ЮКасса API      │
└──────┬───────────┘
       │
       │ 5. Возврат { id, confirmation_url }
       ▼
┌──────────────────┐
│   Core Billing   │
└──────┬───────────┘
       │
       │ 6. Response { payment_url }
       ▼
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │
       │ 7. Redirect на payment_url
       ▼
┌──────────────────┐
│ ЮКасса страница  │
│  оплаты          │
└──────┬───────────┘
       │
       │ 8. Пользователь оплачивает
       ▼
┌──────────────────┐
│  ЮКасса API      │
└──────┬───────────┘
       │
       │ 9. POST /api/v1/billing/webhook
       │    { event: "payment.succeeded", object: {...} }
       ▼
┌──────────────────┐
│   Core Billing   │
└──────┬───────────┘
       │
       │ 10. Проверить подпись
       │ 11. UPDATE payments SET status='succeeded'
       │ 12. UPDATE users SET subscription_end = NOW() + 1 month
       ▼
┌──────────────────┐
│   PostgreSQL     │
└──────┬───────────┘
       │
       │ 13. Подписка активна
       ▼
┌──────────────────┐
│ Telegram Service │
└──────┬───────────┘
       │
       │ 14. Уведомление пользователю
       ▼
┌──────────┐
│   User   │
│ Telegram │
└──────────┘
```

---

## Модель данных

### PostgreSQL Schema

```sql
-- 1. Пользователи
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    telegram_id BIGINT UNIQUE,
    hh_user_id VARCHAR(100),
    hh_access_token TEXT,
    hh_refresh_token TEXT,
    subscription_plan VARCHAR(50) DEFAULT 'trial', -- trial, 1month, 2month, 3month
    subscription_end TIMESTAMP,
    trial_end TIMESTAMP DEFAULT NOW() + INTERVAL '3 days',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_subscription ON users(subscription_end) WHERE is_active = true;
CREATE INDEX idx_users_telegram ON users(telegram_id);

-- 2. Настройки поиска
CREATE TABLE search_configs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    job_title VARCHAR(255),
    keywords TEXT,
    exclude_keywords TEXT,
    location_ids INTEGER[],
    salary_from INTEGER,
    salary_currency VARCHAR(10),
    experience VARCHAR(50), -- noExperience, between1And3, between3And6, moreThan6
    employment_types VARCHAR(50)[], -- full, part, project, volunteer, probation
    schedule_types VARCHAR(50)[], -- fullDay, shift, flexible, remote, flyInFlyOut
    specializations INTEGER[],
    industries INTEGER[],
    job_blacklist TEXT[], -- компании для исключения
    max_applies_num INTEGER DEFAULT 200,
    apply_once_at_company BOOLEAN DEFAULT true,
    fixed_cover_letter TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT one_config_per_user UNIQUE(user_id)
);

-- 3. Резюме пользователей
CREATE TABLE resumes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    hh_resume_id VARCHAR(100),
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    position VARCHAR(255),
    summary TEXT,
    skills TEXT[],
    experience JSONB, -- [{ company, position, description, period }]
    education JSONB,
    languages JSONB,
    certificates JSONB,
    raw_data JSONB, -- полный ответ от hh.ru API
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_resumes_user ON resumes(user_id);

-- 4. История откликов
CREATE TABLE applications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    vacancy_id VARCHAR(100) NOT NULL,
    company_name VARCHAR(255),
    vacancy_title VARCHAR(255),
    vacancy_url TEXT,
    vacancy_data JSONB, -- полная информация о вакансии
    status VARCHAR(50), -- success, failed, skipped
    skip_reason VARCHAR(100), -- low_score, blacklist, duplicate, error
    llm_score INTEGER, -- оценка соответствия 1-100
    cover_letter TEXT,
    questions_answers JSONB, -- [{ question, answer }]
    error_message TEXT,
    applied_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_user_vacancy UNIQUE(user_id, vacancy_id)
);

CREATE INDEX idx_applications_user_date ON applications(user_id, applied_at DESC);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_vacancy ON applications(vacancy_id);

-- 5. Вакансии (кэш)
CREATE TABLE vacancies (
    id VARCHAR(100) PRIMARY KEY,
    company_name VARCHAR(255),
    title VARCHAR(255),
    description TEXT,
    salary_from INTEGER,
    salary_to INTEGER,
    salary_currency VARCHAR(10),
    location VARCHAR(255),
    employment_type VARCHAR(50),
    schedule_type VARCHAR(50),
    experience_required VARCHAR(50),
    skills TEXT[],
    url TEXT,
    published_at TIMESTAMP,
    raw_data JSONB,
    fetched_at TIMESTAMP DEFAULT NOW(),
    
    -- TTL для очистки старых вакансий
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '7 days'
);

CREATE INDEX idx_vacancies_company ON vacancies(company_name);
CREATE INDEX idx_vacancies_published ON vacancies(published_at DESC);
CREATE INDEX idx_vacancies_expires ON vacancies(expires_at);

-- 6. Приглашения на собеседования
CREATE TABLE interviews (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    application_id BIGINT REFERENCES applications(id),
    vacancy_id VARCHAR(100),
    company_name VARCHAR(255),
    vacancy_title VARCHAR(255),
    interview_date TIMESTAMP,
    interview_type VARCHAR(50), -- online, offline, phone
    location VARCHAR(255),
    contact_person VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_email VARCHAR(255),
    additional_info TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, confirmed, rejected, completed
    created_at TIMESTAMP DEFAULT NOW(),
    notified_at TIMESTAMP
);

CREATE INDEX idx_interviews_user ON interviews(user_id, interview_date);
CREATE INDEX idx_interviews_status ON interviews(status);

-- 7. Сообщения от работодателей
CREATE TABLE hr_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    application_id BIGINT REFERENCES applications(id),
    vacancy_id VARCHAR(100),
    company_name VARCHAR(255),
    message_type VARCHAR(50), -- invitation, rejection, question, info
    subject VARCHAR(255),
    message_text TEXT,
    is_read BOOLEAN DEFAULT false,
    received_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hr_messages_user ON hr_messages(user_id, received_at DESC);
CREATE INDEX idx_hr_messages_unread ON hr_messages(user_id) WHERE is_read = false;

-- 8. LLM кэш
CREATE TABLE llm_cache (
    id BIGSERIAL PRIMARY KEY,
    cache_key VARCHAR(64) UNIQUE NOT NULL, -- SHA256(prompt + context)
    prompt_type VARCHAR(50), -- job_is_interesting, answer_question, cover_letter
    question_text TEXT,
    context_hash VARCHAR(64), -- SHA256(resume + vacancy)
    answer TEXT,
    model VARCHAR(50),
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    hit_count INTEGER DEFAULT 0, -- сколько раз использовался
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '30 days'
);

CREATE INDEX idx_llm_cache_key ON llm_cache(cache_key);
CREATE INDEX idx_llm_cache_expires ON llm_cache(expires_at);
CREATE INDEX idx_llm_cache_type ON llm_cache(prompt_type);

-- 9. LLM логи (для аналитики)
CREATE TABLE llm_calls (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    prompt_type VARCHAR(50),
    model VARCHAR(50),
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    from_cache BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_llm_calls_user ON llm_calls(user_id, created_at DESC);
CREATE INDEX idx_llm_calls_date ON llm_calls(created_at);

-- 10. Платежи
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    yk_payment_id VARCHAR(100) UNIQUE NOT NULL,
    amount DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'RUB',
    plan VARCHAR(50), -- 1month, 2month, 3month
    status VARCHAR(50), -- pending, succeeded, canceled, failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_user ON payments(user_id, created_at DESC);
CREATE INDEX idx_payments_status ON payments(status);

-- 11. Генерированные резюме
CREATE TABLE generated_resumes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    vacancy_id VARCHAR(100),
    style VARCHAR(50), -- cloyola, josylad_blue, etc
    html_content TEXT,
    pdf_data BYTEA,
    url TEXT, -- ссылка для скачивания
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_generated_resumes_user ON generated_resumes(user_id, created_at DESC);

-- 12. Jobs (задачи для workers)
CREATE TABLE jobs (
    id VARCHAR(100) PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    search_config_id BIGINT REFERENCES search_configs(id),
    assigned_worker VARCHAR(50), -- worker IP/ID
    status VARCHAR(50) DEFAULT 'pending', -- pending, assigned, processing, completed, failed
    max_applies INTEGER,
    current_applies INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_jobs_status ON jobs(status, created_at);
CREATE INDEX idx_jobs_user ON jobs(user_id, created_at DESC);
```

### Redis Data Structures

```redis
# 1. Очередь задач (FIFO)
LIST jobs:pending
  - Элементы: JSON { job_id, user_id, priority }

# 2. Очереди для workers
LIST jobs:worker1
LIST jobs:worker2
LIST jobs:worker3

# 3. Статус workers
HASH workers:status
  - worker1: JSON { ip, active_jobs, last_seen, health }
  - worker2: ...

# 4. Кэш активных пользователей (для быстрого доступа)
HASH users:active
  - user_id: JSON { subscription_end, max_applies, today_applies }
  - TTL: 1 hour

# 5. Rate limiting
STRING rate_limit:user:{user_id}:daily
  - Значение: количество откликов сегодня
  - TTL: до конца дня

STRING rate_limit:worker:{worker_id}:hh_api
  - Значение: количество запросов к hh.ru за минуту
  - TTL: 1 minute

# 6. WebSocket connections
SET ws:connections:{user_id}
  - Элементы: connection_id[]
  - Для отправки real-time updates

# 7. CAPTCHA решения (временное хранение)
STRING captcha:{user_id}:{request_id}
  - Значение: решение капчи от пользователя
  - TTL: 5 minutes

# 8. Сессии пользователей
STRING session:{token}
  - Значение: JSON { user_id, expires_at }
  - TTL: 24 hours
```

---

## Масштабирование

### Горизонтальное масштабирование

#### 1. HH Workers
```
Текущее состояние:
- 2-3 workers (MVP)

Масштабирование:
- Добавление новых workers на разных IP
- Автоматическое обнаружение через Redis (workers:status)
- Балансировка через HH.Scheduler

При 10,000 MAU:
- Оценка: ~30-50 workers
- Расчёт: 10,000 users * 200 applies/day / 24 hours / 60 min ≈ 1,400 applies/min
- С учётом времени обработки (2-3 мин на отклик) = ~40-50 параллельных workers
```

#### 2. Core (будущее)
```
MVP: Один инстанс Core

Post-MVP:
- Несколько реплик Core за Load Balancer (Nginx/HAProxy)
- Sticky sessions для WebSocket
- Shared Redis для координации
- PostgreSQL connection pooling
```

#### 3. LLM Service
```
MVP: Встроен в Core

Post-MVP:
- Отдельный микросервис (gRPC/HTTP)
- Несколько реплик за балансером
- Разделение по провайдерам (Gemini, OpenAI, GigaChat)
```

#### 4. Telegram Service
```
MVP: Один инстанс

Post-MVP:
- Несколько реплик
- Webhook распределение через балансер
```

### Вертикальное масштабирование

```
PostgreSQL:
- Master-Slave репликация (чтение из slave)
- Партиционирование таблиц (applications, llm_calls по дате)
- Индексы на часто запрашиваемые поля

Redis:
- Redis Cluster (шардинг)
- Sentinel для HA (High Availability)
```

---

## Безопасность

### 1. Аутентификация и авторизация

```go
// JWT токены
type Claims struct {
    UserID int64  `json:"user_id"`
    Email  string `json:"email"`
    jwt.StandardClaims
}

// Middleware для проверки токена
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        claims, err := ValidateJWT(token)
        if err != nil {
            c.AbortWithStatus(401)
            return
        }
        c.Set("user_id", claims.UserID)
        c.Next()
    }
}
```

### 2. Защита персональных данных

```
1. Анонимизация для LLM:
   - ФИО → Иван Иванов
   - Телефон → +7 (900) 000-00-00
   - Email → example@example.com

2. Шифрование в БД:
   - hh_access_token, hh_refresh_token (AES-256)
   - Ключ шифрования в переменных окружения

3. HTTPS everywhere:
   - SSL/TLS для всех соединений
   - Certificate Pinning для мобильных приложений
```

### 3. Rate Limiting

```go
// На уровне пользователя
func UserRateLimiter() gin.HandlerFunc {
    return func(c *gin.Context) {
        userID := c.GetInt64("user_id")
        key := fmt.Sprintf("rate_limit:user:%d:api", userID)
        
        count, _ := redis.Incr(key)
        if count == 1 {
            redis.Expire(key, time.Minute)
        }
        
        if count > 60 { // 60 requests per minute
            c.AbortWithStatus(429)
            return
        }
        c.Next()
    }
}

// На уровне workers (hh.ru API)
// Максимум 20 requests/sec на один worker
```

### 4. Валидация данных

```go
// Pydantic-style валидация через validator library
type SearchConfigInput struct {
    JobTitle    string   `validate:"required,min=3,max=255"`
    Keywords    string   `validate:"max=500"`
    SalaryFrom  *int     `validate:"omitempty,gte=0"`
    MaxApplies  int      `validate:"required,gte=1,lte=500"`
    // ...
}

func ValidateInput(input interface{}) error {
    validate := validator.New()
    return validate.Struct(input)
}
```

### 5. SQL Injection Prevention

```go
// Использование подготовленных запросов (prepared statements)
db.Query("SELECT * FROM users WHERE email = $1", email) // ✅ Безопасно
// НЕ использовать конкатенацию строк:
// db.Query("SELECT * FROM users WHERE email = '" + email + "'") // ❌ Опасно
```

### 6. CORS

```go
// Настройка CORS для фронтенда
router.Use(cors.New(cors.Config{
    AllowOrigins:     []string{"https://yourapp.com"},
    AllowMethods:     []string{"GET", "POST", "PUT", "DELETE"},
    AllowHeaders:     []string{"Authorization", "Content-Type"},
    AllowCredentials: true,
}))
```

---

## Deployment

### MVP: Docker Compose

```yaml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: auto_jobs_applier
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Core
  core:
    build:
      context: ./core
      dockerfile: Dockerfile
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=auto_jobs_applier
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_URL=redis:6379
      - JWT_SECRET=${JWT_SECRET}
      - YK_SHOP_ID=${YK_SHOP_ID}
      - YK_SECRET_KEY=${YK_SECRET_KEY}
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # HH Scheduler
  hh_scheduler:
    build:
      context: ./hh_scheduler
      dockerfile: Dockerfile
    environment:
      - REDIS_URL=redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  # LLM Service
  llm:
    build:
      context: ./llm_service
      dockerfile: Dockerfile
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=auto_jobs_applier
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GIGACHAT_API_KEY=${GIGACHAT_API_KEY}
    depends_on:
      - postgres
    restart: unless-stopped

  # Telegram Service
  telegram:
    build:
      context: ./telegram_service
      dockerfile: Dockerfile
    environment:
      - TG_BOT_TOKEN=${TG_BOT_TOKEN}
      - TG_API_ID=${TG_API_ID}
      - TG_API_HASH=${TG_API_HASH}
      - DB_HOST=postgres
    depends_on:
      - postgres
    restart: unless-stopped

  # HH Worker 1
  hh_worker_1:
    build:
      context: ./hh_worker
      dockerfile: Dockerfile
    environment:
      - WORKER_ID=worker1
      - WORKER_IP=192.168.0.1
      - REDIS_URL=redis:6379
      - DB_HOST=postgres
      - LLM_SERVICE_URL=http://llm:8081
    depends_on:
      - redis
      - postgres
      - llm
    restart: unless-stopped

  # HH Worker 2
  hh_worker_2:
    build:
      context: ./hh_worker
      dockerfile: Dockerfile
    environment:
      - WORKER_ID=worker2
      - WORKER_IP=192.168.0.2
      - REDIS_URL=redis:6379
      - DB_HOST=postgres
      - LLM_SERVICE_URL=http://llm:8081
    depends_on:
      - redis
      - postgres
      - llm
    restart: unless-stopped

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - core
    restart: unless-stopped

  # Nginx (reverse proxy)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - core
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Production: Kubernetes (будущее)

```yaml
# Пример Deployment для Core
apiVersion: apps/v1
kind: Deployment
metadata:
  name: core
spec:
  replicas: 3
  selector:
    matchLabels:
      app: core
  template:
    metadata:
      labels:
        app: core
    spec:
      containers:
      - name: core
        image: registry.yourcompany.com/auto-jobs-applier/core:latest
        env:
        - name: DB_HOST
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: db_host
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db_password
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: core-service
spec:
  selector:
    app: core
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main, release]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'
      - name: Run tests
        run: go test ./...

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker images
        run: |
          docker-compose build
      - name: Push to registry
        run: |
          docker push registry.yourcompany.com/core:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          kubectl apply -f k8s/
          kubectl rollout status deployment/core
```

---

## Мониторинг и логирование

### Prometheus метрики

```go
// Экспорт метрик
var (
    applicationsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "applications_total",
            Help: "Total number of applications",
        },
        []string{"status"}, // success, failed, skipped
    )
    
    llmCalls = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "llm_calls_total",
            Help: "Total LLM API calls",
        },
        []string{"model", "from_cache"},
    )
    
    llmCost = promauto.NewCounter(
        prometheus.CounterOpts{
            Name: "llm_cost_usd_total",
            Help: "Total LLM cost in USD",
        },
    )
    
    activeUsers = promauto.NewGauge(
        prometheus.GaugeOpts{
            Name: "active_users",
            Help: "Number of active users",
        },
    )
)
```

### Grafana Dashboards

```
1. Business Metrics:
   - Active users (trial/paid)
   - Applications per day
   - Success rate
   - Conversion rate (trial → paid)
   - Revenue

2. Technical Metrics:
   - API response time
   - LLM latency
   - Workers load
   - Database connections
   - Redis queue length
   - Error rate

3. Cost Metrics:
   - LLM cost per user
   - LLM cost per application
   - Total infrastructure cost
```

### Логирование

```go
// Структурированные логи (zerolog/zap)
log.Info().
    Int64("user_id", userID).
    Str("vacancy_id", vacancyID).
    Str("status", "success").
    Float64("llm_score", 75.5).
    Msg("Application submitted")

// Централизованное логирование (ELK/Loki)
// Все логи отправляются в Elasticsearch/Loki для анализа
```

---

## Конфигурационные параметры

### Глобальные настройки приложения

Эти параметры определяют поведение всей системы и настраиваются на уровне сервиса Core.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| **Режимы работы** | | | |
| `MONKEY_MODE` | bool | false | Откликаться на ВСЕ вакансии без фильтрации LLM |
| `RESUME_MODE` | bool | false | Генерация резюме под вакансии (без откликов) |
| `COVER_LETTER_MODE` | bool | false | Генерация сопроводительных писем (без откликов) |
| `SKILL_STAT_MODE` | bool | false | Сбор статистики по навыкам из вакансий |
| **Пороги и лимиты** | | | |
| `JOB_IS_INTERESTING_THRESH` | int | 70 | Порог оценки LLM для фильтрации вакансий (0-100) |
| `MINIMUM_WAIT_TIME_SEC` | int | 10 | Минимальное время между откликами (секунды) |
| `RAISE_RESUME` | bool | true | Поднимать резюме в поиске (не чаще 1 раз в 4 часа) |
| **LLM настройки** | | | |
| `LLM_MODEL_TYPE` | string | "gemini" | Провайдер LLM: openai, gemini, gigachat, claude, ollama, huggingface |
| `LLM_MODEL` | string | "gemini-2.0-flash" | Конкретная модель LLM |
| `TEMPERATURE` | float | 0.4 | Температура модели (0.0-1.0): креативность vs строгость |
| **Логирование** | | | |
| `MINIMUM_LOG_LEVEL` | string | "INFO" | Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL |

### Настройки на уровне пользователя

Эти параметры хранятся в таблице `search_configs` и настраиваются каждым пользователем индивидуально.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `job_title` | string | - | Желаемая должность |
| `keywords` | text | - | Ключевые слова для поиска |
| `exclude_keywords` | text | - | Исключающие слова |
| `salary_from` | int | - | Минимальная зарплата |
| `max_applies_num` | int | 200 | Максимум откликов в день |
| `apply_once_at_company` | bool | true | Откликаться на одну компанию только раз |
| `fixed_cover_letter` | text | null | Фиксированное сопроводительное письмо (если заполнено, LLM не используется) |
| `job_blacklist` | text[] | [] | Список компаний для исключения |

### Цены LLM моделей (для расчёта стоимости)

| Модель | Входные токены | Выходные токены |
|--------|----------------|-----------------|
| `gemini-2.0-flash` | $0.0000001 | $0.0000004 |
| `gpt-4o-mini` | $0.00000015 | $0.0000006 |
| `gpt-4o` | $0.0000025 | $0.00001 |
| `GigaChat` | $0.000002 | $0.000002 |
| `GigaChat-Pro` | $0.000015 | $0.000015 |
| `GigaChat-Max` | $0.0000195 | $0.0000195 |

**Примечание:** Цены указаны за 1 токен. Реальная стоимость зависит от длины промптов и ответов.

**Пример расчёта:**
```
Отклик на 1 вакансию с gemini-2.0-flash:
- job_is_interesting: ~500 input + ~100 output = $0.00009
- answer_question (3 вопроса): ~300 input + ~80 output × 3 = $0.00013
- cover_letter: ~600 input + ~250 output = $0.00016
ИТОГО: ~$0.00038 на 1 отклик

При 200 откликах/день: $0.076/день = $2.28/месяц на пользователя
```

---

## Миграция с Python версии

### Этапы миграции

```
Этап 1: MVP (3 месяца)
├─ Разработка Core (API Gateway, User Management, Orchestrator)
├─ Разработка HH Worker (базовая функциональность)
├─ Интеграция LLM (Gemini)
├─ PostgreSQL схема
├─ Redis queue
└─ Базовый Frontend

Этап 2: Billing & Telegram (1 месяц)
├─ ЮКасса интеграция
├─ Telegram Bot
├─ OAuth (Telegram, hh.ru)
└─ Подписки и триал

Этап 3: Полная функциональность (2 месяца)
├─ Resume Builder
├─ Selenium интеграция (chromedp)
├─ CAPTCHA обработка
├─ История диалогов с HR
├─ Приглашения на собеседования
└─ Рекомендованные вакансии

Этап 4: Оптимизация (1 месяц)
├─ LLM кэширование
├─ Прокси поддержка
├─ Масштабирование workers
├─ Мониторинг и алерты
└─ Performance tuning

Этап 5: Production (1 месяц)
├─ Load testing
├─ Security audit
├─ CI/CD настройка
├─ Backup и disaster recovery
└─ Документация
```

### Параллельная работа

```
Период переходный (1-2 месяца):
- Python версия продолжает работать для текущих пользователей
- Go версия в закрытом бета-тесте (100-500 пользователей)
- Сравнение результатов и метрик
- Миграция пользователей по подписке (при продлении)
```

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| **Ban от hh.ru** | Средняя | Критическое | Разные IP для workers, rate limiting, человекоподобное поведение |
| **LLM cost взрывной рост** | Высокая | Высокое | Кэширование, выбор дешёвых моделей, лимиты на пользователя |
| **Изменение hh.ru API** | Низкая | Высокое | Версионирование API, мониторинг изменений, быстрое обновление |
| **CAPTCHA блокировка** | Средняя | Среднее | Telegram интеграция, человеческое решение, разные workers |
| **Scalability проблемы** | Средняя | Высокое | Горизонтальное масштабирование, кэширование, оптимизация БД |
| **Конкуренция** | Высокая | Среднее | Уникальные фичи, качество LLM, UX, цена |

---

## Заключение

Архитектура Go-версии XX Auto Jobs Applier разработана для:

✅ **Масштабируемости** - поддержка 10,000+ MAU  
✅ **Надёжности** - распределённые workers, fault tolerance  
✅ **Эффективности** - кэширование, оптимизация LLM расходов  
✅ **Монетизации** - подписки, триал, биллинг  
✅ **Безопасности** - защита данных, анонимизация  

**Следующие шаги:**
1. Детальное проектирование Core модулей
2. Определение API контрактов
3. Выбор технологий (Gin vs Echo, chromedp vs rod)
4. Создание прототипа (PoC)
5. Разработка MVP

---

**Автор:** Архитектурная документация  
**Версия:** 1.0  
**Дата:** 22 октября 2025  
**Статус:** Draft для утверждения

