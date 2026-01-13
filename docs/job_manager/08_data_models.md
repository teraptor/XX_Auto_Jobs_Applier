# Модели данных модуля Job Manager

## Назначение

Данный документ описывает все структуры данных, используемые в модуле job_manager, их форматы и способы сериализации.

---

## Форматы данных

### YAML
Основной формат для конфигураций и кэша.

**Библиотека**: gopkg.in/yaml.v3

**Использование**:
- Конфигурационные файлы
- Кэш данных
- Логи результатов

### JSON
Формат для API взаимодействия.

**Использование**:
- Запросы к HeadHunter API
- Ответы от HeadHunter API
- Запросы к LLM API

---

## Модели конфигурации

### Secrets

**Файл**: `data_folder/secrets/secrets.yaml`

**Структура**:
```
Secrets:
    access_token: String
    refresh_token: String
    hh_login: String
    hh_password: String
    llm_api_key: String
    llm_proxy: List[String]?
    tg_token: String?
    tg_api_id: Int?
    tg_api_hash: String?
    user_id: String?
```

**Валидация**:
- `access_token` - обязательное, не пусто
- `refresh_token` - обязательное, не пусто
- `hh_login` - обязательное
- `hh_password` - обязательное
- `llm_api_key` - обязательное, не пусто

**Пример**:
```yaml
access_token: "abc123..."
refresh_token: "def456..."
hh_login: "user@example.com"
hh_password: "password"
llm_api_key: "sk-proj-..."
llm_proxy:
  - "http://user:pass@IP:port"
tg_token: "1234567:ABC..."
tg_api_id: 12345
tg_api_hash: "abc..."
user_id: "123456"
```

---

### SearchConfig

**Файл**: `data_folder/search_config/search_config.yaml`

**Структура**:
```
SearchConfig:
    # Обязательные поля
    job_title: String
    user_id: String
    max_applies_num: Int
    
    # Параметры поиска
    keywords: String?
    search_field: SearchField?
    words_to_exclude: String?
    professional_role: String?
    industry: String?
    area: String?
    districts: String?
    metro: String?
    salary: Int?
    only_with_salary: Bool
    currency: Currency
    education: Education?
    experience: Experience
    employment: Employment
    schedule: Schedule
    part_time: PartTime?
    vacancy_label: VacancyLabel?
    order_by: OrderBy
    period: Period
    
    # Управление откликами
    job_blacklist: String?
    cover_letter: String?
    apply_once_at_company: Bool
    skip_companies_with_test: Bool
    max_total_applies_num: Int?

SearchField:
    name: Bool
    company_name: Bool
    description: Bool

Currency:
    RUR: Bool
    EUR: Bool
    USD: Bool

Education:
    not_needed: Bool
    middle: Bool
    higher: Bool

Experience:
    doesntMatter: Bool
    noExperience: Bool
    between1And3: Bool
    between3And6: Bool
    moreThan6: Bool

Employment:
    full: Bool
    part: Bool
    project: Bool
    volunteer: Bool
    probation: Bool

Schedule:
    fullDay: Bool
    shift: Bool
    flexible: Bool
    remote: Bool
    flyInFlyOut: Bool

PartTime:
    project: Bool
    part: Bool
    from_four_to_six_hours_in_a_day: Bool
    only_saturday_and_sunday: Bool
    start_after_sixteen: Bool

VacancyLabel:
    with_address: Bool
    accept_handicapped: Bool
    not_from_agency: Bool
    accept_kids: Bool
    accredited_it: Bool
    low_performance: Bool

OrderBy:
    relevance: Bool
    publication_time: Bool
    salary_desc: Bool
    salary_asc: Bool

Period:
    all_time: Bool
    month: Bool
    week: Bool
    three_days: Bool
    one_day: Bool
```

**Валидация**:
- `job_title` - обязательное, не пусто
- `user_id` - обязательное
- `max_applies_num` - обязательное, > 0
- В Currency, Experience, OrderBy, Period - ТОЛЬКО ОДНО значение true
- В остальных Bool полях - может быть несколько true

