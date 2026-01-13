# Документация Go Architecture - Полный индекс

Навигация по всей документации архитектуры Go-версии проекта.

## 📊 Статистика документации

| Метрика | Значение |
|---------|----------|
| **Файлов** | 6 |
| **Строк кода** | 5,305 |
| **Размер** | ~154 KB |
| **Время чтения** | ~100 минут |
| **Версия** | 1.0 |
| **Дата создания** | 22 октября 2025 |

---

## 🗂️ Структура документации

### 1. [README.md](README.md) (145 строк, 5 мин)
**Для кого:** Все  
**Краткое описание:** Введение и навигация по документации

**Содержание:**
- Быстрый старт для разных ролей
- Таблица компонентов
- Сравнение Python vs Go
- MVP scope
- Roadmap

### 2. [SUMMARY.md](SUMMARY.md) (287 строк, 10 мин)
**Для кого:** Все  
**Краткое описание:** Краткий обзор всех решений

**Содержание:**
- Ключевые архитектурные решения
- Выбор технологий с обоснованием
- Timeline миграции
- Бюджет
- Следующие шаги

### 3. [architecture-go.md](architecture-go.md) (1,994 строки, 30 мин)
**Для кого:** Backend, DevOps, PM  
**Краткое описание:** Полная архитектура системы

**Содержание:**
1. Обзор архитектуры
2. Сравнение с Python версией
3. Компоненты системы (Core, Workers, LLM, Telegram, etc)
4. Схема архитектуры
5. Потоки данных (полный цикл обработки вакансии)
6. Модель данных (PostgreSQL schema, Redis structures)
7. Масштабирование
8. Безопасность
9. Deployment (Docker Compose, Kubernetes)

