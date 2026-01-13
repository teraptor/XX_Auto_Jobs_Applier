# Модуль Job Manager - Обзор архитектуры

## Назначение модуля

Модуль `job_manager` отвечает за полный цикл автоматизированного поиска и подачи откликов на вакансии на платформе HeadHunter (hh.ru). Это центральный модуль приложения, координирующий работу всех остальных компонентов.

---

## Архитектурный обзор

### Принципы проектирования

1. **Модульность**: Каждый компонент отвечает за свою область ответственности
2. **Слабая связанность**: Компоненты взаимодействуют через четко определенные интерфейсы
3. **Инверсия зависимостей**: Зависимости передаются через конструкторы
4. **Единая ответственность**: Каждый класс решает одну задачу
5. **Паттерн Facade**: BotFacade скрывает сложность взаимодействия компонентов

---

## Структура модуля

```
job_manager/
├── api.go                  # Клиент для HeadHunter API
├── authenticator.go        # Аутентификация через Selenium
├── bot_facade.go          # Фасад для координации компонентов
├── job_applier.go         # Логика поиска и откликов
├── resume_scraper.go      # Сбор данных резюме
└── search_customizer.go   # Настройка параметров поиска
```

---

## Компоненты модуля

### 1. HeadHunterAPI (api.go)
**Назначение**: HTTP клиент для взаимодействия с REST API HeadHunter

**Ответственность**:
- Аутентификация через OAuth 2.0
- Выполнение HTTP запросов к API
- Автоматическое обновление токенов доступа
- Обработка ошибок API (rate limits, истекшие токены)
- Управление пользовательскими данными (user_id)

**Ключевые операции**:
- Поиск вакансий
- Получение деталей вакансии
- Отправка откликов
- Получение данных резюме
- Обновление токенов

---

### 2. Authenticator (authenticator.go)
**Назначение**: Веб-автоматизация для входа на сайт hh.ru

**Ответственность**:
- Управление Selenium WebDriver
- Вход на сайт с логином и паролем
- Проверка статуса авторизации
- Обработка CAPTCHA через Telegram интеграцию
- Сохранение сессий браузера

**Ключевые операции**:
- Проверка статуса входа (is_logged_in)
- Ввод учетных данных
- Обработка капчи
- Валидация корректности пароля

---

### 3. BotFacade (bot_facade.go)
**Назначение**: Фасад для координации всех компонентов

**Ответственность**:
- Инициализация и конфигурация компонентов
- Валидация состояния перед операциями
- Управление жизненным циклом процесса
- Координация взаимодействия между компонентами

**Управление состоянием**:
- `parameters_set` - параметры установлены
- `resume_set` - резюме загружено
- `search_parameters_set` - параметры поиска установлены
- `gpt_answerer_set` - LLM компонент настроен

**Ключевые операции**:
- Установка параметров (set_parameters)
- Загрузка резюме (set_resume)
- Настройка поиска (set_search_parameters)
- Подключение LLM (set_gpt_answerer)
- Запуск процесса (start_apply)

---

### 4. JobApplier (job_applier.go)
**Назначение**: Ядро модуля - реализация логики поиска и откликов

**Ответственность**:
- Поиск вакансий по заданным критериям
- Оценка соответствия вакансии кандидату
- Генерация откликов
- Ответы на вопросы работодателя
- Генерация сопроводительных писем
- Управление лимитами и статистикой
- Обработка ошибок и восстановление
- Кэширование данных

**Ключевые операции**:
- Поиск вакансий (search_vacancies)
- Сбор данных вакансии (scrape_vacancy)
- Отправка отклика (send_response)
- Применение к вакансии (apply_job)
- Обработка вопросов (handle_question)
- Генерация отчета (send_report)

**Режимы работы**:
- **Нормальный режим**: AI фильтрация + отклики
- **MONKEY_MODE**: Отклик на все вакансии
- **COVER_LETTER_MODE**: Только генерация писем
- **RESUME_MODE**: Только генерация резюме
- **SKILL_STAT_MODE**: Сбор статистики навыков