---

## Модели данных вакансий

### Vacancy (краткая информация)

**Источник**: GET /vacancies, GET /resumes/{id}/similar_vacancies

**Структура**:
```
Vacancy:
    id: String
    name: String
    alternate_url: String
    
    area:
        id: String
        name: String
    
    employer:
        id: String
        name: String
        accredited_it_employer: Bool?
    
    salary:
        from: Int?
        to: Int?
        currency: String
        gross: Bool
    
    address:
        city: String?
        street: String?
        building: String?
        lat: Float64?
        lng: Float64?
    
    snippet:
        requirement: String?
        responsibility: String?
    
    has_test: Bool
    
    professional_roles: List[Role]
    
    experience:
        id: String
        name: String
    
    work_format: List[WorkFormat]?
    work_schedule_by_days: List[WorkSchedule]?
    employment_form: EmploymentForm?
```

---

### VacancyDetails (детальная информация)

**Источник**: GET /vacancies/{id}

**Структура**:
```
VacancyDetails:
    # Включает все поля из Vacancy +
    
    description: String  # HTML текст
    
    key_skills: List[Skill]?
    
    accept_handicapped: Bool
    
    driver_license_types: List[DriverLicense]?
    
    contacts:
        name: String?
        email: String?
        phones: List[Phone]?
    
    department:
        id: String
        name: String
    
    night_shifts: Bool?
    internship: Bool?
    accept_temporary: Bool?

Skill:
    name: String

DriverLicense:
    id: String

Phone:
    country: String
    city: String
    number: String
    comment: String?
```

---

### Job (обработанная вакансия)

**Назначение**: Внутренняя структура для передачи в LLM

**Структура**:
```
Job:
    # Идентификаторы
    vacancy_id: String
    company_id: String
    
    # Основная информация
    job_title: String
    company_name: String
    company_department: String?
    
    # Описание
    job_description: String  # Очищенное от HTML
    requirement: String?
    responsibility: String?
    
    # Условия
    salary: Salary?
    area: String
    address: Address?
    work_format: List[String]?
    work_schedule_by_days: List[String]?
    employment_form: String?
    required_experience: String?
    
    # Требования
    professional_roles: List[String]
    key_skills: List[String] // из VacancyDetails
    required_driver_licenses: List[String]?
    
    # Дополнительно
    has_test_task: Bool
    accredited_it_employer: Bool?
    accept_handicapped_employers: Bool
    night_shifts: Bool?
    is_internship: Bool?
    accept_temporary_employment: Bool?
    
    # Контакты
    contacts: Contacts?
```

---

## Модели данных резюме

### ResumeInfo

**Источник**: Собирается ResumeScraper из API

**Структура**:
```
ResumeInfo:
    personal_information: PersonalInfo
    work_preferences: WorkPreferences
    availability: Availability
    languages: Map[String]String
    education_details: EducationDetails
    experience_details: ExperienceDetails
    certifications: List[Certification]?
    recommendation: List[Recommendation]?
    salary_expectations: Salary?
    skills: List[String]?
    about_me: String?

PersonalInfo:
    # Базовые данные
    first_name: String
    last_name: String
    middle_name: String?
    age: Int?
    sex: String
    
    # Место проживания
    current_city: String
    metro: String?
    
    # Гражданство и разрешения
    citizenship: List[String]
    legal_authorization: List[String]
    
    # Транспорт
    has_vehicle: Bool
    driver_license_types: List[String]?
    
    # Контакты (анонимизированные для LLM)
    phone: String
    email: String
    telegram: String?
    whatsapp: String?
    linkedin: String?
    github: String?
    skype: String?
    other_site: String?
    preferred_contact: String?

WorkPreferences:
    position: String
    can_relocate: String
    professional_roles: List[String]?
    employments: List[String]?
    schedules: List[String]?
    travel_time_to_work: String
    ready_to_business_trips: String

Availability:
    notice_period: String

EducationDetails:
    level: String?
    primary: List[PrimaryEducation]?
    elementary: List[ElementaryEducation]?
    additional: List[AdditionalEducation]?
    attestation: List[Attestation]?

PrimaryEducation:
    name: String
    organization: String
    result: String?
    year: Int

ExperienceDetails:
    total_experience_years: Int?
    details: List[ExperienceItem]?

ExperienceItem:
    start_date: String
    end_date: String?
    company: String
    area: String?
    position: String
    description: String?
    industries: List[String]?
```

