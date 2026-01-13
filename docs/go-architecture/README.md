# Go Architecture Documentation

Документация по архитектуре Go-реализации проекта XX Auto Jobs Applier.

## Содержание

1. **[architecture-go.md](architecture-go.md)** - Полная архитектура системы
2. **[tech-stack.md](tech-stack.md)** - Технологический стек и обоснование выбора
3. **[api-contracts.md](api-contracts.md)** - API контракты всех сервисов
4. **[deployment.md](deployment.md)** - Инструкции по развёртыванию
5. **[migration-plan.md](migration-plan.md)** - План миграции с Python версии

## Быстрый старт

### Для разработчиков

Если вы новый разработчик в проекте, рекомендуем следующий порядок изучения:

1. Прочитайте [architecture-go.md](architecture-go.md) - общее понимание системы
2. Изучите [tech-stack.md](tech-stack.md) - технологии и инструменты
3. Ознакомьтесь с [api-contracts.md](api-contracts.md) - интерфейсы взаимодействия

### Для DevOps

1. [deployment.md](deployment.md) - развёртывание и конфигурация
2. [architecture-go.md#deployment](architecture-go.md#deployment) - инфраструктура

### Для продакт-менеджеров

1. [architecture-go.md#обзор-архитектуры](architecture-go.md#обзор-архитектуры) - бизнес-обзор
2. [migration-plan.md](migration-plan.md) - план и сроки миграции

## Ключевые компоненты

### Core Services (в Docker Compose)

| Сервис | Описание | Порт |
|--------|----------|------|
| **core** | Монолитный Go сервис (API Gateway, User Management, Orchestrator, Billing) | 8080 |
| **hh.scheduler** | Планировщик задач для workers | - |
| **llm** | LLM сервис (промпты, кэш, анонимизация, Resume Builder) | 8081 |
| **telegram** | Telegram бот (уведомления, CAPTCHA, OAuth) | - |
| **frontend** | React/Vue SPA | 3000 |

### Workers

| Worker | IP | Назначение |
|--------|-------|------------|
| **hh.worker.1** | 192.168.0.1 | Обработка вакансий, Selenium |
| **hh.worker.2** | 192.168.0.2 | Обработка вакансий, Selenium |
| **hh.worker.N** | 192.168.0.N | Масштабируемо |

### Хранилища

| Хранилище | Технология | Назначение |
|-----------|------------|------------|
| **DB** | PostgreSQL 15 | Основные данные (users, applications, vacancies, etc) |
| **Redis** | Redis 7 | Очереди задач, кэш, rate limiting |

## Архитектурная схема

См. [architecture-go.md#схема-архитектуры](architecture-go.md#схема-архитектуры)

## Сравнение с Python версией

| Аспект | Python | Go |
|--------|--------|-----|
| Архитектура | Монолит | Микросервисы |
| Пользователи | 1 (локальный) | 10,000+ (SaaS) |
| UI | CLI | Web (React/Vue) |
| БД | YAML файлы | PostgreSQL + Redis |
| Монетизация | - | Подписки (ЮКасса) |
| Масштабирование | Вертикальное | Горизонтальное (workers) |

Подробнее: [architecture-go.md#сравнение-с-python-версией](architecture-go.md#сравнение-с-python-версией)

## MVP Scope

**Сроки:** 3-4 месяца

**Функциональность:**
- ✅ Регистрация/авторизация (Login, OAuth Telegram, OAuth hh.ru)
- ✅ Настройка поиска вакансий (web UI)
- ✅ Автоматические отклики через hh.ru API
- ✅ LLM интеграция (Gemini)
- ✅ Dashboard с статистикой
- ✅ Подписки через ЮКассу (триал 3 дня)
- ✅ Telegram уведомления

**За рамками MVP:**
- ❌ Selenium интеграция (только API)
- ❌ Resume Builder
- ❌ CAPTCHA обработка
- ❌ История диалогов с HR
- ❌ Kubernetes deployment

## Roadmap

### Q1 2026: MVP
- Core + Workers базовая функциональность
- Frontend (React)
- PostgreSQL + Redis
- LLM интеграция
- Биллинг (ЮКасса)
- Telegram бот

### Q2 2026: Full Feature
- Selenium (chromedp)
- Resume Builder
- CAPTCHA handling
- HR dialogs
- Рекомендованные вакансии
- Оптимизации

### Q3 2026: Scale & Optimize
- Горизонтальное масштабирование
- Мониторинг (Prometheus + Grafana)
- CI/CD
- Load testing
- Security audit

### Q4 2026: Enterprise
- Kubernetes deployment
- Multi-region
- Advanced analytics
- Mobile apps (iOS/Android)
- API для партнёров

## Вопросы и поддержка

Если у вас есть вопросы по архитектуре или нужна помощь:

1. Откройте issue в репозитории
2. Свяжитесь с архитектором проекта
3. Присоединяйтесь к обсуждению в Telegram

## Лицензия

MIT License - см. [LICENSE](../../LICENSE)

---

**Последнее обновление:** 22 октября 2025  
**Статус документации:** Draft