---

### 5. ResumeScraper (resume_scraper.go)
**Назначение**: Сбор и структурирование данных резюме пользователя

**Ответственность**:
- Получение данных резюме через API
- Парсинг структуры резюме
- Анонимизация персональных данных для LLM
- Деанонимизация данных в ответах LLM
- Подъем резюме в поиске
- Сохранение данных резюме

**Извлекаемые данные**:
- Персональная информация
- Опыт работы
- Образование
- Навыки и технологии
- Сертификаты
- Языки
- Контактная информация
- Предпочтения по работе

**Ключевые операции**:
- Получение ID резюме (get_id_of_selected_resume)
- Сбор информации (get_resume_info)
- Анонимизация (anonymize_personal_information)
- Деанонимизация (deanonymize_personal_information)
- Подъем резюме (raise_resume)

---

### 6. SearchCustomizer (search_customizer.go)
**Назначение**: Преобразование параметров поиска в API запросы

**Ответственность**:
- Конвертация пользовательских настроек в API параметры
- Получение ID регионов, метро, специализаций
- Разрешение названий в идентификаторы через API
- Формирование параметров запроса

**Обрабатываемые параметры**:
- Ключевые слова и область поиска
- Опыт работы
- Тип занятости и график
- География (регионы, метро)
- Специализация и отрасль
- Зарплата и валюта
- Метки вакансий
- Сортировка и период

**Ключевые операции**:
- Установка параметров (set_advanced_search_params)
- Получение ID регионов (_get_area_ids)
- Получение ID метро (_get_metro_ids)
- Получение ID специализации (_get_professional_role_id)
- Получение ID отраслей (_get_industry_ids)

---

## Потоки данных

### Поток инициализации

```
main.py
  └─> создает компоненты:
      ├─> HeadHunterAPI (secrets)
      ├─> GPTAnswerer (llm_api_key)
      ├─> ResumeScraper (api, job_title, gpt_answerer)
      ├─> SearchCustomizer (api)
      ├─> JobApplier (api, resume_scraper, search_customizer)
      └─> BotFacade (resume_scraper, search_customizer, job_applier)
  └─> BotFacade.set_parameters(parameters)
  └─> BotFacade.set_resume()
  └─> BotFacade.set_search_parameters(parameters)
  └─> BotFacade.set_gpt_answerer(gpt_answerer, parameters)
  └─> BotFacade.start_apply()
```

### Поток обработки вакансии

```
JobApplier.start_applying()
  └─> Цикл по страницам:
      └─> search_vacancies(page_num)
          ├─> API: GET /resumes/{id}/similar_vacancies (похожие вакансии)
          └─> API: GET /vacancies (основной поиск)
      └─> Для каждой вакансии:
          └─> send_response(vacancy)
              ├─> scrape_vacancy(vacancy)
              │   ├─> Парсинг краткой информации
              │   └─> API: GET /vacancies/{id} (детали)
              │
              ├─> Проверки:
              │   ├─> Черный список компаний
              │   ├─> Дубликаты (уже откликались)
              │   └─> Лимиты откликов
              │
              ├─> GPTAnswerer.job_is_interesting() (если не MONKEY_MODE)
              │   └─> Оценка 1-100, сравнение с JOB_IS_INTERESTING_THRESH
              │
              └─> apply_job(vacancy, company_name, job_title, job)
                  ├─> Генерация сопроводительного письма:
                  │   ├─> Фиксированное (если cover_letter задано)
                  │   └─> GPTAnswerer.write_cover_letter()
                  │
                  ├─> API: POST /negotiations (отклик)
                  │
                  └─> Если требуется тест:
                      ├─> Инициализация Selenium driver
                      ├─> Authenticator.start() (вход на сайт)
                      ├─> Переход на страницу отклика
                      ├─> find_and_handle_questions()
                      │   ├─> handle_question() для каждого вопроса:
                      │   │   ├─> Radio: GPTAnswerer.select_one_answer_from_options()
                      │   │   ├─> Checkbox: GPTAnswerer.select_many_answers_from_options()
                      │   │   └─> Text: GPTAnswerer.answer_question_textual_wide_range()
                      │   ├─> _select_correct_resume()
                      │   ├─> _enter_cover_letter()
                      │   └─> Click "Откликнуться"
                      └─> Закрытие driver
```