---

## Модели кэша и результатов

### Cache

**Файл**: `data_folder/output/last_run.yaml`

**Структура**:
```
Cache:
    last_run: DateTime?  # ISO 8601
    last_apply: DateTime?  # ISO 8601
    success_applies_num: Int
    total_applies_num: Int
```

**Пример**:
```yaml
last_run: "2025-10-22T14:30:00"
last_apply: "2025-10-22T15:45:23"
success_applies_num: 15
total_applies_num: 127
```

---

### CompanyApplications

**Файлы**: 
- `success.yaml`
- `skipped.yaml`
- `failed.yaml`

**Структура**:
```
Map[String]Map[String]List[ApplicationInfo]

где:
    первый ключ - resume_id
    второй ключ - company_id ИЛИ company_name
    значение - список откликов на вакансии этой компании

ApplicationInfo:
    vacancy_id: String
    job_title: String
    link: String
    reason: String  # пусто для success
```

**Пример**:
```yaml
resume_abc123:
  company_456:
    - vacancy_id: "vac_789"
      job_title: "Python Developer"
      link: "https://hh.ru/vacancy/vac_789"
      reason: ""
    - vacancy_id: "vac_790"
      job_title: "Senior Python Developer"
      link: "https://hh.ru/vacancy/vac_790"
      reason: ""
  
  "ООО Рога и Копыта":
    - vacancy_id: "vac_791"
      job_title: "Backend Developer"
      link: "https://hh.ru/vacancy/vac_791"
      reason: "Вакансия уже встречалась"
```

---

### AnswersCache

**Файл**: `answers.yaml`

**Структура**:
```
List[AnswerCacheItem]

AnswerCacheItem:
    question: String
    answer: String
```

**Пример**:
```yaml
- question: "Опишите ваш опыт работы с Python"
  answer: "У меня 5 лет опыта разработки на Python..."

- question: "Какие фреймворки вы знаете?"
  answer: "Django, Flask, FastAPI, SQLAlchemy"
```

---

### SkillStatistics

**Файл**: `skill_stat.yaml`

**Структура**:
```
Map[String]Int

где:
    ключ - название навыка
    значение - количество вакансий, требующих этот навык
```

**Пример**:
```yaml
Python: 45
Django: 23
PostgreSQL: 31
Docker: 28
Redis: 15
REST API: 38
```

---

### LLMAPICallLog

**Файл**: `llm_api_calls.yaml`

**Структура**:
```
List[LLMCallLogItem]

LLMCallLogItem:
    timestamp: DateTime
    prompt: String
    response: String
    input_tokens: Int
    output_tokens: Int
    cost_usd: Float64
    model: String
```

**Пример**:
```yaml
- timestamp: "2025-10-22T14:30:15"
  prompt: "Оцени вакансию..."
  response: "85"
  input_tokens: 1523
  output_tokens: 3
  cost_usd: 0.0001523
  model: "gemini-2.0-flash"
```

---

## Модели для Selenium

### WebElement (внешняя структура)

**Источник**: Selenium WebDriver

**Основные методы**:
- `find_element(by, selector)` → WebElement
- `find_elements(by, selector)` → List[WebElement]
- `click()` → void
- `send_keys(text)` → void
- `get_attribute(name)` → String
- `text` → String (property)
- `location` → Location (property)

**Селекторы**:
- `"xpath"` - XPath выражение
- `"css selector"` - CSS селектор
- `"class name"` - имя класса
- `"id"` - ID элемента

