# API Contracts

Детальное описание API контрактов всех сервисов системы.

## Оглавление

1. [Core API](#core-api)
2. [LLM Service API](#llm-service-api)
3. [Telegram Service API](#telegram-service-api)
4. [HH.Worker Internal API](#hhworker-internal-api)
5. [WebSocket API](#websocket-api)
6. [Error Handling](#error-handling)

---

## Core API

Base URL: `https://api.yourapp.com/api/v1`

### Authentication

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

---

### 1. Auth Endpoints

#### POST /auth/register

Регистрация нового пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "hh_access_token": "optional_hh_token",
  "hh_refresh_token": "optional_hh_refresh"
}
```

**Response 201:**
```json
{
  "user": {
    "id": 123,
    "email": "user@example.com",
    "subscription_plan": "trial",
    "trial_end": "2025-10-25T12:00:00Z",
    "created_at": "2025-10-22T12:00:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Errors:**
- `400` - Invalid email or weak password
- `409` - Email already exists

---

#### POST /auth/login

Вход в систему.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response 200:**
```json
{
  "user": {
    "id": 123,
    "email": "user@example.com",
    "subscription_plan": "1month",
    "subscription_end": "2025-11-22T12:00:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Errors:**
- `401` - Invalid credentials
- `404` - User not found

---

#### POST /auth/oauth/telegram

OAuth через Telegram.

**Request:**
```json
{
  "id": 123456789,
  "first_name": "Ivan",
  "username": "ivan_dev",
  "auth_date": 1698765432,
  "hash": "abc123..."
}
```

**Response 200:**
```json
{
  "user": {
    "id": 123,
    "email": null,
    "telegram_id": 123456789,
    "subscription_plan": "trial"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "is_new_user": true
}
```

---

#### POST /auth/oauth/hh

OAuth через hh.ru.

**Request:**
```json
{
  "code": "authorization_code_from_hh",
  "redirect_uri": "https://yourapp.com/auth/callback"
}
```

**Response 200:**
```json
{
  "user": {
    "id": 123,
    "email": "user@example.com",
    "hh_user_id": "hh_123456",
    "subscription_plan": "trial"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "is_new_user": true
}
```

---

### 2. User Endpoints

#### GET /users/me

Получить текущего пользователя.

**Response 200:**
```json
{
  "id": 123,
  "email": "user@example.com",
  "telegram_id": 123456789,
  "hh_user_id": "hh_123456",
  "subscription_plan": "1month",
  "subscription_end": "2025-11-22T12:00:00Z",
  "trial_end": null,
  "is_active": true,
  "created_at": "2025-10-22T12:00:00Z",
  "stats": {
    "total_applications": 450,
    "successful_applications": 380,
    "interviews_count": 15
  }
}
```

---

#### PUT /users/me

Обновить профиль.

**Request:**
```json
{
  "email": "newemail@example.com",
  "hh_access_token": "new_token",
  "hh_refresh_token": "new_refresh"
}
```

**Response 200:**
```json
{
  "id": 123,
  "email": "newemail@example.com",
  "updated_at": "2025-10-22T13:00:00Z"
}
```

---

### 3. Search Config Endpoints

#### GET /search-config

Получить настройки поиска.

**Response 200:**
```json
{
  "id": 456,
  "user_id": 123,
  "job_title": "Backend Developer",
  "keywords": "golang, python, api",
  "exclude_keywords": "php, wordpress",
  "location_ids": [1, 2],
  "salary_from": 150000,
  "salary_currency": "RUR",
  "experience": "between3And6",
  "employment_types": ["full", "remote"],
  "schedule_types": ["remote", "flexible"],
  "max_applies_num": 200,
  "apply_once_at_company": true,
  "fixed_cover_letter": null,
  "job_blacklist": ["ООО Рога и Копыта", "ИП Пупкин"],
  "updated_at": "2025-10-22T12:00:00Z"
}
```

---

#### PUT /search-config

Обновить настройки поиска.

**Request:**
```json
{
  "job_title": "Go Developer",
  "keywords": "golang, kubernetes, microservices",
  "salary_from": 200000,
  "max_applies_num": 150,
  "fixed_cover_letter": "Здравствуйте! Меня заинтересовала ваша вакансия..."
}
```

**Response 200:**
```json
{
  "id": 456,
  "user_id": 123,
  "job_title": "Go Developer",
  "keywords": "golang, kubernetes, microservices",
  "salary_from": 200000,
  "max_applies_num": 150,
  "fixed_cover_letter": "Здравствуйте! Меня заинтересовала ваша вакансия...",
  "updated_at": "2025-10-22T13:30:00Z"
}
```

---

### 4. Applications Endpoints

#### GET /applications

Получить историю откликов.

**Query Parameters:**
- `page` (int, default=1)
- `per_page` (int, default=20, max=100)
- `status` (string: success, failed, skipped)
- `date_from` (ISO8601)
- `date_to` (ISO8601)
- `company_name` (string)

**Response 200:**
```json
{
  "applications": [
    {
      "id": 1001,
      "user_id": 123,
      "vacancy_id": "98765432",
      "company_name": "Яндекс",
      "vacancy_title": "Go Developer",
      "vacancy_url": "https://hh.ru/vacancy/98765432",
      "status": "success",
      "llm_score": 85,
      "cover_letter": "Здравствуйте! Меня заинтересовала...",
      "questions_answers": [
        {
          "question": "Опыт с Kubernetes?",
          "answer": "Да, 3 года работы с K8s в production..."
        }
      ],
      "applied_at": "2025-10-22T10:30:00Z"
    },
    {
      "id": 1002,
      "vacancy_id": "98765433",
      "company_name": "Сбер",
      "vacancy_title": "Senior Backend Developer",
      "status": "skipped",
      "skip_reason": "low_score",
      "llm_score": 45,
      "applied_at": "2025-10-22T10:35:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 450,
    "total_pages": 23
  }
}
```

---

#### GET /applications/:id

Детали одного отклика.

**Response 200:**
```json
{
  "id": 1001,
  "user_id": 123,
  "vacancy_id": "98765432",
  "company_name": "Яндекс",
  "vacancy_title": "Go Developer",
  "vacancy_url": "https://hh.ru/vacancy/98765432",
  "vacancy_data": {
    "description": "Мы ищем опытного Go разработчика...",
    "salary": {"from": 250000, "to": 350000, "currency": "RUR"},
    "skills": ["Go", "Kubernetes", "PostgreSQL"],
    "experience": "between3And6"
  },
  "status": "success",
  "llm_score": 85,
  "cover_letter": "Здравствуйте! Меня заинтересовала...",
  "questions_answers": [
    {"question": "Опыт с Kubernetes?", "answer": "Да, 3 года..."}
  ],
  "applied_at": "2025-10-22T10:30:00Z"
}
```

---

#### POST /applications/:id/messages

Добавить сообщение от HR (вручную).

**Request:**
```json
{
  "message_type": "invitation",
  "subject": "Приглашение на собеседование",
  "message_text": "Добрый день! Мы хотели бы пригласить вас..."
}
```

**Response 201:**
```json
{
  "id": 501,
  "application_id": 1001,
  "message_type": "invitation",
  "subject": "Приглашение на собеседование",
  "message_text": "Добрый день! Мы хотели бы пригласить вас...",
  "is_read": false,
  "received_at": "2025-10-22T14:00:00Z"
}
```

---

### 5. Vacancies Endpoints

#### GET /vacancies

Рекомендованные вакансии по профилю.

**Query Parameters:**
- `page` (int)
- `per_page` (int)

**Response 200:**
```json
{
  "vacancies": [
    {
      "id": "98765432",
      "company_name": "Яндекс",
      "title": "Go Developer",
      "description": "Мы ищем опытного...",
      "salary": {"from": 250000, "to": 350000, "currency": "RUR"},
      "location": "Москва",
      "employment_type": "full",
      "schedule_type": "remote",
      "skills": ["Go", "Kubernetes", "PostgreSQL"],
      "url": "https://hh.ru/vacancy/98765432",
      "published_at": "2025-10-20T09:00:00Z",
      "llm_score": 85,
      "already_applied": false
    }
  ],
  "pagination": {...}
}
```

---

### 6. Interviews Endpoints

#### GET /interviews

Получить приглашения на собеседования.

**Query Parameters:**
- `status` (pending, confirmed, rejected, completed)
- `date_from`
- `date_to`

**Response 200:**
```json
{
  "interviews": [
    {
      "id": 301,
      "user_id": 123,
      "application_id": 1001,
      "vacancy_id": "98765432",
      "company_name": "Яндекс",
      "vacancy_title": "Go Developer",
      "interview_date": "2025-10-25T14:00:00Z",
      "interview_type": "online",
      "location": "Google Meet",
      "contact_person": "Иванов Иван",
      "contact_phone": "+7 (999) 123-45-67",
      "contact_email": "ivanov@yandex.ru",
      "additional_info": "Ссылка на встречу будет отправлена за час до собеседования",
      "status": "pending",
      "created_at": "2025-10-22T15:00:00Z"
    }
  ]
}
```

---

#### PATCH /interviews/:id

Обновить статус собеседования.

**Request:**
```json
{
  "status": "confirmed"
}
```

**Response 200:**
```json
{
  "id": 301,
  "status": "confirmed",
  "updated_at": "2025-10-22T16:00:00Z"
}
```

---

### 7. Billing Endpoints

#### GET /billing/subscription

Получить текущую подписку.

**Response 200:**
```json
{
  "user_id": 123,
  "subscription_plan": "1month",
  "subscription_end": "2025-11-22T12:00:00Z",
  "is_trial": false,
  "days_left": 31,
  "auto_renew": false,
  "next_billing_date": null
}
```

---

#### POST /billing/subscribe

Создать платёж для подписки.

**Request:**
```json
{
  "plan": "2month"
}
```

**Response 200:**
```json
{
  "payment_id": "abc123-def456",
  "yk_payment_id": "2a5a7b9c-....",
  "amount": 900.00,
  "currency": "RUB",
  "plan": "2month",
  "status": "pending",
  "confirmation_url": "https://yoomoney.ru/payments/abc123",
  "created_at": "2025-10-22T17:00:00Z"
}
```

**Frontend:**
```javascript
// Перенаправить пользователя на confirmation_url
window.location.href = response.confirmation_url
```

---

#### POST /billing/cancel

Отменить подписку (не продлевать).

**Response 200:**
```json
{
  "user_id": 123,
  "subscription_plan": "1month",
  "subscription_end": "2025-11-22T12:00:00Z",
  "auto_renew": false,
  "message": "Подписка будет отменена после окончания текущего периода"
}
```

---

#### GET /billing/history

История платежей.

**Response 200:**
```json
{
  "payments": [
    {
      "id": "payment_123",
      "yk_payment_id": "2a5a7b9c-....",
      "amount": 500.00,
      "currency": "RUB",
      "plan": "1month",
      "status": "succeeded",
      "created_at": "2025-09-22T12:00:00Z",
      "updated_at": "2025-09-22T12:05:00Z"
    }
  ]
}
```

---

#### POST /billing/webhook

Webhook от ЮКасса (НЕ для фронтенда).

**Request (от ЮКасса):**
```json
{
  "type": "notification",
  "event": "payment.succeeded",
  "object": {
    "id": "2a5a7b9c-....",
    "status": "succeeded",
    "amount": {
      "value": "500.00",
      "currency": "RUB"
    },
    "metadata": {
      "user_id": "123",
      "plan": "1month"
    }
  }
}
```

**Response 200:**
```json
{
  "status": "ok"
}
```

**Логика:**
1. Проверить подпись ЮКасса
2. Обновить payment status в БД
3. Продлить subscription_end пользователя
4. Отправить уведомление в Telegram

---

## LLM Service API

Base URL: `http://llm:8081/llm/v1` (internal)

### 1. Job Interest Score

#### POST /job_is_interesting

Оценка соответствия вакансии резюме (1-100).

**Request:**
```json
{
  "user_id": 123,
  "vacancy": {
    "title": "Go Developer",
    "description": "Мы ищем опытного разработчика на Go...",
    "skills": ["Go", "Kubernetes", "PostgreSQL"],
    "salary": {"from": 250000, "to": 350000}
  },
  "resume": {
    "position": "Backend Developer",
    "skills": ["Go", "Python", "PostgreSQL", "Docker"],
    "experience": [
      {
        "company": "Яндекс",
        "position": "Backend Developer",
        "duration_years": 3,
        "description": "Разработка микросервисов на Go..."
      }
    ]
  },
  "model": "gemini-2.0-flash"
}
```

**Response 200:**
```json
{
  "score": 85,
  "reasoning": "Опыт кандидата отлично соответствует требованиям: 3 года работы с Go, опыт с PostgreSQL и Docker. Отсутствует опыт с Kubernetes, но это можно быстро освоить.",
  "from_cache": false,
  "tokens": {
    "input": 450,
    "output": 120
  },
  "cost_usd": 0.000093,
  "model": "gemini-2.0-flash"
}
```

---

### 2. Answer Question

#### POST /answer_question

Ответ на вопрос работодателя.

**Request:**
```json
{
  "user_id": 123,
  "question": "Опыт работы с Kubernetes в production?",
  "question_type": "textual",
  "resume": {
    "experience": [...]
  },
  "model": "gemini-2.0-flash"
}
```

**Response 200:**
```json
{
  "answer": "Да, у меня есть опыт работы с Kubernetes: в Яндексе я развернул и поддерживал 15+ микросервисов в K8s кластере, настраивал мониторинг через Prometheus и Grafana.",
  "from_cache": true,
  "tokens": null,
  "cost_usd": 0.0
}
```

---

### 3. Generate Cover Letter

#### POST /generate_cover_letter

Генерация сопроводительного письма.

**Request:**
```json
{
  "user_id": 123,
  "vacancy": {...},
  "resume": {...},
  "model": "gemini-2.0-flash"
}
```

**Response 200:**
```json
{
  "cover_letter": "Здравствуйте!\n\nМеня заинтересовала вакансия Go Developer в вашей компании...",
  "anonymized_letter": "Здравствуйте!\n\nМеня заинтересовала... (с Иван Иванов вместо реального имени)",
  "from_cache": false,
  "tokens": {"input": 600, "output": 250},
  "cost_usd": 0.00016
}
```

**Примечание:** Поле `cover_letter` уже деанонимизировано (с реальными данными пользователя).

---

### 4. Generate Resume

#### POST /generate_resume

Генерация HTML/PDF резюме под вакансию.

**Request:**
```json
{
  "user_id": 123,
  "vacancy_id": "98765432",
  "style": "josylad_blue",
  "model": "gemini-2.0-flash"
}
```

**Response 200:**
```json
{
  "resume_id": "resume_123_98765432",
  "html_url": "https://yourapp.com/resumes/resume_123_98765432.html",
  "pdf_url": "https://yourapp.com/resumes/resume_123_98765432.pdf",
  "created_at": "2025-10-22T18:00:00Z"
}
```

---

### 5. Summarize Text

#### POST /summarize_text

Резюмирование длинного текста.

**Request:**
```json
{
  "text": "Очень длинное описание вакансии, более 5000 слов...",
  "max_length": 500,
  "model": "gemini-2.0-flash"
}
```

**Response 200:**
```json
{
  "summary": "Компания ищет опытного Go разработчика для работы над микросервисами. Требуется опыт с Kubernetes, PostgreSQL, gRPC. Зарплата 250-350k.",
  "tokens": {"input": 3500, "output": 80},
  "cost_usd": 0.00038
}
```

---

## Telegram Service API

Base URL: `http://telegram:8082/telegram/v1` (internal)

### 1. Send Notification

#### POST /send_notification

Отправить уведомление пользователю.

**Request:**
```json
{
  "user_id": 123,
  "notification_type": "interview",
  "data": {
    "company_name": "Яндекс",
    "vacancy_title": "Go Developer",
    "interview_date": "2025-10-25T14:00:00Z",
    "contact_person": "Иванов Иван",
    "contact_phone": "+7 (999) 123-45-67"
  }
}
```

**Response 200:**
```json
{
  "status": "sent",
  "telegram_message_id": 12345,
  "sent_at": "2025-10-22T19:00:00Z"
}
```

**Telegram Message:**
```
🎉 Новое приглашение на собеседование!

Компания: Яндекс
Вакансия: Go Developer
Дата: 25 октября 2025, 14:00
Контакт: Иванов Иван (+7 (999) 123-45-67)

Подробнее: https://yourapp.com/interviews/301
```

---

### 2. Request CAPTCHA Solution

#### POST /request_captcha_solution

Запросить решение капчи у пользователя.

**Request:**
```json
{
  "user_id": 123,
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "timeout_seconds": 300
}
```

**Response 200:**
```json
{
  "request_id": "captcha_123_456",
  "status": "pending",
  "expires_at": "2025-10-22T19:05:00Z"
}
```

**Логика:**
1. Отправить изображение капчи в Telegram пользователю
2. Ждать ответ от пользователя (max 5 минут)
3. Сохранить решение в Redis: `captcha:{user_id}:{request_id}`

**Telegram Message:**
```
⚠️ Требуется решить капчу для продолжения работы

[Изображение капчи]

Пожалуйста, введите символы с картинки:
```

---

### 3. Get CAPTCHA Solution

#### GET /captcha_solution/:request_id

Получить решение капчи (для worker).

**Response 200:**
```json
{
  "request_id": "captcha_123_456",
  "solution": "xK9pLm",
  "solved_at": "2025-10-22T19:02:00Z"
}
```

**Response 408 (timeout):**
```json
{
  "error": "timeout",
  "message": "Пользователь не ответил в течение 5 минут"
}
```

---

## HH.Worker Internal API

Воркеры НЕ предоставляют HTTP API, но взаимодействуют через:

1. **Redis Queue** (получение Jobs)
2. **PostgreSQL** (сохранение результатов)
3. **LLM Service API** (запросы к LLM)
4. **Telegram Service API** (CAPTCHA)
5. **hh.ru API** (поиск и отклики)

### Worker → LLM Service

```go
// Пример запроса к LLM сервису
type LLMClient struct {
    baseURL string
}

func (c *LLMClient) JobIsInteresting(vacancy Vacancy, resume Resume) (int, error) {
    req := JobInterestRequest{
        UserID: resume.UserID,
        Vacancy: vacancy,
        Resume: resume,
        Model: "gemini-2.0-flash",
    }
    
    resp, _ := http.Post(c.baseURL+"/job_is_interesting", "application/json", reqBody)
    // Parse response...
    return resp.Score, nil
}
```

### Worker → Telegram Service (CAPTCHA)

```go
func (w *Worker) SolveCAPTCHA(imageBase64 string) (string, error) {
    // 1. Запросить решение
    reqResp, _ := w.telegramClient.RequestCAPTCHA(w.userID, imageBase64, 300)
    requestID := reqResp.RequestID
    
    // 2. Ждать решение (polling каждые 5 секунд)
    for i := 0; i < 60; i++ {
        solution, err := w.telegramClient.GetCAPTCHASolution(requestID)
        if err == nil {
            return solution.Solution, nil
        }
        time.Sleep(5 * time.Second)
    }
    
    return "", errors.New("CAPTCHA timeout")
}
```

---

## WebSocket API

**URL:** `wss://api.yourapp.com/api/v1/ws`

**Authentication:** Query parameter `?token=JWT_TOKEN`

### Connection

```javascript
const ws = new WebSocket('wss://api.yourapp.com/api/v1/ws?token=' + jwtToken)

ws.onopen = () => {
  console.log('Connected to WebSocket')
}

ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  handleRealtimeUpdate(message)
}
```

### Message Types

#### 1. New Application

Когда создан новый отклик.

```json
{
  "type": "new_application",
  "data": {
    "id": 1005,
    "vacancy_id": "98765440",
    "company_name": "Сбер",
    "vacancy_title": "Senior Go Developer",
    "status": "success",
    "llm_score": 92,
    "applied_at": "2025-10-22T20:00:00Z"
  }
}
```

#### 2. New Interview

Новое приглашение на собеседование.

```json
{
  "type": "new_interview",
  "data": {
    "id": 305,
    "company_name": "Яндекс",
    "vacancy_title": "Go Developer",
    "interview_date": "2025-10-25T14:00:00Z",
    "status": "pending"
  }
}
```

#### 3. Job Progress

Прогресс выполнения задачи.

```json
{
  "type": "job_progress",
  "data": {
    "job_id": "job_123",
    "status": "processing",
    "current_applies": 45,
    "max_applies": 200,
    "progress_percent": 22.5
  }
}
```

#### 4. Subscription Expiring

Подписка скоро закончится.

```json
{
  "type": "subscription_expiring",
  "data": {
    "subscription_plan": "1month",
    "subscription_end": "2025-10-25T12:00:00Z",
    "days_left": 3
  }
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "value": "invalid-email"
    },
    "request_id": "req_abc123"
  }
}
```

### Error Codes

| HTTP | Code | Описание |
|------|------|----------|
| 400 | `VALIDATION_ERROR` | Невалидные данные в запросе |
| 401 | `UNAUTHORIZED` | Невалидный или отсутствует токен |
| 403 | `FORBIDDEN` | Нет доступа к ресурсу |
| 404 | `NOT_FOUND` | Ресурс не найден |
| 409 | `CONFLICT` | Конфликт (например, email уже существует) |
| 422 | `UNPROCESSABLE_ENTITY` | Бизнес-логика не позволяет выполнить операцию |
| 429 | `RATE_LIMIT_EXCEEDED` | Превышен лимит запросов |
| 500 | `INTERNAL_ERROR` | Внутренняя ошибка сервера |
| 503 | `SERVICE_UNAVAILABLE` | Сервис временно недоступен |

### Rate Limiting Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1698765432
```

### Request Tracing

Каждый ответ содержит:
```
X-Request-ID: req_abc123def456
```

Для отладки и логирования.

---

## Versioning

**Формат:** `/api/v{N}/endpoint`

**Текущая версия:** v1

**Backward Compatibility:**
- Изменения, которые НЕ ломают совместимость (добавление полей) - в той же версии
- Breaking changes - новая версия (v2)

**Deprecation Policy:**
- Уведомление за 3 месяца
- Старая версия поддерживается 6 месяцев после релиза новой

---

## Pagination

Стандартная пагинация для всех списковых эндпоинтов:

**Query Parameters:**
- `page` (default=1)
- `per_page` (default=20, max=100)

**Response:**
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 450,
    "total_pages": 23,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## CORS

**Allowed Origins:**
- `https://yourapp.com` (production)
- `http://localhost:3000` (development)

**Allowed Methods:**
- GET, POST, PUT, PATCH, DELETE, OPTIONS

**Allowed Headers:**
- Authorization, Content-Type, X-Request-ID

---

## Заключение

API контракты разработаны с учётом:

✅ **RESTful принципов**  
✅ **Consistency** (единообразие структур)  
✅ **Backward compatibility**  
✅ **Security** (JWT, rate limiting)  
✅ **Developer Experience** (понятные ошибки, документация)

**Следующий шаг:** Генерация OpenAPI (Swagger) документации

---

**Автор:** API Contracts Documentation  
**Версия:** 1.0  
**Дата:** 22 октября 2025