---

## Взаимодействие с внешними системами

### HeadHunter API

**Базовый URL**: `https://api.hh.ru`

**Аутентификация**: OAuth 2.0 (Bearer token)

**Основные эндпоинты**:

| Метод | Эндпоинт | Назначение |
|-------|----------|------------|
| GET | `/me` | Получение user_id |
| POST | `/token` | Обновление токенов |
| GET | `/resumes/mine` | Список резюме пользователя |
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

**Обработка ошибок**:
- `too_many_requests` → пауза 1-2 часа
- `token_expired` → автообновление токена
- `test_required` → запуск Selenium для ответа на вопросы
- `limit_exceeded` → достигнут лимит откликов
- `already_applied` → уже откликались
- `application_denied` → вакансия неактивна

---

### Selenium WebDriver

**Браузер**: Chrome

**Назначение**:
- Вход на сайт hh.ru
- Ответ на вопросы работодателя
- Выбор резюме
- Ввод сопроводительного письма
- Обработка капчи

**Профиль браузера**: Сохраняется в `chrome_profile/` для переиспользования сессий

**Элементы для взаимодействия**:
- Логин: `[data-qa="login-input-username"]`
- Пароль: `[data-qa="login-input-password"]`
- Вход: `[data-qa="account-login-submit"]`
- Капча: `[data-qa="account-captcha-picture"]`
- Вопросы: `[data-qa="task-body"]`
- Radio: `[data-qa="radio-container"]`
- Checkbox: `[data-qa="checkbox-container"]`
- Текст: `textarea`
- Резюме: `[data-qa="cell-text"]` или `[data-qa="resume-title"]`
- Письмо: `[data-qa="vacancy-response-popup-form-letter-input"]`
- Отклик: кнопка с текстом "Откликнуться"

---

### LLM (AI компонент)

**Интерфейс**: GPTAnswerer

**Используемые методы**:
- `job_is_interesting(job_description, resume)` → int (1-100)
- `write_cover_letter(job_description, resume)` → string
- `select_one_answer_from_options(question, options)` → string
- `select_many_answers_from_options(question, options)` → []string
- `answer_question_textual_wide_range(question)` → string
- `resume_improvement_recommendations()` → string
- `parse_contacts(about_me_text)` → map[string]string

**Передаваемые данные**: Анонимизированные (личные данные заменены на dummy)

---

### Telegram

**Интерфейс**: TelegramManager

**Используемые методы**:
- `process_captcha()` - отправка изображения капчи
- `TelegramReportSender.send_telegram_report()` - отчет о работе

**Топики**:
- Errors (TG_ERR_TOPIC_ID) - ошибки
- Captcha (TG_CAPTCHA_TOPIC_ID) - капчи
- Reports (TG_REPORT_TOPIC_ID) - отчеты

---

## Управление состоянием

### Кэш (last_run.yaml)
- `last_run` - время последнего запуска (ISO 8601)
- `last_apply` - время последнего отклика
- `success_applies_num` - количество успешных откликов в сессии
- `total_applies_num` - общее количество откликов

### Выходные файлы (data_folder/output/)

