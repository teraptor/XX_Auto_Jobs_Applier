# Go Architecture - Краткий обзор

Документация по архитектуре Go-версии XX Auto Jobs Applier.

## 📋 Документы

| Документ | Описание | Читать |
|----------|----------|--------|
| **[README.md](README.md)** | Введение и навигация | 5 мин |
| **[architecture-go.md](architecture-go.md)** | Полная архитектура системы | 30 мин |
| **[tech-stack.md](tech-stack.md)** | Технологический стек | 20 мин |
| **[api-contracts.md](api-contracts.md)** | API контракты | 25 мин |
| **[migration-plan.md](migration-plan.md)** | План миграции с Python | 20 мин |

**Общее время на изучение:** ~100 минут (1.5 часа)

---

## 🎯 Ключевые решения

### 1. Архитектура

**Выбор:** Монолитный Core + Распределённые Workers

**Обоснование:**
- Core монолитный (проще разработка MVP)
- Workers горизонтально масштабируются
- Микросервисы только где нужно (LLM, Telegram)

### 2. Технологии

| Компонент | Технология | Почему |
|-----------|------------|--------|
| **Backend** | Go 1.21+ | Производительность, concurrency |
| **Web Framework** | Gin | Популярность, производительность |
| **Database** | PostgreSQL 15 | Надёжность, JSONB, полнотекстовый поиск |
| **Cache/Queue** | Redis 7 | Быстро, простое API |
| **Frontend** | React 18 | Большое сообщество, компоненты |
| **Selenium** | chromedp | Нативный Go, быстрее |
| **LLM** | Gemini 2.0-flash | Дешевле, быстрее |

### 3. Deployment

**MVP:** Docker Compose на VPS  
**Production:** Kubernetes (будущее)

---

## 🏗️ Компоненты системы

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Frontend   │ (React)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         Core (Go Monolith)          │
│  ┌──────────┬──────────┬─────────┐ │
│  │API Gateway│User Mgmt │Billing │ │
│  └──────────┴──────────┴─────────┘ │
└──────┬──────────┬──────────┬───────┘
       │          │          │
       ▼          ▼          ▼
   ┌───────┐ ┌───────┐ ┌──────────┐
   │YooKassa│ │  LLM  │ │Telegram │
   └───────┘ └───┬───┘ └──────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
   ┌────────┐        ┌──────────┐
   │HH.Sched│───────>│  Redis   │
   └────────┘        └────┬─────┘
                          │
       ┌──────────────────┼──────────────┐
       ▼                  ▼              ▼
   ┌────────┐        ┌────────┐    ┌────────┐
   │Worker 1│        │Worker 2│    │Worker N│
   └───┬────┘        └───┬────┘    └───┬────┘
       │                 │              │
       └─────────────────┼──────────────┘
                         ▼
                    ┌─────────┐
                    │  hh.ru  │
                    └─────────┘
