# Настройка поиска вакансий на hh.ru

## 📋 Оглавление

1. [Введение](#введение)
2. [Архитектура системы поиска](#архитектура-системы-поиска)
3. [Конфигурационные файлы](#конфигурационные-файлы)
4. [Процесс настройки поиска](#процесс-настройки-поиска)
5. [Преобразование параметров](#преобразование-параметров)
6. [Применение параметров поиска](#применение-параметров-поиска)
7. [Роль LLM в фильтрации вакансий](#роль-llm-в-фильтрации-вакансий)
8. [Алгоритм оценки вакансий](#алгоритм-оценки-вакансий)
9. [Параметры конфигурации](#параметры-конфигурации)
10. [Примеры использования](#примеры-использования)
11. [Отладка и оптимизация](#отладка-и-оптимизация)

---

## Введение

Система автоматизированного поиска вакансий использует **двухуровневую архитектуру фильтрации**:

1. **Структурированный поиск** через API HeadHunter (hh.ru)
2. **Интеллектуальная фильтрация** через LLM (Large Language Model)

Это позволяет:
- ✅ Находить релевантные вакансии с точностью до конкретных требований
- ✅ Учитывать личные интересы и предпочтения кандидата
- ✅ Избегать overqualification (вакансии ниже уровня кандидата)
- ✅ Соблюдать параметры поиска, заданные пользователем

---

## Архитектура системы поиска

```
┌─────────────────────────────────────────────────────────────────┐
│                    Пользовательская конфигурация                │
│                     (search_config.yaml)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ConfigValidator                            │
│         (валидация через Pydantic модель SearchConfig)          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SearchCustomizer                            │
│  • Преобразование параметров в ID через API hh.ru              │
│  • Регионы → ID регионов                                        │
│  • Метро → ID станций                                           │
│  • Специализация → ID роли (алгоритм Левенштейна)               │
│  • Отрасли → ID отраслей                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        JobApplier                               │
│         Двухэтапный поиск вакансий:                             │
│  1. /resumes/{id}/similar_vacancies (похожие на резюме)         │
│  2. /vacancies (общий поиск по параметрам)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GPTAnswerer                                │
│  • Трансформация параметров в читаемый текст                    │
│  • Оценка соответствия вакансии резюме                          │
│  • Проверка соответствия параметрам поиска                      │
│  • Оценка Score (1-100)                                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  Score >= 70 ?
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
    ✅ Откликаемся          ❌ Пропускаем
```

---

## Конфигурационные файлы

### Основные файлы

| Файл | Назначение |
|------|------------|
| `data_folder/search_config/search_config.yaml` | Параметры поиска вакансий |
| `data_folder/secrets/secrets.yaml` | Токены доступа и секретные ключи |
| `data_folder_example/search_config/search_config.yaml` | Эталонный пример с комментариями |

### Структура search_config.yaml

```yaml
# Обязательные поля
job_title: Программист Python  # Должность (ОБЯЗАТЕЛЬНО)
user_id: '168901459'           # ID на hh.ru (ОБЯЗАТЕЛЬНО)
max_applies_num: 200           # Лимит откликов (ОБЯЗАТЕЛЬНО)

# Поисковые параметры
keywords: Аналитик, программист
professional_role: Программист
industry: Банк, Финансовые услуги
area: Москва, Санкт-Петербург
metro: Павелецкая, Новокосино
salary: 300000
currency:
  RUR: true
  EUR: false
  USD: false

# Требования к кандидату
experience:
  moreThan6: true
education:
  higher: true

# Условия работы
employment:
  full: true
  part: true
schedule:
  fullDay: true
  remote: true

# Дополнительные фильтры
vacancy_label:
  accredited_it: true
  with_address: true
job_blacklist: Google, Meta
apply_once_at_company: true
```

---

## Процесс настройки поиска

### Шаг 1: Загрузка и валидация конфигурации

**Файл:** `main.py`

```python
# Валидация параметров через Pydantic
config_validator = ConfigValidator()
secrets = config_validator.validate_secrets(SECRETS_FILE)
parameters = config_validator.validate_search_config(
    SEARCH_CONFIG_FILE, SEARCH_CONFIG_FILE_TMP, secrets
)
```

**Проверяется:**
- ✅ Обязательные поля присутствуют
- ✅ Типы данных корректны
- ✅ Значения в допустимых диапазонах
- ✅ Только одно значение `true` для эксклюзивных параметров

### Шаг 2: Инициализация компонентов

**Файл:** `bot_facade.py`

```python
bot = BotFacade(resume_component, search_component, apply_component)
bot.set_parameters(parameters)           # Общие параметры
bot.set_resume()                         # Информация о резюме
bot.set_search_parameters(parameters)    # Параметры поиска
bot.set_gpt_answerer(gpt_answerer, parameters)  # LLM компонент
```

### Шаг 3: Установка параметров поиска

**Файл:** `search_customizer.py`

```python
def set_advanced_search_params(self, parameters: Dict[str, Any]) -> None:
    """Установка параметров поиска"""
    self.search_params["text"] = parameters.get("keywords") or ""
    self.search_params["search_field"] = self._get_search_field_ids(parameters)
    self.search_params["experience"] = self._get_experience_id(parameters)
    self.search_params["employment"] = self._get_employment_ids(parameters)
    self.search_params["schedule"] = self._get_schedule_ids(parameters)
    self.search_params["area"] = self._get_area_ids(parameters)
    self.search_params["metro"] = self._get_metro_ids(parameters)
    self.search_params["professional_role"] = self._get_professional_role_id(parameters)
    self.search_params["industry"] = self._get_industry_ids(parameters)
    self.search_params["salary"] = parameters.get("salary") or 0
    self.search_params["currency"] = self._get_currency_id(parameters)
    self.search_params["label"] = self._get_vacancy_label_ids(parameters)
    self.search_params["only_with_salary"] = parameters.get("only_with_salary") or False
    self.search_params["period"] = self._get_period(parameters)
    self.search_params["order_by"] = self._get_order_by_id(parameters)
    self.search_params["part_time"] = self._get_part_time_ids(parameters)
```

---

## Преобразование параметров

### Географические параметры

#### 1. Регионы (`_get_area_ids`)

**Алгоритм:**
1. Получить список стран из резюме (гражданство или разрешение на работу)
2. Запросить дерево регионов через API: `https://api.hh.ru/areas`
3. Найти регион/город по точному совпадению названия (case-insensitive)
4. Вернуть список ID регионов

**Пример:**
```python
# Ввод: "Москва, Санкт-Петербург"
# Вывод: ["1", "2"]
```

**Важно:** Разделитель для регионов - **точка с запятой (`;`)**, а не запятая!

```yaml
# Правильно:
area: Москва;Санкт-Петербург

# Неправильно:
area: Москва, Санкт-Петербург  # Интерпретируется как один регион
```

#### 2. Метро (`_get_metro_ids`)

**Алгоритм:**
1. Использовать ID регионов из предыдущего шага
2. Запросить данные о метро: `https://api.hh.ru/metro`
3. Искать станции только в выбранных городах
4. Вернуть список ID станций

**Пример:**
```python
# Ввод: "Павелецкая, Комсомольская"
# Регионы: ["1"] (Москва)
# Вывод: ["2.345", "2.346"]
```

### Профессиональные параметры

#### 3. Специализация (`_get_professional_role_id`)

**Алгоритм: Нечеткий поиск через расстояние Левенштейна**

1. Получить справочник специализаций: `https://api.hh.ru/professional_roles`
2. Для каждой роли вычислить расстояние Левенштейна
3. Выбрать роль с минимальным расстоянием

**Пример:**
```python
# Ввод: "Програмист"  (с опечаткой)
# Нашли: "Программист, разработчик"  (расстояние = 1)
# Вывод: "96"
```

**Преимущество:** Устойчивость к опечаткам и разным формулировкам.

#### 4. Отрасль (`_get_industry_ids`)

**Алгоритм: Точное совпадение**

1. Получить справочник отраслей: `https://api.hh.ru/industries`
2. Точное совпадение названий (case-insensitive)
3. Вернуть список ID отраслей

**Пример:**
```python
# Ввод: "Банки, Финансовые услуги"
# Вывод: ["7", "33"]
```

### Временные и числовые параметры

#### 5. Период публикации (`_get_period`)

**Преобразование:**
```python
{
    "all_time": 0,      # За всё время
    "month": 30,        # За месяц
    "week": 7,          # За неделю
    "three_days": 3,    # За 3 дня
    "one_day": 1        # За сутки
}
```

#### 6. Валюта (`_get_currency_id`)

**Значения:** `RUR`, `EUR`, `USD`

**Важно:** Только одно значение может быть `true`!

---

## Применение параметров поиска

### Двухэтапный поиск вакансий

**Файл:** `job_applier.py` → `search_vacancies()`

#### Этап 1: Вакансии, похожие на резюме

```python
# API: /resumes/{resume_id}/similar_vacancies
resume_vacancies = self.api.api_request(
    f"https://api.hh.ru/resumes/{self.resume_id}/similar_vacancies",
    params=search_params,
)
```

**Преимущества:**
- 🎯 Высокая релевантность (hh.ru сам сопоставляет с резюме)
- 🚀 Приоритет в обработке

#### Этап 2: Общий поиск

```python
# API: /vacancies
search_params_["text"] = self.job_title
main_vacancies = self.api.api_request(
    "https://api.hh.ru/vacancies",
    params=search_params_,
)
```

**Расширяет поиск** вакансиями по должности с учётом всех фильтров.

### Формирование запроса к API

```python
search_params = {"page": page_num, "per_page": 10}

# Добавление только непустых параметров
for key, value in self.search_component.search_params.items():
    if value:
        search_params[key] = value
```

**Пример итогового запроса:**
```python
{
    "page": 0,
    "per_page": 10,
    "text": "Python разработчик",
    "area": ["1", "2"],              # Москва, СПб
    "professional_role": "96",       # Программист
    "salary": 300000,
    "currency": "RUR",
    "experience": ["between3And6"],
    "schedule": ["fullDay", "remote"],
    "period": 30
}
```

---

## Роль LLM в фильтрации вакансий

### Трансформация параметров в текст

**Файл:** `json_to_readable.py` → `transform_search_config_data()`

Параметры преобразуются в **человекочитаемый формат** для LLM:

```python
def transform_search_config_data(data: dict) -> str:
    """
    Превращает YAML-конфиг в структурированный текст
    для передачи в LLM
    """
```

**Пример вывода:**

```
Параметры Поиска Вакансий
===

ОСНОВНЫЕ ПАРАМЕТРЫ ПОИСКА:
  Должность для поиска: Программист Python
  Ключевые слова: Аналитик, программист
  Специализация: Программист
  Регионы: Москва, Санкт-Петербург
  Метро: Павелецкая, Новокосино

ФИНАНСОВЫЕ УСЛОВИЯ:
  Уровень дохода от: 300000
  Показывать только с указанной з/п: Нет
  Валюта: Рубли (RUR)

ОБРАЗОВАНИЕ И ОПЫТ:
  Требуемый опыт: Более 6 лет

УСЛОВИЯ РАБОТЫ:
  Тип занятости: Полная занятость, Частичная занятость
  График работы: Полный день, Удаленная работа

ДРУГИЕ ПАРАМЕТРЫ ВАКАНСИИ:
  С адресом, От аккредитованных ИТ-компаний

СПИСКИ ИСКЛЮЧЕНИЙ И ШАБЛОНЫ:
  Черный список компаний: Google, Meta
```

### Установка параметров в GPTAnswerer

**Файл:** `llm_manager.py`

```python
def set_search_parameters(self, parameters: dict) -> None:
    """Устанавливаем параметры поиска вакансий."""
    self.search_parameters = transform_search_config_data(parameters)
```

### Промпт для оценки вакансии

**Файл:** `prompts.py` → `job_is_interesting`

```python
job_is_interesting = """
You are an expert in recruitment.
Evaluate whether the provided resume meets the requirements specified in the job description 
and whether job description meets the search parameters.
Determine if the candidate is suitable for this job based on the provided information.

##Job Description##
```
{job_description}
```

##Resume##
```
{resume}
```

##Search Parameters##
```
{search_parameters}
```

##Additional Rules##
- Identify key requirements from the job description, distinguishing strict requirements (mandatory) from soft requirements (desirable).
- Determine relevant qualifications from the resume and skills list.
- Compare qualifications to the requirements, ensuring all strict requirements are met.
- A 1-year difference in experience is allowed if applicable, as experience is typically a strict requirement.
- Assign a suitability score from 1 to 100, where 1 means that candidate meets no requirements, and 100 means that candidate meets all requirements.
- If at least one of the skills levels in resume is significanly lower than the requirements (e.g. required level is "advanced" but in resume it is "elementary"), subtract 20 points from the overall score.
- If vacancy requires year or less of experience and candidate has 4 or more years of experience, subtract 10 points from the overall score.
- If the job aligns with one or more of the candidate's interests, add 10 point to the overall score.
- **If vacancy doesn't match one or more of search parameters, subtract 20 points from the overall score for each search parameter that it doesn't match.**
- Provide a brief justification for the score, indicating which requirements are met and which are not.

Output format (strictly follow this format):
Score: [numeric score]
Reasoning: [brief explanation]
Do not include anything else in the response beyond the score and reasoning.
"""
```

**Ключевое правило штрафов:**

| Несоответствие | Штраф |
|----------------|-------|
| Параметр поиска не совпадает | **-20 баллов** за каждый |
| Уровень навыка значительно ниже | **-20 баллов** |
| Overqualified (опыт 4+ года для junior) | **-10 баллов** |
| Совпадение с интересами | **+10 баллов** |

### Вызов LLM для оценки

**Файл:** `llm_manager.py` → `job_is_interesting()`

```python
def job_is_interesting(self) -> bool | None:
    """
    Спрашиваем у LLM, может ли быть интересна
    данная вакансия с учетом нашего резюме, навыков и интересов
    """
    logger.info("Проверяем, насколько вакансия может быть интересна.")
    chain = self._create_chain(prompts.job_is_interesting)
    
    output = chain.invoke({
        "resume": self.resume_readable,
        "job_description": self.job_readable,
        "search_parameters": self.search_parameters,
    })
    
    # Парсинг ответа
    score = re.search(r"Score: (\d+)", output).group(1)
    reasoning = re.search(r"Reasoning: (.+)", output, re.DOTALL).group(1)
    
    logger.info(f"Степень 'интересности' вакансии: {score}")
    
    if int(score) < JOB_IS_INTERESTING_THRESH:
        logger.info(f"Работа не интересна: {reasoning}")
        return False
    
    return True
```

### Применение в процессе отклика

**Файл:** `job_applier.py` → `send_repsonse()`

```python
# Задать вакансию в LLM для оценки
self.gpt_answerer.set_job(job)

if MONKEY_MODE is True:
    # В 'режиме обезьяны' любая вакансия считается интересной
    job_is_interesting = True
else:
    # Иначе просить LLM оценить вакансию
    job_is_interesting = self.gpt_answerer.job_is_interesting()

# Откликнуться только если вакансия интересна
if job_is_interesting:
    # Отправка отклика
    ...
```

---

## Алгоритм оценки вакансий

```
┌─────────────────────────────────────────────────────────────┐
│               Начало оценки вакансии                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Базовая оценка соответствия резюме и вакансии (1-100)      │
│  • Анализ требований (обязательные vs желательные)          │
│  • Сопоставление навыков                                    │
│  • Проверка опыта (±1 год допускается)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Проверка параметров поиска                        │
│  ┌─────────────────────────────────────────────┐            │
│  │ Для каждого параметра из search_config:     │            │
│  │  • Регион                                   │            │
│  │  • Зарплата                                 │            │
│  │  • График работы                            │            │
│  │  • Тип занятости                            │            │
│  │  • и т.д.                                   │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
│  Не совпадает? → Score -= 20                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Проверка уровня навыков                           │
│  Уровень навыка значительно ниже требуемого?                │
│  (например: требуется advanced, есть elementary)            │
│                                                              │
│  Да? → Score -= 20                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Проверка на overqualification                       │
│  Вакансия требует ≤1 года опыта,                            │
│  а у кандидата ≥4 года?                                     │
│                                                              │
│  Да? → Score -= 10                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Проверка совпадения интересов                       │
│  Вакансия совпадает с интересами кандидата?                 │
│  (из раздела "about_me" резюме)                             │
│                                                              │
│  Да? → Score += 10                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Итоговая оценка Score                          │
│                                                              │
│  Score >= 70  ?                                             │
│      │                                                       │
│  ┌───┴────┐                                                 │
│  ▼        ▼                                                 │
│ Да       Нет                                                │
│  │        │                                                 │
│  │        └──> ❌ Пропустить вакансию                      │
│  │             (сохранить в skipped.yaml с причиной)        │
│  │                                                          │
│  └──────────> ✅ Вакансия интересна                        │
│               • Генерация сопроводительного письма          │
│               • Ответ на вопросы работодателя               │
│               • Отправка отклика                            │
└─────────────────────────────────────────────────────────────┘
```

### Пример расчета Score

**Исходные данные:**
- Резюме: Python разработчик, 5 лет опыта
- Вакансия: Senior Python Developer, требуется 3-6 лет
- Параметры поиска: Москва, удаленка, зарплата от 300k RUR

**Расчет:**

| Этап | Действие | Score |
|------|----------|-------|
| Начальная оценка | Резюме соответствует требованиям | **85** |
| Проверка региона | ✅ Вакансия в Москве | 85 |
| Проверка графика | ✅ Удаленная работа | 85 |
| Проверка зарплаты | ❌ Зарплата 250k (ниже 300k) | 85 - 20 = **65** |
| Проверка навыков | ✅ Все навыки на нужном уровне | 65 |
| Проверка опыта | ✅ 5 лет входит в 3-6 (±1 год) | 65 |
| Проверка интересов | ✅ Упомянут интерес к ML, вакансия с ML | 65 + 10 = **75** |
| **Итоговый Score** | | **75** |

**Результат:** ✅ **Откликаемся** (75 >= 70)

---

## Параметры конфигурации

### Обязательные поля

| Параметр | Тип | Описание |
|----------|-----|----------|
| `job_title` | string | Должность (должна совпадать с названием резюме на hh.ru) |
| `user_id` | string | ID пользователя на hh.ru |
| `max_applies_num` | integer | Максимум откликов за один запуск (по умолчанию: 200) |

### Поисковые параметры

#### Базовые

| Параметр | Тип | Разделитель | Пример |
|----------|-----|-------------|--------|
| `keywords` | string | `,` | `"Аналитик, программист"` |
| `words_to_exclude` | string | `,` | `"Google, Meta"` |
| `professional_role` | string | - | `"Программист"` |
| `industry` | string | `,` | `"Банки, Финансовые услуги"` |
| `area` | string | `;` | `"Москва;Санкт-Петербург"` |
| `metro` | string | `,` | `"Павелецкая, Комсомольская"` |
| `districts` | string | `,` | `"Чертаново, Бутово"` ⚠️ *не используется API* |

#### Область поиска

```yaml
search_field:
  name: false          # В названии вакансии
  company_name: true   # В названии компании
  description: true    # В описании вакансии
```

#### Финансовые

```yaml
salary: 300000         # Уровень дохода (целое число)
only_with_salary: false  # Только вакансии с указанной зарплатой

currency:              # Только ОДНО значение true
  RUR: true
  EUR: false
  USD: false
```

#### Требования к кандидату

```yaml
education:             # ⚠️ Не используется API
  not_needed: true
  middle: false
  higher: false

experience:            # Только ОДНО значение true
  doesntMatter: false
  noExperience: false
  between1And3: false
  between3And6: false
  moreThan6: true
```

#### Условия работы

```yaml
employment:            # Несколько значений true
  full: true           # Полная занятость
  part: true           # Частичная занятость
  project: false       # Проектная работа
  volunteer: false     # Волонтерство
  probation: false     # Стажировка

schedule:              # Несколько значений true
  fullDay: true        # Полный день
  shift: false         # Сменный график
  flexible: false      # Гибкий график
  remote: true         # Удаленная работа
  flyInFlyOut: false   # Вахтовый метод

part_time:             # Для подработки
  project: true
  part: true
  from_four_to_six_hours_in_a_day: false
  only_saturday_and_sunday: false
  start_after_sixteen: false
```

#### Дополнительные фильтры

```yaml
vacancy_label:
  with_address: true                # С адресом
  accept_handicapped: false         # Для людей с инвалидностью
  not_from_agency: false            # Без кадровых агентств
  accept_kids: false                # Доступные с 14 лет
  accredited_it: true               # От аккредитованных ИТ-компаний
  low_performance: false            # Меньше 10 откликов
```

#### Сортировка и период

```yaml
order_by:              # Только ОДНО значение true
  relevance: true      # По соответствию
  publication_time: false  # По дате
  salary_desc: false   # По убыванию зарплаты
  salary_asc: false    # По возрастанию зарплаты

period:                # Только ОДНО значение true
  all_time: false      # За всё время
  month: true          # За месяц
  week: false          # За неделю
  three_days: false    # За 3 дня
  one_day: false       # За сутки
```

### Управление откликами

```yaml
job_blacklist: "Google, Meta"  # Исключить компании
apply_once_at_company: true    # Не более 1 отклика на компанию
skip_companies_with_test: false  # Пропускать с тестовыми заданиями
max_total_applies_num: 1500    # Общий лимит откликов (опционально)

# Готовое сопроводительное письмо (если заполнено - LLM не используется)
cover_letter: |
  Здравствуйте! Прошу рассмотреть моё резюме...
```

---

## Примеры использования

### Пример 1: Junior Python разработчик

```yaml
job_title: Junior Python Developer
keywords: Python, Django, Flask
professional_role: Программист
area: Москва;Санкт-Петербург;Новосибирск
salary: 80000
currency:
  RUR: true
  EUR: false
  USD: false

experience:
  noExperience: true
  between1And3: true
  doesntMatter: false
  between3And6: false
  moreThan6: false

employment:
  full: true
  part: false
  project: false
  volunteer: false
  probation: true

schedule:
  fullDay: true
  remote: true
  shift: false
  flexible: false
  flyInFlyOut: false

vacancy_label:
  with_address: false
  accept_handicapped: false
  not_from_agency: true
  accept_kids: false
  accredited_it: false
  low_performance: false

apply_once_at_company: true
skip_companies_with_test: false
max_applies_num: 100
```

### Пример 2: Senior Backend разработчик (удаленка)

```yaml
job_title: Senior Python Backend Developer
keywords: Python, FastAPI, PostgreSQL, Redis, Kafka
professional_role: Программист
industry: Информационные технологии, IT-консалтинг
area: ""  # Любой регион (удаленка)
salary: 400000
only_with_salary: true
currency:
  RUR: true
  EUR: false
  USD: false

experience:
  doesntMatter: false
  noExperience: false
  between1And3: false
  between3And6: false
  moreThan6: true

employment:
  full: true
  part: false
  project: true  # Рассматриваем проектную работу
  volunteer: false
  probation: false

schedule:
  fullDay: false
  remote: true  # ТОЛЬКО удаленка
  shift: false
  flexible: true
  flyInFlyOut: false

vacancy_label:
  with_address: false
  accept_handicapped: false
  not_from_agency: true  # Без агентств
  accept_kids: false
  accredited_it: true  # Только аккредитованные IT
  low_performance: true  # Вакансии с малым числом откликов

job_blacklist: Яндекс, Сбер, ВТБ  # Личные предпочтения
apply_once_at_company: true
skip_companies_with_test: true  # Пропускать тестовые
max_applies_num: 50  # Селективный подход
```

### Пример 3: Data Scientist с готовым письмом

```yaml
job_title: Data Scientist
keywords: Machine Learning, Python, TensorFlow, PyTorch
professional_role: Аналитик
industry: Финансовые услуги, Банки, Страхование
area: Москва
metro: Маяковская, Белорусская, Динамо
salary: 350000
currency:
  RUR: true
  EUR: false
  USD: false

experience:
  doesntMatter: false
  noExperience: false
  between1And3: false
  between3And6: true
  moreThan6: false

employment:
  full: true
  part: false
  project: false
  volunteer: false
  probation: false

schedule:
  fullDay: true
  remote: true
  shift: false
  flexible: true
  flyInFlyOut: false

# Готовое сопроводительное письмо
cover_letter: |
  Здравствуйте!
  
  Меня заинтересовала вакансия Data Scientist в вашей компании.
  
  Мой опыт:
  - 4 года в анализе данных и машинном обучении
  - Работал с PyTorch, TensorFlow, scikit-learn
  - Реализовывал ML-модели для финтех-проектов
  - Опыт A/B тестирования и метрик
  
  Готов обсудить детали проектов на собеседовании.
  
  Контакты: @my_telegram, email@example.com

apply_once_at_company: true
skip_companies_with_test: false
max_applies_num: 30
```

---

## Отладка и оптимизация

### Режимы работы

**Файл:** `src/app_config.py`

```python
# Режим "обезьяны" - откликаемся на ВСЕ вакансии без LLM-фильтрации
MONKEY_MODE = False

# Режим создания резюме (экспериментальный)
RESUME_MODE = False

# Режим проверки сопроводительных писем (не откликаемся, только генерируем)
COVER_LETTER_MODE = False

# Сбор статистики по навыкам
SKILL_STAT_MODE = False

# Порог интересности вакансии (1-100)
JOB_IS_INTERESTING_THRESH = 70

# Автоподнятие резюме (не чаще 1 раза в 4 часа)
AUTO_RAISE_RESUME = True
```

### Логирование

**Уровни логирования:**

| Уровень | Что логируется |
|---------|----------------|
| `DEBUG` | Детальная отладка, все параметры |
| `INFO` | Основные этапы работы, оценки LLM |
| `WARNING` | Пропущенные вакансии, ошибки API |
| `ERROR` | Критические ошибки |

**Где смотреть логи:**
```
logs/app.log  # Основной лог приложения
```

**Полезные сообщения:**

```
INFO - Установка параметров SearchCustomizer
INFO - Параметры SearchCustomizer успешно установлены
INFO - Найдено 347 вакансий
INFO - Проверяем, насколько вакансия может быть интересна
INFO - Степень 'интересности' вакансии: 85
INFO - Работа не интересна: Salary below expectations (250k vs 300k required)
WARNING - Пропускаем вакансию по причине: Already applied to this company
```

### Выходные файлы

**Папка:** `data_folder/output/`

| Файл | Содержимое |
|------|------------|
| `success.yaml` | Успешные отклики |
| `failed.yaml` | Ошибки при отправке |
| `skipped.yaml` | Пропущенные вакансии с причинами |
| `answers.yaml` | Кэш ответов LLM на вопросы |
| `llm_api_calls.yaml` | Полный лог обращений к LLM (для анализа расходов) |
| `cover_letters.txt` | Сгенерированные сопроводительные письма |
| `resume.yaml` | Информация о резюме |
| `last_run.yaml` | Данные о последнем запуске |

### Частые проблемы

#### 1. Слишком мало вакансий

**Причины:**
- 🔴 Слишком строгие параметры поиска
- 🔴 Высокий порог `JOB_IS_INTERESTING_THRESH`
- 🔴 Малое значение `period` (например, только за сутки)

**Решение:**
```yaml
# Ослабить фильтры
period:
  month: true  # Вместо one_day

# Снизить порог в app_config.py
JOB_IS_INTERESTING_THRESH = 60  # Вместо 70
```

#### 2. Слишком много нерелевантных вакансий

**Причины:**
- 🔴 `MONKEY_MODE = True` (отключен LLM-фильтр)
- 🔴 Низкий порог `JOB_IS_INTERESTING_THRESH`
- 🔴 Слишком широкие параметры поиска

**Решение:**
```python
# app_config.py
MONKEY_MODE = False
JOB_IS_INTERESTING_THRESH = 75  # Повысить порог

# search_config.yaml
keywords: "Python, Django, FastAPI"  # Более специфичные ключевые слова
```

#### 3. Вакансии не соответствуют региону

**Проблема:** Указан регион, но приходят вакансии из других городов

**Причина:** Неправильный разделитель

```yaml
# ❌ НЕПРАВИЛЬНО (запятая)
area: Москва, Санкт-Петербург

# ✅ ПРАВИЛЬНО (точка с запятой)
area: Москва;Санкт-Петербург
```

#### 4. LLM штрафует за несоответствие параметрам

**Проблема:** Score всегда низкий из-за штрафов -20

**Причина:** Параметры в `search_config.yaml` противоречат реальным вакансиям

**Решение:** Проверить логи, найти причину штрафа:
```
INFO - Работа не интересна: Vacancy location (Новосибирск) 
       doesn't match search parameters (Москва, СПб) - penalty -20
```

Либо ослабить параметры, либо расширить список регионов.

#### 5. Не находит специализацию

**Проблема:** `professional_role` не преобразуется в ID

**Причина:** Слишком специфичное или нестандартное название

**Решение:** Использовать более общие формулировки:
```yaml
# ❌ Может не найти
professional_role: Full-stack разработчик на Python и React

# ✅ Найдет
professional_role: Программист
```

**Проверка:** Посмотреть список доступных ролей через API:
```bash
curl https://api.hh.ru/professional_roles
```

---

## Полезные команды

### Тестирование конфигурации

```bash
# Проверка валидности YAML
python -c "import yaml; yaml.safe_load(open('data_folder/search_config/search_config.yaml'))"

# Режим проверки сопроводительных писем (без откликов)
# В app_config.py установить COVER_LETTER_MODE = True
python main.py

# Режим обезьяны (отклик на все вакансии для тестирования)
# В app_config.py установить MONKEY_MODE = True
python main.py
```

### Просмотр результатов

```bash
# Успешные отклики
cat data_folder/output/success.yaml

# Пропущенные вакансии с причинами
cat data_folder/output/skipped.yaml

# Сгенерированные письма
cat data_folder/output/cover_letters.txt

# Расходы на LLM
cat data_folder/output/llm_api_calls.yaml
```

### Очистка кэша

```bash
# Удалить кэш ответов (LLM будет генерировать заново)
rm data_folder/output/answers.yaml

# Полная очистка результатов
rm -rf data_folder/output/*
```

---

## Дополнительные ресурсы

- **Основная документация:** [README.md](README.md)
- **Руководство по папкам данных:** [docs/data_folders_guide.md](docs/data_folders_guide.md)
- **Архитектура приложения:** [docs/architecture.md](docs/architecture.md)
- **Промпты и их использование:** [docs/prompts/](docs/prompts/)
- **Получение токенов hh.ru:** [notebooks/get_tokens.ipynb](notebooks/get_tokens.ipynb)

---

**Версия документа:** 1.0  
**Дата создания:** 6 ноября 2025  
**Автор:** AI Assistant на основе анализа кодовой базы

