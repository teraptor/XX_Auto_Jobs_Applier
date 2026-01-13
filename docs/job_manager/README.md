# Документация модуля Job Manager

## Назначение

Данная папка содержит полную техническую документацию модуля `job_manager` для реализации на языке Go. Документация предназначена для LLM, который будет осуществлять портирование модуля с Python на Go.

---

## Структура документации

### 📚 Общие документы

#### [00_overview.md](00_overview.md)
**Обзор архитектуры модуля**

**Содержание**:
- Назначение модуля
- Архитектурные принципы
- Структура модуля и компоненты
- Потоки данных
- Взаимодействие с внешними системами
- Управление состоянием
- Обработка ошибок
- Ограничения и лимиты
- Безопасность и приватность

**Когда использовать**: Начните с этого документа для понимания общей картины

---

### 🔌 Контракты и интерфейсы

#### [01_contracts.md](01_contracts.md)
**Контракты всех компонентов**

**Содержание**:
- Соглашения о типах данных
- **HeadHunterAPI** - полное описание интерфейса
  - Конструктор
  - api_request
  - refress_access_token
  - Приватные методы
- **Authenticator** - полное описание интерфейса
  - Конструктор
  - start, is_logged_in
  - handle_login, enter_credentials
  - process_captcha
- **BotFacade** и **BotState** - полное описание интерфейсов
  - Управление состоянием
  - Координация компонентов

**Когда использовать**: Для понимания сигнатур методов и контрактов

---

### 🎯 JobApplier - Основной компонент

#### [05_job_applier_contracts.md](05_job_applier_contracts.md)
**Контракты JobApplier**

**Содержание**:
- Структура данных JobApplier
- Конструктор
- Публичные методы:
  - set_parameters, set_gpt_answerer, set_resume
  - search_vacancies
  - scrape_vacancy
  - start_applying
  - send_response
  - apply_job
  - find_and_handle_questions

**Когда использовать**: Для понимания основной логики поиска и откликов

---

#### [05_job_applier_questions.md](05_job_applier_questions.md)
**Обработка вопросов работодателя**

**Содержание**:
- Типы вопросов (Radio, Checkbox, Text)
- Методы обработки:
  - handle_question
  - _handle_radio_question
  - _handle_checkbox_question
  - _handle_textbox_question
- Интеграция с LLM
- Кэширование ответов
- Обработка ошибок Selenium

**Когда использовать**: Для реализации логики ответов на вопросы через Selenium

---

### 📊 Модели данных

#### [08_data_models.md](08_data_models.md)
**Все структуры данных модуля**

**Содержание**:
- Форматы данных (YAML, JSON)
- **Модели конфигурации**:
  - Secrets
  - SearchConfig (со всеми вложенными структурами)
- **Модели вакансий**:
  - Vacancy (краткая)
  - VacancyDetails (детальная)
  - Job (обработанная)
- **Модели резюме**:
  - ResumeInfo
  - PersonalInfo
  - WorkPreferences
  - EducationDetails
  - ExperienceDetails
- **Модели кэша и результатов**:
  - Cache
  - CompanyApplications
  - AnswersCache
  - SkillStatistics
  - LLMAPICallLog
- **Анонимизация данных**
- **Сериализация/Десериализация**

**Когда использовать**: Для создания struct'ов и понимания формата данных

---

## Порядок изучения документации

### Для полного понимания модуля

```
Шаг 1: Общее понимание
  └─> 00_overview.md
      └─> Получить общую картину архитектуры

Шаг 2: Изучение интерфейсов
  └─> 01_contracts.md
      └─> Понять контракты простых компонентов:
          ├─> HeadHunterAPI
          ├─> Authenticator
          └─> BotFacade

Шаг 3: Модели данных
  └─> 08_data_models.md
      └─> Изучить все структуры данных

Шаг 4: Основная логика
  └─> 05_job_applier_contracts.md
      └─> Понять логику поиска и откликов

Шаг 5: Детали обработки
  └─> 05_job_applier_questions.md
      └─> Детали работы с Selenium и вопросами
```

---

### Для реализации конкретного компонента

**HeadHunterAPI**:
1. `01_contracts.md` → раздел HeadHunterAPI
2. `08_data_models.md` → раздел Модели вакансий
3. `00_overview.md` → раздел HeadHunter API

**Authenticator**:
1. `01_contracts.md` → раздел Authenticator
2. `00_overview.md` → раздел Selenium WebDriver

**BotFacade**:
1. `01_contracts.md` → разделы BotState и BotFacade
2. `00_overview.md` → раздел Потоки данных

**JobApplier**:
1. `05_job_applier_contracts.md` → вся логика
2. `05_job_applier_questions.md` → обработка вопросов
3. `08_data_models.md` → все необходимые модели
4. `00_overview.md` → понимание контекста

---

## Ключевые концепции

### 1. Разделение ответственности

- **HeadHunterAPI** - только HTTP взаимодействие
- **Authenticator** - только вход через Selenium
- **JobApplier** - бизнес-логика откликов
- **ResumeScraper** - сбор и анонимизация резюме
- **SearchCustomizer** - преобразование параметров поиска
- **BotFacade** - координация всех компонентов

### 2. Паттерны проектирования

- **Facade** - BotFacade скрывает сложность
- **Dependency Injection** - зависимости через конструкторы
- **Strategy** - разные режимы работы (MONKEY_MODE, RESUME_MODE, etc.)
- **Cache** - кэширование ответов LLM и данных

### 3. Обработка ошибок

- **API Level** - retry с экспоненциальной задержкой
- **Application Level** - счетчик ошибок, критический порог
- **Selenium Level** - закрытие driver, частичное сохранение

### 4. Безопасность