---

## Константы и перечисления

### Результаты операций

```
ApplyResult:
    Success  # Успешный отклик
    Skip     # Пропущено (причина в message)
    Error    # Ошибка (описание в message)
    Limit    # Достигнут лимит
```

### Режимы работы

```
Mode:
    Normal           # Обычный режим
    Monkey           # MONKEY_MODE - откликаться на все
    CoverLetter      # COVER_LETTER_MODE - только письма
    Resume           # RESUME_MODE - только резюме
    SkillStat        # SKILL_STAT_MODE - статистика навыков
```

### Типы вопросов

```
QuestionType:
    Radio      # Выбор одного варианта
    Checkbox   # Выбор нескольких вариантов
    Text       # Текстовый ответ
```

---

## Анонимизация данных

### Dummy данные

**Мужской вариант** (DUMMY_PERSONAL_INFO_MALE):
```
first_name: "Аристаний"
middle_name: "Астромерович"
last_name: "Звягольцев"
phone: "+7 (933) 575-35-35"
email: "aristaniy93@gmail.com"
telegram: "https://t.me/aristaniy93"
whatsapp: "https://wa.me/aristaniy93"
other_site: "https://www.aristaniy93.ru"
linkedin: "https://linkedin.com/in/aristaniy-zvyagoltsev-f3e57c712"
github: "https://github.com/aristaniy93"
skype: "aristaniy93"
habr_career: "https://career.habr.ru/aristaniy93"
moi_krug: "https://moi-krug.ru/aristaniy93"
livejournal: "https://aristaniy93.livejournal.com"
```

**Женский вариант** (DUMMY_PERSONAL_INFO_FEMALE):
```
first_name: "Аристания"
middle_name: "Астромеровна"
last_name: "Звягольцева"
// ... остальные поля аналогично
```

### Процесс анонимизации

**При отправке в LLM**:
1. Скопировать personal_information → сохранить оригинал
2. Заменить каждое поле на dummy значение
3. Заменить упоминания в текстах (regex)
4. Отправить анонимизированные данные

**При получении ответа от LLM**:
1. Найти все dummy значения в ответе
2. Заменить на оригинальные значения
3. Вернуть деанонимизированный ответ

---

## Сериализация/Десериализация

### YAML

**Сериализация**:
```
func SaveYAML(filepath string, data any) error:
    bytes = yaml.Marshal(data)
    WriteFile(filepath, bytes)
```

**Десериализация**:
```
func LoadYAML(filepath string, target any) error:
    bytes = ReadFile(filepath)
    yaml.Unmarshal(bytes, target)
```

### JSON

**Для API запросов**:
```
func MarshalJSON(data any) ([]byte, error):
    return json.Marshal(data)

func UnmarshalJSON(bytes []byte, target any) error:
    return json.Unmarshal(bytes, target)
```

---

## Валидация данных

### Pydantic-подобная валидация

**Для Go**: использовать теги struct + validator библиотека

**Пример**:
```
type SearchConfig struct {
    JobTitle        string `yaml:"job_title" validate:"required"`
    UserID          string `yaml:"user_id" validate:"required"`
    MaxAppliesNum   int    `yaml:"max_applies_num" validate:"required,gt=0"`
    Keywords        string `yaml:"keywords,omitempty"`
    // ...
}
```

**Валидация**:
- `required` - обязательное поле
- `gt=0` - больше 0
- `oneof` - одно из списка значений
- Custom validators для сложной логики

---

## Миграция данных

### Совместимость версий

При изменении структуры данных:

1. **Добавление поля**:
   - Сделать поле опциональным
   - Использовать `omitempty` в тегах YAML

2. **Удаление поля**:
   - Оставить поле но не использовать
   - Добавить deprecated комментарий

3. **Изменение типа**:
   - Создать новое поле с новым типом
   - Мигрировать данные при загрузке

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Назначение**: Спецификация моделей данных для реализации на Go