```

---

## 📊 Сравнение: Python vs Go

| Критерий | Python | Go |
|----------|--------|-----|
| **Архитектура** | Монолит | Микросервисы |
| **Пользователи** | 1 (локальный) | 10,000+ (SaaS) |
| **UI** | CLI | Web (React) |
| **Хранение** | YAML файлы | PostgreSQL + Redis |
| **Масштабирование** | Вертикальное | Горизонтальное |
| **Производительность** | ~10 откликов/час | 200+ откликов/час |
| **Монетизация** | Нет | Подписки (ЮКасса) |
| **Deployment** | Локально | Cloud (Docker/K8s) |

---

## 📈 Timeline миграции

```
Месяц 1-2:  Core (API Gateway, Auth, Orchestrator)
Месяц 3:    Worker (базовая логика)
Месяц 4:    Frontend + Billing
Месяц 5:    Оптимизация
Месяц 6:    Deployment + Monitoring
Месяц 7-8:  Beta Testing
────────────────────────────────────────────────
TOTAL: 6-8 месяцев до launch
```

---

## 💰 Бюджет

### Development (6 месяцев)
- **Команда (4.5 FTE):** $180,000
- **Инфраструктура:** $1,200
- **Сервисы:** $600
- **ИТОГО:** **$181,800**

### Production (месяц)
- **Серверы (Core + Workers):** $140
- **PostgreSQL + Redis:** $45
- **LLM API:** $100-500
- **ИТОГО:** **$295-745/мес**

### При 10,000 MAU
- **Infrastructure:** $1,500-3,500/мес
- **Revenue (10% conversion):** $5,000/мес
- **Profit:** **$1,500-3,500/мес**

---

## ✅ MVP Scope

**Включено в MVP:**
- ✅ Регистрация/авторизация (Login, OAuth)
- ✅ Настройка поиска (web UI)
- ✅ Автоматические отклики (hh.ru API)
- ✅ LLM интеграция (Gemini)
- ✅ Dashboard с статистикой
- ✅ Подписки (ЮКасса)
- ✅ Telegram бот (уведомления)

**НЕ включено в MVP:**
- ❌ Selenium (только API)
- ❌ Resume Builder
- ❌ CAPTCHA handling
- ❌ HR dialogs
- ❌ Mobile apps

---

## 🚀 Следующие шаги

### Неделя 1
1. ✅ Утвердить архитектуру
2. ✅ Собрать команду (4-8 человек)
3. ✅ Создать репозиторий
4. ✅ Настроить Docker Compose

### Неделя 2
1. Создать PostgreSQL migrations
2. Настроить CI/CD (GitHub Actions)
3. Начать Core разработку
4. Kick-off встреча

### Месяц 1
1. Core API Gateway
2. User Management
3. Orchestrator
4. Unit + Integration tests

### Месяц 3
1. Демо для stakeholders
2. Внутреннее тестирование
3. Корректировка roadmap

### Месяц 6
1. Beta launch (500 пользователей)
2. Marketing campaign
3. Сбор feedback

### Месяц 8
1. **Public Launch 🚀**

---

## 📚 Детальная информация

Для углубления в конкретные темы читайте:

**Архитектура:**
- [Компоненты системы](architecture-go.md#компоненты-системы)
- [Схема архитектуры](architecture-go.md#схема-архитектуры)
- [Потоки данных](architecture-go.md#потоки-данных)
- [Модель данных](architecture-go.md#модель-данных)

**Технологии:**
- [Backend stack](tech-stack.md#backend)
- [Frontend stack](tech-stack.md#frontend)
- [Infrastructure](tech-stack.md#infrastructure)
- [External services](tech-stack.md#external-services)

**API:**
- [Core API endpoints](api-contracts.md#core-api)
- [LLM Service API](api-contracts.md#llm-service-api)
- [Telegram Service API](api-contracts.md#telegram-service-api)
- [WebSocket API](api-contracts.md#websocket-api)

**Миграция:**
- [Этапы разработки](migration-plan.md#этапы-разработки)
- [Timeline](migration-plan.md#timeline)
- [Команда](migration-plan.md#команда)
- [Риски](migration-plan.md#риски-и-митигация)

---

## 🎓 Для разных ролей

### Backend Developer
**Читать обязательно:**
1. [architecture-go.md](architecture-go.md) - Компоненты и потоки
2. [tech-stack.md](tech-stack.md) - Go технологии
3. [api-contracts.md](api-contracts.md) - API интерфейсы

### Frontend Developer
**Читать обязательно:**
1. [README.md](README.md) - Обзор системы
2. [api-contracts.md](api-contracts.md) - Core API, WebSocket
3. [tech-stack.md](tech-stack.md#frontend) - React stack

### DevOps Engineer
**Читать обязательно:**
1. [architecture-go.md](architecture-go.md#deployment) - Infrastructure
2. [tech-stack.md](tech-stack.md#infrastructure) - Monitoring
3. [migration-plan.md](migration-plan.md#этап-7-deployment--monitoring-2-недели) - Deployment plan

### Product Manager
**Читать обязательно:**
1. [README.md](README.md) - Обзор и roadmap
2. [migration-plan.md](migration-plan.md) - Timeline и бюджет
3. [architecture-go.md](architecture-go.md#обзор-архитектуры) - Бизнес-метрики

### QA Engineer
**Читать обязательно:**
1. [api-contracts.md](api-contracts.md) - API для тестирования
2. [migration-plan.md](migration-plan.md#этап-6-оптимизация-и-доработки-3-недели) - Testing strategy

---

## 📞 Контакты

**Вопросы по документации:**
- Открыть issue в GitHub
- Связаться с архитектором проекта

**Обсуждение:**
- Telegram чат команды
- Weekly sync meetings

---

## 📝 История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2025-10-22 | 1.0 | Первая версия документации |

---

**Статус:** Draft для утверждения  
**Следующий review:** После утверждения архитектуры  
**Автор:** Architecture Team