| Файл | Формат | Назначение |
|------|--------|-----------|
| `success.yaml` | YAML | Успешные отклики |
| `skipped.yaml` | YAML | Пропущенные вакансии + причина |
| `failed.yaml` | YAML | Ошибки при откликах |
| `answers.yaml` | YAML | Кэш ответов LLM на вопросы |
| `skill_stat.yaml` | YAML | Статистика навыков |
| `resume.yaml` | YAML | Данные резюме |
| `cover_letters.txt` | Text | Сопроводительные письма |
| `llm_api_calls.yaml` | YAML | Логи запросов к LLM |
| `resume_recommendations.yaml` | YAML | Рекомендации по резюме |

---

## Обработка ошибок

### Стратегия обработки

**Уровни**:
1. **API Level**: Retry с экспоненциальной задержкой, автообновление токенов
2. **Application Level**: Счетчик последовательных ошибок, критический порог MAX_APPLIES_NUM
3. **Selenium Level**: Закрытие driver при ошибке, сохранение частичного прогресса

**Критические ошибки**:
- Последовательно MAX_APPLIES_NUM ошибок → остановка с отчетом
- Неверный пароль → остановка
- Капча не решена за 1 час → остановка
- Невалидная конфигурация → остановка до запуска

**Восстановимые ошибки**:
- Rate limit → пауза 1-2 часа
- Истекший токен → автообновление
- Timeout → повтор
- Вакансия неактивна → skip

---

## Ограничения и лимиты

### Лимиты откликов
- `max_applies_num` - за один запуск (по умолчанию 200)
- `max_total_applies_num` - всего за все время (опционально, 1500)
- `apply_once_at_company` - не более 1 отклика на компанию

### Временные ограничения
- Минимум 10 секунд на обработку одной вакансии (MINIMUM_WAIT_TIME_SEC)
- Максимум 400 вакансий за запуск (защита от бесконечного цикла)
- Поиск запускается не чаще раз в 24 часа
- Подъем резюме не чаще раз в 4 часа

### API лимиты HeadHunter
- Rate limits → автоматическая пауза
- Лимит откликов → остановка с сохранением прогресса

---

## Безопасность и приватность

### Анонимизация данных для LLM
Замена реальных данных на dummy перед отправкой в LLM:
- ФИО → вымышленное имя
- Телефон → dummy номер
- Email → dummy email
- GitHub → dummy username
- Другие контакты → dummy значения

**Механизм**: 
- `anonymize_personal_information()` - перед отправкой в LLM
- `deanonymize_personal_information()` - после получения ответа

### Хранение токенов
- Токены хранятся в `secrets.yaml`
- Автообновление через refresh_token
- Обновленные токены перезаписываются в файл

---

## Производительность

### Оптимизации
- Кэширование ответов LLM в `answers.yaml`
- Сохранение сессий браузера в `chrome_profile/`
- Пагинация поиска вакансий (10 за запрос)
- Двухэтапный поиск: сначала похожие на резюме, затем общий
- Проверка дубликатов перед API запросами

### Узкие места
- LLM запросы (самые медленные)
- Selenium операции (ответ на вопросы)
- API запросы к hh.ru

---

## Метрики и мониторинг

### Отслеживаемые метрики
- Количество обработанных вакансий
- Количество успешных откликов
- Количество пропущенных вакансий (+ причины)
- Количество ошибок (последовательных и общих)
- Стоимость LLM запросов
- Статистика требуемых навыков

### Логирование
- Все действия логируются через logger
- Критические ошибки отправляются в Telegram
- Отчет о работе отправляется в конце сессии

---

## Следующие документы

1. [Контракты и интерфейсы](01_contracts.md)
2. [HeadHunterAPI - детали](02_api.md)
3. [Authenticator - детали](03_authenticator.md)
4. [BotFacade - детали](04_bot_facade.md)
5. [JobApplier - детали](05_job_applier.md)
6. [ResumeScraper - детали](06_resume_scraper.md)
7. [SearchCustomizer - детали](07_search_customizer.md)
8. [Модели данных](08_data_models.md)
9. [Алгоритмы и логика](09_algorithms.md)

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Назначение**: Спецификация для реализации на Go

