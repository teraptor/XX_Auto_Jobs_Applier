# Обзор системы промптов XX Auto Jobs Applier

## Назначение документации

Данная документация предназначена для LLM, которая будет реализовывать систему промптов на языке Go. Документ описывает архитектуру, последовательность вызовов, логику работы и экономику использования LLM в приложении XX Auto Jobs Applier.

---

## Краткое описание

XX Auto Jobs Applier использует Large Language Models (LLM) для автоматизации процесса откликов на вакансии. LLM выполняет несколько критически важных функций:

1. **Оценка соответствия** кандидата требованиям вакансии
2. **Генерация сопроводительных писем** под конкретную вакансию
3. **Ответы на вопросы работодателя** различных типов
4. **Анализ и улучшение резюме**
5. **Суммаризация описаний вакансий**

**Ключевая особенность**: Все промпты оптимизированы для минимизации токенов при сохранении качества ответов.

---

## Список промптов

### 1. Основные промпты (используются в цикле обработки)

| № | Название промпта | Назначение | Частота вызова |
|---|------------------|------------|----------------|
| 1 | `job_is_interesting` | Оценка соответствия вакансии резюме | 1 раз на вакансию |
| 2 | `text_question_answer_template` | Ответ на текстовый вопрос | 0-5 раз на вакансию |
| 3 | `options_template` | Выбор одного варианта из списка | 0-3 раз на вакансию |
| 4 | `many_options_template` | Выбор нескольких вариантов | 0-2 раз на вакансию |
| 5 | `coverletter_template` | Генерация сопроводительного письма | 1 раз на вакансию (если нет готового) |
| 6 | `summarize_prompt_template` | Суммаризация описания вакансии | 1 раз на вакансию |

### 2. Вспомогательные промпты (редко используемые)

| № | Название | Назначение | Использование |
|---|----------|------------|---------------|
| 7 | `resume_is_interesting` | Оценка резюме для улучшения | Режим RESUME_MODE |
| 8 | `resume_improve` | Рекомендации по улучшению | Режим RESUME_MODE |
| 9 | `parse_contacts_template` | Извлечение контактов из резюме | 1 раз при инициализации |
| 10 | `parse_resume_search_params_template` | Парсинг параметров поиска | Не используется |

### 3. Промпты для генерации резюме (модуль resume_builder)

| № | Название | Назначение | Использование |
|---|----------|------------|---------------|
| 11 | `prompt_header` | Генерация заголовка резюме | Режим RESUME_MODE |
| 12 | `prompt_education` | Генерация секции образования | Режим RESUME_MODE |
| 13 | `prompt_working_experience` | Генерация секции опыта | Режим RESUME_MODE |
| 14 | `prompt_side_projects` | Генерация секции проектов | Режим RESUME_MODE |
| 15 | `prompt_achievements` | Генерация секции достижений | Режим RESUME_MODE |
| 16 | `prompt_certifications` | Генерация секции сертификатов | Режим RESUME_MODE |
| 17 | `prompt_additional_skills` | Генерация секции навыков | Режим RESUME_MODE |

### 4. Устаревшие промпты (не используются)

- `personal_information_template`
- `legal_authorization_template`
- `work_preferences_template`
- `education_details_template`
- `experience_details_template`
- `projects_template`
- `availability_template`
- `salary_expectations_template`
- `certifications_template`
- `languages_template`
- `interests_template`
- `previous_job_template`
- `general_knowledge_template`
- `numeric_question_template`
- `try_to_fix_template`

---

## Общие элементы промптов

### custom_instructions

**Назначение**: Улучшение качества ответов LLM

**Содержание**:
```
##INSTRUCTIONS##
You MUST ALWAYS:
- BE LOGICAL
- You will be PENALIZED for incorrect answers
- NEVER HALLUCINATE
- You DENIED to overlook the critical context
- ALWAYS follow ##Response Rules## and ##Additional Rules##

##Response Rules##
1. USE the language of my message
2. Imagine you are a real-world expert in the field before answering
3. MUST combine deep knowledge and clear thinking
4. I'm going to tip $1,000,000 for the best reply
5. Your answer is CRITICAL for my career
6. Answer in natural, human-like manner
7. DO NOT FORMAT URL links in Markdown
8. DO NOT CHANGE format of phone numbers, emails, etc.
9. DON'T LET ANYONE SUSPECT that you are not human
```

**Применение**: Эти инструкции можно добавлять в начало каждого промпта для повышения качества.

**Размер**: ~200 токенов

---

## Структура промптов

Все промпты следуют единообразной структуре:

```
1. Role Definition
   - "You are an expert in..."
   - Определение роли и экспертизы LLM

2. Task Description
   - "Your task is to..."
   - Четкое описание задачи

3. Input Data
   - ##Job Description##
   - ##Resume##
   - ##Question##
   - Структурированные входные данные

4. Additional Rules
   - Специфичные правила для задачи
   - Ограничения на ответ
   - Примеры желаемого поведения

5. Output Format
   - Строгий формат ответа
   - "Output format (strictly follow this format):"
   - Шаблон ответа

6. Examples (опционально)
   - ##Example 1##
   - ##Example 2##
   - Конкретные примеры input → output
```

---

## Поддерживаемые LLM провайдеры

| Провайдер | Модели | Статус | Цена (input/output за 1M токенов) |
|-----------|--------|--------|-----------------------------------|
| **OpenAI** | gpt-4o | ✅ Поддерживается | $2.50 / $10.00 |
| **OpenAI** | gpt-4o-mini | ✅ Поддерживается | $0.15 / $0.60 |
| **Google** | gemini-2.0-flash | ✅ Рекомендуется | $0.10 / $0.40 |
| **Сбер** | GigaChat | ✅ Поддерживается | ₽200 / ₽200 ($2.00 / $2.00) |
| **Сбер** | GigaChat-Pro | ✅ Поддерживается | ₽1500 / ₽1500 ($15.00 / $15.00) |
| **Сбер** | GigaChat-Max | ✅ Поддерживается | ₽1950 / ₽1950 ($19.50 / $19.50) |
| **Anthropic** | Claude | 🚧 В разработке | - |
| **Ollama** | Local models | 🚧 В разработке | Бесплатно |

**Рекомендуемая модель**: `gemini-2.0-flash`
- Лучшее соотношение цена/качество
- Быстрая скорость ответа
- Поддержка русского языка
- Стоимость: $0.10 / $0.40 за 1M токенов

---

## Анонимизация данных

**Проблема**: LLM видит реальные персональные данные пользователя

**Решение**: Анонимизация перед отправкой в LLM

### Процесс анонимизации

```
Реальные данные → Анонимизация → LLM → Деанонимизация → Использование
```

### Что анонимизируется

| Данные | Заменяется на | Пример |
|--------|---------------|--------|
| ФИО | Dummy имя по полу | Иван Иванов → Алексей Петров |
| Телефон | Dummy номер | +7 (999) 123-45-67 → +7 (999) 000-00-00 |
| Email | Dummy email | ivan@mail.ru → alex@example.com |
| Telegram | Dummy username | @ivan123 → @alex_example |
| WhatsApp | Dummy номер | +7 999 123 45 67 → +7 999 000 00 00 |
| LinkedIn | Dummy ссылка | linkedin.com/in/ivan → linkedin.com/in/alex-petrov |

### Константы для анонимизации

**DUMMY_PERSONAL_INFO_MALE** (мужчины):
```yaml
first_name: "Алексей"
last_name: "Петров"
phone_number: "+7 (999) 000-00-00"
email: "alex.petrov@example.com"
telegram: "@alex_example"
```

**DUMMY_PERSONAL_INFO_FEMALE** (женщины):
```yaml
first_name: "Екатерина"
last_name: "Иванова"
phone_number: "+7 (999) 111-11-11"
email: "ekaterina.ivanova@example.com"
telegram: "@kate_example"
```

### Деанонимизация

**Когда**: Только перед отправкой фактического отклика через API

**Где**: В методе `apply_job()` после генерации сопроводительного письма

**Логика**:
1. Сгенерировать письмо с dummy данными
2. Заменить все вхождения dummy данных на реальные
3. Отправить через API

---

## Кэширование ответов

**Цель**: Избежать повторных вызовов LLM для одинаковых вопросов

### Структура кэша

**Файл**: `data_folder/output/answers.yaml`

**Формат**:
```yaml
"Вопрос работодателя 1": "Ответ 1"
"Вопрос работодателя 2": "Ответ 2"
"How many years of experience with Python?": "5 years"
```

### Логика кэширования

**При получении вопроса**:
1. Нормализовать текст вопроса (trim, lowercase)
2. Проверить наличие в кэше
3. Если есть → использовать готовый ответ
4. Если нет → вызвать LLM → сохранить в кэш

**Когда НЕ использовать кэш**:
- Вопросы с уникальным контекстом (про конкретную вакансию)
- Генерация сопроводительных писем
- Оценка соответствия вакансии

---

## Логирование вызовов LLM

### Структура лога

**Файл**: `data_folder/output/llm_api_calls.yaml`

**Формат записи**:
```yaml
- timestamp: "2025-10-22T15:30:45"
  model: "gemini-2.0-flash"
  prompt_type: "job_is_interesting"
  input_tokens: 1234
  output_tokens: 156
  cost_usd: 0.000185
  latency_ms: 1234
  success: true
  error: null
```