**Ключевые разделы:**
- [Frontend](architecture-go.md#1-frontend-web-ui) - 9 страниц
- [Core](architecture-go.md#2-core-монолитный-go-сервис) - 5 модулей
- [HH.Scheduler](architecture-go.md#3-hhscheduler-планировщик-задач)
- [HH.Worker](architecture-go.md#4-hhworker-распределённые-воркеры)
- [LLM Service](architecture-go.md#5-llm-service-микросервис-для-ai)
- [Telegram Service](architecture-go.md#6-telegram-service-микросервис-для-уведомлений)
- [PostgreSQL Schema](architecture-go.md#модель-данных) - 12 таблиц
- [Deployment](architecture-go.md#deployment)

### 4. [tech-stack.md](tech-stack.md) (793 строки, 20 мин)
**Для кого:** Разработчики всех уровней  
**Краткое описание:** Технологический стек и обоснование выбора

**Содержание:**
1. Backend (Go, Gin, GORM, Redis)
2. Selenium Alternative (chromedp vs rod)
3. LLM Integration (Gemini, OpenAI, GigaChat)
4. Frontend (React, TypeScript, Material-UI)
5. Infrastructure (PostgreSQL, Redis, Monitoring)
6. External Services (ЮКасса, Telegram, hh.ru)
7. Development Tools (Testing, Linting, CI/CD)
8. Cost Estimation

**Ключевые решения:**
- **Go 1.21+** - производительность, concurrency
- **Gin** - web framework (vs Echo)
- **GORM** - ORM для MVP (vs sqlx)
- **chromedp** - Selenium alternative (vs rod)
- **React** - frontend (vs Vue)
- **PostgreSQL** - database (vs MongoDB)
- **Redis** - cache & queue
- **Gemini** - LLM (дешевле OpenAI)

### 5. [api-contracts.md](api-contracts.md) (1,169 строк, 25 мин)
**Для кого:** Backend, Frontend, QA  
**Краткое описание:** API контракты всех сервисов

**Содержание:**
1. **Core API** (15+ endpoints)
   - Auth (register, login, OAuth)
   - Users (profile, settings)
   - Search Config (настройки поиска)
   - Applications (история откликов)
   - Vacancies (рекомендованные)
   - Interviews (собеседования)
   - Billing (подписки, платежи)

2. **LLM Service API** (5 endpoints)
   - Job interest score
   - Answer question
   - Generate cover letter
   - Generate resume
   - Summarize text

3. **Telegram Service API** (3 endpoints)
   - Send notification
   - Request CAPTCHA solution
   - Get CAPTCHA solution

4. **WebSocket API** (real-time updates)

5. **Error Handling** (стандартные коды и форматы)

**Примеры запросов/ответов для всех endpoints**

### 6. [migration-plan.md](migration-plan.md) (917 строк, 20 мин)
**Для кого:** PM, Tech Lead, Stakeholders  
**Краткое описание:** Детальный план миграции с Python

**Содержание:**
1. Обзор миграции (цели, scope)
2. Этапы разработки (0-9)
   - Этап 0: Подготовка (2 недели)
   - Этап 1: Core MVP (4 недели)
   - Этап 2: HH Worker (5 недель)
   - Этап 3: Frontend (4 недели)
   - Этап 4: Billing + Telegram (3 недели)
   - Этап 5: HH Scheduler (1 неделя)
   - Этап 6: Оптимизация (3 недели)
   - Этап 7: Deployment (2 недели)
   - Этап 8: Beta Testing (4 недели)
   - Этап 9: Public Launch (1 неделя)

3. Timeline (6-8 месяцев)
4. Команда (4.5-8.5 FTE)
5. Риски и митигация
6. Критерии успеха (MVP, Beta, Launch)
7. Бюджет ($247,900)
8. ROI расчёты

**Ключевые milestone:**
- Месяц 2: Core MVP готов
- Месяц 4: Worker + Frontend готовы
- Месяц 6: Production deployment
- Месяц 8: Public launch 🚀

---

## 🔍 Навигация по темам

### Архитектура

| Тема | Документ | Раздел |
|------|----------|--------|
| Обзор системы | [architecture-go.md](architecture-go.md) | [Обзор](architecture-go.md#обзор-архитектуры) |
| Компоненты | [architecture-go.md](architecture-go.md) | [Компоненты](architecture-go.md#компоненты-системы) |
| Схема | [architecture-go.md](architecture-go.md) | [Схема](architecture-go.md#схема-архитектуры) |
| Потоки данных | [architecture-go.md](architecture-go.md) | [Потоки](architecture-go.md#потоки-данных) |
| БД модель | [architecture-go.md](architecture-go.md) | [Модель](architecture-go.md#модель-данных) |

### Технологии

| Тема | Документ | Раздел |
|------|----------|--------|
| Backend stack | [tech-stack.md](tech-stack.md) | [Backend](tech-stack.md#backend) |
| Frontend stack | [tech-stack.md](tech-stack.md) | [Frontend](tech-stack.md#frontend) |
| Infrastructure | [tech-stack.md](tech-stack.md) | [Infrastructure](tech-stack.md#infrastructure) |
| Обоснование выбора | [tech-stack.md](tech-stack.md) | Весь документ |

### API

| Тема | Документ | Раздел |
|------|----------|--------|
| Core API | [api-contracts.md](api-contracts.md) | [Core](api-contracts.md#core-api) |
| LLM API | [api-contracts.md](api-contracts.md) | [LLM](api-contracts.md#llm-service-api) |
| Telegram API | [api-contracts.md](api-contracts.md) | [Telegram](api-contracts.md#telegram-service-api) |
| WebSocket | [api-contracts.md](api-contracts.md) | [WebSocket](api-contracts.md#websocket-api) |
| Ошибки | [api-contracts.md](api-contracts.md) | [Errors](api-contracts.md#error-handling) |

### Разработка

| Тема | Документ | Раздел |
|------|----------|--------|
| Timeline | [migration-plan.md](migration-plan.md) | [Timeline](migration-plan.md#timeline) |
| Этапы | [migration-plan.md](migration-plan.md) | [Этапы](migration-plan.md#этапы-разработки) |
| Команда | [migration-plan.md](migration-plan.md) | [Команда](migration-plan.md#команда) |
| Бюджет | [migration-plan.md](migration-plan.md) | [Бюджет](migration-plan.md#бюджет) |
| Риски | [migration-plan.md](migration-plan.md) | [Риски](migration-plan.md#риски-и-митигация) |

### Deployment

| Тема | Документ | Раздел |
|------|----------|--------|
| Docker Compose | [architecture-go.md](architecture-go.md) | [Deployment](architecture-go.md#deployment) |
| Kubernetes | [architecture-go.md](architecture-go.md) | [Production](architecture-go.md#production-kubernetes-будущее) |
| CI/CD | [tech-stack.md](tech-stack.md) | [CI/CD](tech-stack.md#cicd) |
| Мониторинг | [architecture-go.md](architecture-go.md) | [Monitoring](architecture-go.md#мониторинг-и-логирование) |

---

## 🎯 Быстрый поиск

### Для Backend Developer

**Начать здесь:**
1. [architecture-go.md](architecture-go.md) - Компоненты и потоки (30 мин)
2. [tech-stack.md](tech-stack.md) - Go технологии (20 мин)
3. [api-contracts.md](api-contracts.md) - API интерфейсы (25 мин)

**Важные секции:**
- [Core сервис](architecture-go.md#2-core-монолитный-go-сервис)
- [Worker логика](architecture-go.md#4-hhworker-распределённые-воркеры)
- [PostgreSQL schema](architecture-go.md#модель-данных)
- [Gin framework](tech-stack.md#2-web-framework)
- [GORM](tech-stack.md#3-orm-vs-sql-builder)

### Для Frontend Developer

**Начать здесь:**
1. [README.md](README.md) - Обзор (5 мин)
2. [api-contracts.md](api-contracts.md) - Core API (25 мин)
3. [tech-stack.md](tech-stack.md#frontend) - React stack (5 мин)

**Важные секции:**
- [Frontend страницы](architecture-go.md#1-frontend-web-ui)
- [Core API endpoints](api-contracts.md#core-api)
- [WebSocket API](api-contracts.md#websocket-api)
- [React tech stack](tech-stack.md#react-vs-vuejs)

### Для DevOps

**Начать здесь:**
1. [architecture-go.md](architecture-go.md#deployment) - Infrastructure (10 мин)
2. [tech-stack.md](tech-stack.md#infrastructure) - Monitoring (10 мин)
3. [migration-plan.md](migration-plan.md#этап-7-deployment--monitoring-2-недели) - Deployment (5 мин)

**Важные секции:**
- [Docker Compose](architecture-go.md#mvp-docker-compose)
- [Kubernetes](architecture-go.md#production-kubernetes-будущее)
- [Мониторинг](architecture-go.md#мониторинг-и-логирование)
- [CI/CD](tech-stack.md#cicd)

### Для Product Manager

**Начать здесь:**
1. [SUMMARY.md](SUMMARY.md) - Краткий обзор (10 мин)
2. [migration-plan.md](migration-plan.md) - Timeline и бюджет (20 мин)
3. [architecture-go.md](architecture-go.md#обзор-архитектуры) - Бизнес-метрики (5 мин)

**Важные секции:**
- [Timeline](migration-plan.md#timeline)
- [Бюджет](migration-plan.md#бюджет)
- [ROI](migration-plan.md#бюджет)
- [MVP scope](README.md#mvp-scope)
- [Roadmap](README.md#roadmap)
- [Риски](migration-plan.md#риски-и-митигация)

### Для QA Engineer

**Начать здесь:**
1. [api-contracts.md](api-contracts.md) - API (25 мин)
2. [migration-plan.md](migration-plan.md#этап-6-оптимизация-и-доработки-3-недели) - Testing (5 мин)

**Важные секции:**
- [API endpoints](api-contracts.md)
- [Error handling](api-contracts.md#error-handling)
- [Testing strategy](migration-plan.md#неделя-3-testing--bug-fixes)
- [Load testing](migration-plan.md#неделя-3-testing--bug-fixes)

---

## 📖 Словарь терминов

| Термин | Описание |
|--------|----------|
| **Core** | Монолитный Go сервис (API Gateway, User Management, Orchestrator, Billing) |
| **Worker** | Распределённый воркер для обработки вакансий |
| **HH.Scheduler** | Планировщик задач для балансировки нагрузки между workers |
| **LLM Service** | Микросервис для работы с AI (Gemini, OpenAI, GigaChat) |
| **Telegram Service** | Микросервис для Telegram уведомлений и CAPTCHA |
| **Job** | Задача для worker (обработать N вакансий для пользователя X) |
| **MAU** | Monthly Active Users (активные пользователи в месяц) |
| **MVP** | Minimum Viable Product (минимальный продукт) |
| **FTE** | Full-Time Equivalent (полная занятость) |
| **MRR** | Monthly Recurring Revenue (ежемесячный доход) |

---

## 🔗 Ссылки на внешние ресурсы

### Документация технологий

- [Go Documentation](https://go.dev/doc/)
- [Gin Framework](https://gin-gonic.com/docs/)
- [GORM](https://gorm.io/docs/)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [Redis](https://redis.io/docs/)
- [React](https://react.dev/)
- [chromedp](https://github.com/chromedp/chromedp)

### API Документация

- [hh.ru API](https://github.com/hhru/api)
- [Google Gemini](https://ai.google.dev/docs)
- [OpenAI API](https://platform.openai.com/docs)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [ЮKassa API](https://yookassa.ru/developers)

### Инструменты

- [Docker](https://docs.docker.com/)
- [Kubernetes](https://kubernetes.io/docs/)
- [Prometheus](https://prometheus.io/docs/)
- [Grafana](https://grafana.com/docs/)

---

## 📝 Обновления документации

### Как обновлять

1. Создать issue с описанием изменений
2. Создать PR с обновлением документации
3. Code review от Tech Lead
4. Merge в main ветку

### История версий

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2025-10-22 | Первая версия всей документации |

### Планируемые обновления

- [ ] OpenAPI (Swagger) спецификация для Core API
- [ ] Sequence diagrams (mermaid.js)
- [ ] Deployment runbook
- [ ] Troubleshooting guide
- [ ] Performance benchmarks

---

## ✅ Checklist: Прочитал документацию

### Backend Developer
- [ ] Прочитал architecture-go.md
- [ ] Прочитал tech-stack.md
- [ ] Прочитал api-contracts.md
- [ ] Понял Core компоненты
- [ ] Понял Worker логику
- [ ] Понял PostgreSQL schema
- [ ] Готов к разработке

### Frontend Developer
- [ ] Прочитал README.md
- [ ] Прочитал api-contracts.md (Core API)
- [ ] Прочитал tech-stack.md (Frontend секция)
- [ ] Понял страницы приложения
- [ ] Понял API endpoints
- [ ] Готов к разработке

### DevOps
- [ ] Прочитал architecture-go.md (Deployment)
- [ ] Прочитал tech-stack.md (Infrastructure)
- [ ] Прочитал migration-plan.md (Этап 7)
- [ ] Понял Docker Compose setup
- [ ] Понял production deployment
- [ ] Готов к настройке инфраструктуры

### Product Manager
- [ ] Прочитал SUMMARY.md
- [ ] Прочитал migration-plan.md
- [ ] Понял timeline (6-8 месяцев)
- [ ] Понял бюджет ($250k)
- [ ] Понял риски
- [ ] Готов к планированию

---

## 🚀 Готовы начать?

**Следующие шаги:**
1. ✅ Прочитать документацию (используя этот INDEX)
2. ✅ Утвердить архитектуру
3. ✅ Собрать команду
4. ✅ Kick-off встреча
5. ✅ Начать Этап 0: Подготовка

**Let's build! 🎯**

---

**Создано:** 22 октября 2025  
**Версия:** 1.0  
**Статус:** Draft для утверждения  
**Автор:** Architecture Team