- **Анонимизация** - замена личных данных на dummy
- **Деанонимизация** - восстановление после LLM
- **Локальное хранение** - все данные на диске
- **Автообновление токенов** - через refresh_token

---

## Важные замечания для реализации

### Требования к Go реализации

1. **Конкурентность**:
   - НЕ использовать goroutines для LLM запросов (последовательные)
   - Можно использовать для параллельной загрузки данных

2. **Обработка ошибок**:
   - Использовать `error` тип
   - Логировать все ошибки
   - Критические ошибки → panic или возврат

3. **Selenium**:
   - Использовать `github.com/tebeka/selenium`
   - Управлять жизненным циклом драйвера
   - Обрабатывать StaleElementReference

4. **YAML/JSON**:
   - `gopkg.in/yaml.v3` для YAML
   - `encoding/json` для JSON
   - Теги struct для маппинга полей

5. **HTTP клиент**:
   - Использовать стандартный `net/http`
   - Таймауты для всех запросов
   - Retry логика

6. **Логирование**:
   - Использовать `log/slog` или аналог
   - Уровни: DEBUG, INFO, WARNING, ERROR, CRITICAL
   - Структурированные логи

---

## Внешние зависимости

### Обязательные библиотеки

```
github.com/tebeka/selenium         # Selenium WebDriver для Go
gopkg.in/yaml.v3                   # YAML парсинг
github.com/go-playground/validator # Валидация struct
```

### Опциональные библиотеки

```
github.com/sirupsen/logrus         # Продвинутое логирование
github.com/spf13/viper             # Конфигурация
go.uber.org/zap                    # Быстрое логирование
```

---

## API эндпоинты HeadHunter

### Базовый URL
`https://api.hh.ru`

### Основные эндпоинты

| Метод | Путь | Назначение |
|-------|------|-----------|
| GET | `/me` | Получение user_id |
| POST | `/token` | Обновление токенов |
| GET | `/resumes/mine` | Список резюме |
| GET | `/resumes/{id}` | Детали резюме |
| POST | `/resumes/{id}/publish` | Подъем резюме |
| GET | `/resumes/{id}/similar_vacancies` | Похожие вакансии |
| GET | `/vacancies` | Поиск вакансий |
| GET | `/vacancies/{id}` | Детали вакансии |
| POST | `/negotiations` | Отправка отклика |
| GET | `/areas` | Справочник регионов |
| GET | `/metro` | Справочник метро |
| GET | `/professional_roles` | Справочник специализаций |
| GET | `/industries` | Справочник отраслей |

### Аутентификация

**Тип**: OAuth 2.0 Bearer Token

**Header**:
```
Authorization: Bearer {access_token}
```

---

## Selenium селекторы

### Авторизация

```
Логин:      [data-qa="login-input-username"]
Пароль:     [data-qa="login-input-password"]
Вход:       [data-qa="account-login-submit"]
Капча:      [data-qa="account-captcha-picture"]
Капча input: [data-qa="account-captcha-input"]
Ошибка:     [data-qa="account-login-error"]
```

### Вопросы работодателя

```
Вопрос:     [data-qa="task-body"]
Radio:      [data-qa="radio-container"]
Checkbox:   [data-qa="checkbox-container"]
Textarea:   textarea
```

### Отклик на вакансию

```
Резюме:     [data-qa="cell-text"] ИЛИ [data-qa="resume-title"]
Письмо:     [data-qa="vacancy-response-popup-form-letter-input"]
Кнопка:     //*[text()='Откликнуться']
```

---

## Конфигурационные файлы

### Расположение

```
data_folder/
├── secrets/
│   └── secrets.yaml           # Приватные данные
├── search_config/
│   └── search_config.yaml     # Параметры поиска
└── output/
    ├── success.yaml           # Успешные отклики
    ├── skipped.yaml           # Пропущенные вакансии
    ├── failed.yaml            # Ошибки
    ├── answers.yaml           # Кэш ответов LLM
    ├── skill_stat.yaml        # Статистика навыков
    ├── resume.yaml            # Данные резюме
    ├── cover_letters.txt      # Сопроводительные письма
    ├── llm_api_calls.yaml     # Логи LLM
    └── last_run.yaml          # Кэш последнего запуска
```

---

## Режимы работы

### Константы из app_config.py

```
MONKEY_MODE = false           # Откликаться на все подряд
RESUME_MODE = false           # Только генерация резюме
COVER_LETTER_MODE = false     # Только генерация писем
SKILL_STAT_MODE = false       # Только сбор статистики
JOB_IS_INTERESTING_THRESH = 70  # Порог интересности (1-100)
MINIMUM_WAIT_TIME_SEC = 10    # Минимум времени на вакансию
```

---

## Метрики и лимиты

### Лимиты откликов

```
max_applies_num: 200              # За один запуск (по умолчанию)
max_total_applies_num: 1500       # Всего (опционально)
MAX_APPLIES_NUM: 100              # Критическое число последовательных ошибок
```

### Временные ограничения

```
MINIMUM_WAIT_TIME_SEC: 10         # Минимум на одну вакансию
Поиск: не чаще раз в 24 часа
Подъем резюме: не чаще раз в 4 часа
Rate limit пауза: 1-2 часа
Капча таймаут: 1 час
```

---

## Версионирование

**Версия документации**: 1.0  
**Дата создания**: 22 октября 2025  
**Язык реализации**: Go  
**Исходный язык**: Python 3.12

---

## Контакты и поддержка

**Автор проекта**: beatwad  
**GitHub**: https://github.com/beatwad/XX_Auto_Jobs_Applier  
**Telegram**: https://t.me/xx_auto_job

---

## Лицензия

Документация и код распространяются по лицензии MIT.

---

<div align="center">

**Удачи в реализации! 🚀**

</div>