### Что логируется

- ✅ Время вызова
- ✅ Модель LLM
- ✅ Тип промпта
- ✅ Количество input/output токенов
- ✅ Стоимость вызова (USD)
- ✅ Латентность (миллисекунды)
- ✅ Статус (success/error)
- ✅ Текст ошибки (если есть)

### Агрегированная статистика

**В конце сессии** выводится:
```
=== LLM Usage Statistics ===
Total calls: 234
Total tokens: 345,678 (input: 245,678 | output: 100,000)
Total cost: $0.45
Average latency: 1,234 ms
Success rate: 98.7%
```

---

## Управление rate limits

### Проблема

LLM провайдеры ограничивают:
- Запросы в минуту (RPM)
- Токены в минуту (TPM)
- Запросы в день (RPD)

### Стратегия обработки

**1. Обнаружение rate limit**:
```
HTTP 429 Too Many Requests
Header: retry-after: 60
```

**2. Экспоненциальная задержка**:
```
Попытка 1: Задержка = 1 сек
Попытка 2: Задержка = 2 сек
Попытка 3: Задержка = 4 сек
Попытка 4: Задержка = 8 сек
...
```

**3. Максимум попыток**: 5

**4. Логирование**:
```
WARNING: Rate limit exceeded, retrying in 60 seconds...
```

**5. Fallback**:
- Переключение на другую модель (если настроено)
- Пропуск вакансии с логированием

---

## Обработка ошибок LLM

### Типы ошибок

| Тип ошибки | HTTP код | Действие |
|-----------|----------|----------|
| Rate limit | 429 | Retry с задержкой |
| Invalid API key | 401 | Критическая ошибка, остановка |
| Invalid request | 400 | Логировать, пропустить вакансию |
| Server error | 500/502/503 | Retry 3 раза |
| Timeout | - | Retry 3 раза |
| Hallucination | - | Парсинг, валидация, retry |

### Валидация ответов

**Для каждого промпта** проверяется:

1. **Формат ответа**:
   - Наличие ожидаемых полей
   - Соответствие формату output

2. **Содержание**:
   - Не пустая строка
   - Нет фраз типа "I don't know", "No information"

3. **Специфичные проверки**:
   - `job_is_interesting`: Score должен быть числом 1-100
   - `options_template`: Ответ должен быть из списка options
   - `coverletter_template`: Длина > 50 символов

### Обработка некорректных ответов

```
Шаг 1: LLM вернул некорректный ответ
Шаг 2: Логировать ошибку
Шаг 3: Попытка 2 (с модифицированным промптом)
Шаг 4: Если снова ошибка → возврат дефолтного значения
```

**Дефолтные значения**:
- `job_is_interesting`: False (пропустить вакансию)
- `text_question_answer`: "Нет информации"
- `options_template`: Первый вариант из списка
- `coverletter_template`: Использовать фиксированное письмо

---

## Оптимизация промптов

### Методы сокращения токенов

**1. Удаление избыточности**:
```
❌ Before: "Please analyze the following job description carefully..."
✅ After: "Analyze job description:"
```

**2. Использование сокращений**:
```
❌ Before: "##Additional Rules and Guidelines##"
✅ After: "##Rules##"
```

**3. Структурированный формат**:
```
❌ Before: Длинное описание в прозе
✅ After: Bullet points и нумерованные списки
```

**4. Удаление примеров** (где возможно):
- Примеры занимают много токенов
- Использовать только для сложных задач

**5. Компрессия данных резюме**:
```
❌ Before: Полное JSON резюме (5000 токенов)
✅ After: Только релевантные поля (2000 токенов)
```

### Измерение эффективности

**Метрики**:
- Токены на один вызов
- Стоимость на одну вакансию
- Качество ответов (manual review)

**Целевые показатели**:
- job_is_interesting: < 2000 input токенов
- text_question: < 1500 input токенов
- coverletter: < 3000 input токенов

---

## Заключение

Система промптов XX Auto Jobs Applier оптимизирована для:
- ✅ Минимизации стоимости LLM вызовов
- ✅ Высокого качества ответов
- ✅ Быстрой обработки вакансий
- ✅ Надежной работы с различными LLM провайдерами

**Следующие разделы**:
- [01_vacancy_processing_flow.md](01_vacancy_processing_flow.md) - Детальный процесс обработки вакансии
- [02_prompt_details.md](02_prompt_details.md) - Подробное описание каждого промпта
- [03_cost_calculation.md](03_cost_calculation.md) - Расчет стоимости для разных сценариев

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Статус**: Готово к реализации на Go

