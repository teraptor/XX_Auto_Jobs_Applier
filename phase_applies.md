# Фаза откликов на вакансии (Phase Applies)

## 📋 Оглавление

1. [Введение](#введение)
2. [Архитектура фазы откликов](#архитектура-фазы-откликов)
3. [Предварительная проверка вакансии](#предварительная-проверка-вакансии)
4. [Генерация сопроводительного письма](#генерация-сопроводительного-письма)
5. [Деанонимизация персональных данных](#деанонимизация-персональных-данных)
6. [Ответы на вопросы работодателя](#ответы-на-вопросы-работодателя)
7. [Отправка отклика через API](#отправка-отклика-через-api)
8. [Обработка результатов](#обработка-результатов)
9. [Сохранение статистики](#сохранение-статистики)
10. [Режимы работы](#режимы-работы)
11. [Обработка ошибок](#обработка-ошибок)
12. [Примеры работы](#примеры-работы)
13. [Отладка и мониторинг](#отладка-и-мониторинг)

---

## Введение

**Фаза откликов** (Apply Phase) — это финальный этап обработки вакансии, который запускается после успешного прохождения **фазы поиска и фильтрации** (см. [phase-search.md](phase-search.md)).

### Условия входа в фазу откликов

Вакансия попадает в фазу откликов, если:
- ✅ Найдена через API HeadHunter
- ✅ Прошла базовые фильтры (регион, зарплата, график и т.д.)
- ✅ **Score от LLM >= 70** (по умолчанию, настраивается через `JOB_IS_INTERESTING_THRESH`)
- ✅ Компания не в черном списке (`job_blacklist`)
- ✅ Не превышен лимит откликов на компанию (`apply_once_at_company`)

### Основные компоненты

| Компонент | Файл | Назначение |
|-----------|------|------------|
| `JobApplier` | `src/job_manager/job_applier.py` | Координация процесса отклика |
| `GPTAnswerer` | `src/llm/llm_manager.py` | Генерация писем и ответов через LLM |
| `ResumeScraper` | `src/job_manager/resume_scraper.py` | Работа с резюме, деанонимизация |
| `HeadHunterAPI` | `src/job_manager/api.py` | Взаимодействие с API hh.ru |

---

## Архитектура фазы откликов

```
┌────────────────────────────────────────────────────────────────┐
│  Вход: Вакансия прошла фильтрацию (Score >= 70)                │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  1. Предварительная проверка                                   │
│     • Проверка дубликатов (уже откликались?)                   │
│     • Проверка черного списка компаний                         │
│     • Проверка лимита откликов на компанию                     │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  2. Генерация сопроводительного письма                         │
│     ┌──────────────────────────────────────┐                   │
│     │ Готовое письмо в конфиге?           │                   │
│     └────┬─────────────────────────────┬───┘                   │
│          │ Да                          │ Нет                   │
│          ▼                             ▼                       │
│   Использовать                  LLM генерирует                 │
│   fixed_cover_letter            персональное письмо            │
│          │                             │                       │
│          └──────────────┬──────────────┘                       │
│                         ▼                                       │
│              Сопроводительное письмо                           │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  3. Деанонимизация персональных данных                         │
│     • Замена placeholder имени на реальное                     │
│     • Замена placeholder телефона на реальный                  │
│     • Замена placeholder email на реальный                     │
│     • Замена placeholder Telegram на реальный                  │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  4. Проверка на вопросы работодателя                           │
│     ┌──────────────────────────────────────┐                   │
│     │ Есть вопросы от работодателя?       │                   │
│     └────┬─────────────────────────────┬───┘                   │
│          │ Да                          │ Нет                   │
│          ▼                             ▼                       │
│   Генерация ответов              Пропускаем                    │
│   через LLM (с кэшем)                  │                       │
│          │                             │                       │
│          └──────────────┬──────────────┘                       │
│                         ▼                                       │
│              Готовый пакет для отклика                         │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  5. Отправка отклика через API                                 │
│     POST https://api.hh.ru/negotiations                        │
│     {                                                           │
│       "vacancy_id": "...",                                     │
│       "resume_id": "...",                                      │
│       "message": "сопроводительное письмо"                     │
│     }                                                           │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  6. Обработка ответа API                                       │
│     ┌──────────────────────────────────────┐                   │
│     │ Код ответа?                          │                   │
│     └────┬──────────┬──────────┬───────────┘                   │
│          │          │          │                               │
│      201 │     errors│   test_required                         │
│          ▼          ▼          ▼                               │
│      SUCCESS    Обработка   Selenium                           │
│                  ошибки     (автозаполнение)                   │
│          │          │          │                               │
│          └──────────┴──────────┘                               │
│                     │                                           │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  7. Сохранение результатов                                     │
│     • success.yaml  - успешные отклики                         │
│     • failed.yaml   - ошибки при отклике                       │
│     • skipped.yaml  - пропущенные вакансии                     │
│     • cover_letters.txt - все письма                           │
│     • llm_api_calls.yaml - логи LLM вызовов                    │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  8. Обновление счетчиков и проверка лимитов                    │
│     • success_applies_num++                                    │
│     • total_applies_num++                                      │
│     • Проверка: достигнут лимит? → STOP или продолжить         │
└────────────────────────────────────────────────────────────────┘
```

---

## Предварительная проверка вакансии

**Файл:** `src/job_manager/job_applier.py` → `send_repsonse()`

### Этап 1: Проверка дубликатов

```python
def _is_already_applied_to_company(self, company_name: str) -> bool:
    """Проверяем, откликались ли мы уже на вакансию этой компании"""
    return company_name in self.companies_applied
```

**Логика:**
- При включенной опции `apply_once_at_company: true` в конфиге
- Проверяется список `self.companies_applied`
- Если компания уже есть → вакансия пропускается

**Результат:**
```yaml
# skipped.yaml
- company: "ООО Рога и Копыта"
  vacancy: "Python Developer"
  reason: "Already applied to this company"
```

### Этап 2: Проверка черного списка

```python
job_blacklist = parameters.get("job_blacklist", [])
if company_name in job_blacklist:
    logger.warning(f"Компания {company_name} в черном списке")
    return "Skip", "Company in blacklist"
```

**Конфигурация:**
```yaml
# search_config.yaml
job_blacklist: Google, Meta, Яндекс
```

### Этап 3: Проверка внешних ссылок

```python
if "<!doctype html>" in response.get("response_text", ""):
    return "Skip", "Не смогли откликнуться. При отклике предлагают переход на сторонний сайт"
```

**Причина:** Некоторые компании используют внешние формы для откликов, которые не поддерживаются API.

---

## Генерация сопроводительного письма

**Файл:** `src/llm/llm_manager.py` → `write_cover_letter()`

### Два режима генерации

#### Режим 1: Готовое письмо (fixed_cover_letter)

```yaml
# search_config.yaml
cover_letter: |
  Здравствуйте!
  
  Меня заинтересовала вакансия в вашей компании.
  
  Мой опыт:
  - 5 лет разработки на Python
  - Работа с Django, FastAPI, PostgreSQL
  - Опыт в финтех и банковском секторе
  
  Готов обсудить детали на собеседовании.
  
  С уважением,
  Иван Сидоров
  Telegram: @ivan_example
```

**Использование:**
```python
if self.fixed_cover_letter:
    logger.info("Берем готовое сопроводительное письмо")
    cover_letter_text = self.fixed_cover_letter
```

**Преимущества:**
- 🚀 Мгновенная скорость (без вызова LLM)
- 💰 Нулевая стоимость (нет API вызовов)
- 🎯 Полный контроль над содержанием

**Недостатки:**
- ❌ Не персонализировано под вакансию
- ❌ Не отвечает на вопросы из описания

#### Режим 2: Генерация через LLM

**Промпт:** `src/llm/prompts.py` → `coverletter_template`

```python
coverletter_template = """
Составь краткое и выразительное сопроводительное письмо на основе 
предоставленного описания вакансии и резюме.

Письмо должно быть не длиннее пяти абзацев.

##Описание работы##
```
{job_description}
```

##Резюме##
```
{resume}
```

##Дополнительные правила##
- НЕ УКАЗЫВАЙ напрямую название компании
- Текст ДОЛЖЕН быть написан на том же языке, что и описание работы
- УЧИТЫВАЙ что пол автора письма - {sex}
- Если в описании есть вопросы - ответь на них
- Не указывай ссылки (Github, LinkedIn)
- НЕ ИСПОЛЬЗУЙ фразы "что соответствует требованиям"
"""
```

### Процесс генерации

**Шаг 1: Подготовка контекста**

```python
sex = self.resume["personal_information"].get("sex")  # "мужской" или "женский"
telegram = self.resume["personal_information"].get("telegram", "")
phone = self.resume["personal_information"].get("phone", "")
email = self.resume["personal_information"].get("email", "")
```

**Шаг 2: Формирование дополнительного промпта**

```python
additional_prompt = "- В качестве контакта укажи "

if telegram:
    additional_prompt += f"Telegram: {telegram}"
elif phone:
    additional_prompt += f"Телефон: {phone}"
else:
    additional_prompt += f"Email: {email}"
```

**Шаг 3: Вызов LLM**

```python
chain = self._create_chain(prompts.coverletter_template + additional_prompt)
output = chain.invoke({
    "resume": self.resume_readable,
    "job_description": self.job_readable,
    "sex": sex,
})
```

**Шаг 4: Сохранение результата**

```python
logger.info(f"Сопроводительное письмо сгенерировано: '{output}'")
return output
```

### Примеры сгенерированных писем

#### Пример 1: Junior разработчик

**Вход:**
- Вакансия: Junior Python Developer
- Опыт: 1 год, выпускник ВУЗа
- Навыки: Python, Django, PostgreSQL

**Выход:**
```
Добрый день!

Меня заинтересовала вакансия Junior Python Developer в вашей компании. 
Я начинающий разработчик с годом коммерческого опыта и большим желанием 
развиваться в направлении backend-разработки.

В моем опыте есть разработка web-приложений на Django, работа с PostgreSQL 
и REST API. Участвовал в создании CRM-системы для малого бизнеса, где 
отвечал за backend-часть и интеграции с внешними сервисами.

Быстро обучаюсь новым технологиям, готов погружаться в код и документацию. 
Интересуют задачи, где можно применить знания Python и узнать best practices 
от опытных коллег.

Буду рад обсудить детали на собеседовании.

С уважением,
Алексей
Telegram: @alexdev
```

#### Пример 2: Senior с акцентом на опыт

**Вход:**
- Вакансия: Senior Backend Developer (FastAPI, PostgreSQL, Redis)
- Опыт: 7 лет, из них 5 лет в финтехе
- Навыки: Python, FastAPI, PostgreSQL, Redis, Kafka, Docker

**Выход:**
```
Здравствуйте!

Хочу откликнуться на вакансию Senior Backend Developer в вашей команде. 
У меня 7 лет опыта разработки на Python, из них 5 лет в финтехе, что дает 
хорошее понимание специфики работы с критичными системами и высокими 
требованиями к надежности.

В последних проектах активно использовал FastAPI для построения 
микросервисной архитектуры, PostgreSQL для хранения данных, Redis для 
кэширования и Kafka для асинхронной обработки событий. Проектировал 
высоконагруженные API с пропускной способностью до 10000 RPS.

Опыт включает построение CI/CD пайплайнов, настройку мониторинга через 
Prometheus/Grafana, оптимизацию SQL-запросов и работу с Docker/Kubernetes. 
Практикую code review, документирование архитектуры и менторинг junior-разработчиков.

Интересны задачи, связанные с проектированием масштабируемых систем и 
оптимизацией производительности. Готов подробнее обсудить опыт и подходы к решению задач.

С уважением,
Дмитрий Иванов
Telegram: @dmitry_backend
```

#### Пример 3: Ответ на вопросы из вакансии

**Вход - описание вакансии содержит:**
```
...
Ответьте, пожалуйста, в сопроводительном письме:
1. Какой ваш опыт работы с React?
2. Готовы ли вы работать в офисе 3 дня в неделю?
```

**Резюме:**
- Опыт: React - 3 года
- Предпочтительный график: Гибридный

**Выход:**
```
Добрый день!

Меня заинтересовала вакансия Frontend Developer в вашей компании. 
Занимаюсь разработкой на React уже 3 года, создавал SPA для e-commerce 
и финтех-проектов.

Опыт включает работу с React Hooks, Redux/MobX, TypeScript, а также 
настройку сборки через Webpack. Умею оптимизировать производительность 
приложений, работать с REST API и WebSocket.

Отвечая на ваши вопросы:
1. С React работаю 3 года в коммерческих проектах, от небольших лендингов 
   до сложных SPA с множеством интеграций.
2. Да, готов работать в офисе 3 дня в неделю. Гибридный формат работы 
   для меня комфортен.

Буду рад обсудить детали и продемонстрировать примеры работ.

С уважением,
Мария Петрова
Telegram: @maria_frontend
```

### Стоимость генерации письма

**Модель:** `gpt-4o-mini` (по умолчанию)

**Средний запрос:**
- Input: ~3500 токенов (резюме + описание вакансии + промпт)
- Output: ~400 токенов (письмо)

**Тарифы OpenAI (gpt-4o-mini):**
- Input: $0.000150 за 1K токенов
- Output: $0.000600 за 1K токенов

**Расчет стоимости:**
```
Input:  3.5K × $0.000150 = $0.000525
Output: 0.4K × $0.000600 = $0.000240
Итого:  $0.000765 (~0.08₽ по курсу 100₽/$)
```

**За 100 откликов:**
- Стоимость: ~$0.77 (~77₽)
- Время: ~60 секунд (при скорости ~40 токенов/сек)

---

## Деанонимизация персональных данных

**Файл:** `src/job_manager/resume_scraper.py` → `deanonymize_personal_information()`

### Зачем нужна анонимизация?

**Проблема:** LLM провайдеры (OpenAI, Claude и др.) могут сохранять историю запросов для обучения моделей.

**Решение:** 
1. В резюме, которое видит LLM, используются **placeholder данные**
2. После генерации письма происходит **деанонимизация** (замена на реальные)

### Процесс деанонимизации

**Файл:** `src/job_manager/job_applier.py`

```python
cover_letter_text = self.gpt_answerer.write_cover_letter()

# Деанонимизация
cover_letter_text = self.resume_component.deanonymize_personal_information(
    cover_letter_text
)
```

### Что заменяется?

```python
def deanonymize_personal_information(self, text: str) -> str:
    """Заменить анонимизированные данные на реальные"""
    
    # Загрузить реальные данные из резюме
    real_info = self._get_real_personal_information()
    dummy_info = self._get_dummy_personal_information()
    
    # Замены
    replacements = {
        dummy_info["full_name"]: real_info["full_name"],
        dummy_info["phone"]: real_info["phone"],
        dummy_info["email"]: real_info["email"],
        dummy_info["telegram"]: real_info["telegram"],
    }
    
    for dummy, real in replacements.items():
        if dummy and real:
            text = text.replace(dummy, real)
    
    return text
```

### Пример

**До деанонимизации (что видел LLM):**
```
Здравствуйте!

...

С уважением,
Алексей Петров
Telegram: @alex_example
Телефон: +7 (999) 000-00-00
Email: alex.petrov@example.com
```

**После деанонимизации (что отправляется):**
```
Здравствуйте!

...

С уважением,
Иван Сидоров
Telegram: @ivan_real_contact
Телефон: +7 (916) 123-45-67
Email: ivan.sidorov@gmail.com
```

### Конфигурация dummy данных

**Файл:** `data_folder/resume/personal_information_dummy.yaml`

```yaml
full_name: Алексей Петров
phone: +7 (999) 000-00-00
email: alex.petrov@example.com
telegram: @alex_example
whatsapp: +7 (999) 000-00-00
```

**Важно:** Dummy данные должны быть **правдоподобными**, чтобы LLM генерировал естественный текст.

---

## Ответы на вопросы работодателя

**Файл:** `src/job_manager/job_applier.py` → `find_and_handle_questions()`

### Типы вопросов

#### 1. Текстовые вопросы (через API)

Обрабатываются автоматически через API `POST /negotiations`:

```python
params = {
    "vacancy_id": "12345",
    "resume_id": "67890",
    "message": cover_letter_text,
}
```

Если API возвращает ошибку `errors: [{value: "test_required"}]`, переходим к Selenium.

#### 2. Вопросы с формой (через Selenium)

**Когда:** Работодатель требует заполнить анкету на сайте

**Процесс:**

```python
if error["value"] == "test_required" and self.hh_login and self.hh_password:
    logger.info("Для отклика требуется пройти тест")
    self.driver = self.init_driver()
    answer_result, answer_text = self.find_and_handle_questions(
        vacancy, cover_letter_text
    )
```

### Генерация ответов через LLM

**Файл:** `src/llm/llm_manager.py` → `answer_question_from_job_description()`

**Промпт:** `src/llm/prompts.py` → `answer_question_template`

```python
answer_question_template = """
You are helping a job applicant answer a question from a job application form.

##Question##
{question}

##Resume##
{resume}

##Additional Rules##
- Answer based ONLY on information from the resume
- Keep the answer concise and relevant (1-3 sentences)
- Write in the same language as the question
- If the resume doesn't contain relevant information, provide a brief professional response
- Do not invent facts not present in the resume

Provide only the answer text, without any additional commentary.
"""
```

### Кэширование ответов

**Файл:** `data_folder/output/answers.yaml`

```yaml
answers:
  - question: "Какой у вас опыт работы с Python?"
    answer: "5 лет коммерческого опыта разработки на Python, работал с Django, FastAPI, PostgreSQL"
    hash: "a3f5d8e2..."
    
  - question: "Готовы ли вы к командировкам?"
    answer: "Да, готов к командировкам по России и за рубеж"
    hash: "b7c9a1f4..."
```

**Логика:**
```python
def answer_question_from_job_description(self, question: str) -> str:
    # Проверить кэш
    cached_answer = self._check_answer_cache(question)
    if cached_answer:
        logger.info(f"Ответ найден в кэше: {cached_answer}")
        return cached_answer
    
    # Иначе запросить LLM
    chain = self._create_chain(prompts.answer_question_template)
    answer = chain.invoke({
        "question": question,
        "resume": self.resume_readable,
    })
    
    # Сохранить в кэш
    self._save_answer_to_cache(question, answer)
    return answer
```

### Автозаполнение форм через Selenium

**Файл:** `src/job_manager/job_applier.py` → `find_and_handle_questions()`

**Процесс:**

1. **Инициализация браузера**
```python
def init_driver(self):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Без GUI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)
```

2. **Авторизация на hh.ru**
```python
driver.get("https://hh.ru/account/login")
driver.find_element(By.NAME, "login").send_keys(self.hh_login)
driver.find_element(By.NAME, "password").send_keys(self.hh_password)
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
```

3. **Переход на страницу вакансии**
```python
vacancy_url = vacancy["alternate_url"]
driver.get(vacancy_url)
```

4. **Поиск и заполнение полей**
```python
questions = driver.find_elements(By.CSS_SELECTOR, ".vacancy-response-questions__question")

for question_element in questions:
    question_text = question_element.text
    
    # Получить ответ от LLM
    answer = self.gpt_answerer.answer_question_from_job_description(question_text)
    
    # Заполнить поле
    input_field = question_element.find_element(By.TAG_NAME, "textarea")
    input_field.send_keys(answer)
```

5. **Отправка формы**
```python
submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
submit_button.click()
```

6. **Закрытие браузера**
```python
if self.driver is not None:
    self.driver.close()
    self.driver = None
```

### Обработка CAPTCHA

**Проблема:** hh.ru может показывать CAPTCHA при автоматизации

**Решение (будущее):**
- Интеграция с сервисами распознавания CAPTCHA (2captcha, AntiCaptcha)
- Отправка уведомления в Telegram для ручного решения

**Текущее поведение:**
```python
if "captcha" in driver.page_source.lower():
    logger.error("Обнаружена CAPTCHA. Пропускаем вакансию")
    return False, "CAPTCHA required"
```

---

## Отправка отклика через API

**Файл:** `src/job_manager/job_applier.py` → `apply_job()`

### Формирование запроса

```python
params = {
    "message": cover_letter_text,      # Сопроводительное письмо
    "resume_id": self.resume_id,       # ID резюме на hh.ru
    "vacancy_id": vacancy["id"],       # ID вакансии
}

response = self.api.api_request(
    type_="post",
    url="https://api.hh.ru/negotiations",
    params=params,
)
```

### Эндпоинт API

**URL:** `POST https://api.hh.ru/negotiations`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/x-www-form-urlencoded
```

**Body:**
```
vacancy_id=95157421
&resume_id=a1b2c3d4e5f6
&message=Здравствуйте!%0A%0AМеня%20заинтересовала...
```

### Возможные ответы API

#### Успех (201 Created)

```json
{
  "id": "12345678",
  "created_at": "2025-11-07T12:34:56+0300",
  "state": {
    "id": "response",
    "name": "Отклик"
  },
  "vacancy": {
    "id": "95157421",
    "name": "Python Developer"
  }
}
```

**Обработка:**
```python
if response.status_code == 201:
    logger.info(f"✅ Успешно откликнулись на вакансию компании {company_name}")
    return "Success", ""
```

#### Ошибки (400 Bad Request)

```json
{
  "errors": [
    {
      "type": "negotiations",
      "value": "already_applied"
    }
  ]
}
```

**Типы ошибок:**

| Код ошибки | Значение | Действие |
|------------|----------|----------|
| `already_applied` | Уже откликались на эту вакансию | Пропустить |
| `limit_exceeded` | Превышен лимит откликов | Остановка |
| `test_required` | Требуется заполнить анкету | Selenium |
| `resume_not_found` | Резюме не найдено | Ошибка |
| `vacancy_archived` | Вакансия архивирована | Пропустить |
| `resume_not_published` | Резюме не опубликовано | Ошибка |

**Обработка:**
```python
if "errors" in response:
    errors = response["errors"]
    for error in errors:
        # Лимит откликов
        if error["value"] == "limit_exceeded":
            logger.warning("⚠️ Достигли лимита откликов")
            return "Limit", ""
        
        # Требуется тест
        if error["value"] == "test_required" and self.hh_login and self.hh_password:
            logger.info("📝 Для отклика требуется пройти тест")
            # Запуск Selenium
            answer_result, answer_text = self.find_and_handle_questions(...)
            if answer_result:
                return "Success", ""
            return "Skip", answer_text
    
    # Другие ошибки
    error_message = ";".join([error["value"] for error in errors])
    logger.warning(f"❌ Ошибка при отклике: {error_message}")
    return "Skip", error_message
```

### Rate Limiting

HeadHunter API имеет ограничения:
- **20 запросов в минуту** на пользователя
- **200 откликов в день** (стандартный лимит)

**Обработка:**
```python
from src.utils.time import pause, sleep

# Случайная пауза между откликами (15-20 секунд)
pause()

# Если обработка страницы была быстрой - подождать
time_left = int(minimum_job_time - time.time())
if time_left > 0:
    sleep((time_left, time_left + 5))
```

**Функция `pause()`:**
```python
def pause() -> None:
    """Случайная пауза 15-20 секунд для имитации человеческого поведения"""
    time_to_sleep = random.randint(15, 20)
    logger.debug(f"Пауза {time_to_sleep} секунд")
    time.sleep(time_to_sleep)
```

---

## Обработка результатов

**Файл:** `src/job_manager/job_applier.py` → `_save_company()`

### Сохранение успешных откликов

**Файл:** `data_folder/output/success.yaml`

```yaml
success:
  - company: ООО "Рога и Копыта"
    vacancy: Senior Python Developer
    url: https://hh.ru/vacancy/95157421
    applied_at: "2025-11-07T15:30:45"
    cover_letter: |
      Здравствуйте!
      
      Меня заинтересовала вакансия...
    
  - company: АО "Банк России"
    vacancy: Backend Developer (Python)
    url: https://hh.ru/vacancy/95200123
    applied_at: "2025-11-07T15:32:10"
```

**Код:**
```python
def _save_company(self, job: dict, apply_result: Tuple[str, str], vacancy: dict):
    result, reason = apply_result
    company_name = job.get("company", {}).get("name", "Unknown")
    vacancy_title = vacancy.get("name", "Unknown")
    vacancy_url = vacancy.get("alternate_url", "")
    
    if result == "Success":
        self._append_to_yaml("success.yaml", {
            "company": company_name,
            "vacancy": vacancy_title,
            "url": vacancy_url,
            "applied_at": datetime.now().isoformat(),
        })
```

### Сохранение пропущенных вакансий

**Файл:** `data_folder/output/skipped.yaml`

```yaml
skipped:
  - company: ООО "Пример"
    vacancy: Junior Python Developer
    url: https://hh.ru/vacancy/12345
    reason: "Already applied to this company"
    skipped_at: "2025-11-07T15:28:30"
    
  - company: Яндекс
    vacancy: Python Backend Developer
    url: https://hh.ru/vacancy/67890
    reason: "Company in blacklist"
    skipped_at: "2025-11-07T15:29:15"
    
  - company: ООО "Низкая зп"
    vacancy: Middle Python Developer
    url: https://hh.ru/vacancy/11111
    reason: "Вакансия не интересна (Score: 65 < 70)"
    skipped_at: "2025-11-07T15:30:00"
```

### Сохранение ошибок

**Файл:** `data_folder/output/failed.yaml`

```yaml
failed:
  - company: ООО "Проблемная"
    vacancy: Python Developer
    url: https://hh.ru/vacancy/99999
    error: "resume_not_published"
    failed_at: "2025-11-07T15:31:45"
    
  - company: АО "Тест"
    vacancy: Backend Developer
    url: https://hh.ru/vacancy/88888
    error: "Не смогли откликнуться. При отклике предлагают переход на сторонний сайт"
    failed_at: "2025-11-07T15:33:20"
```

### Сохранение сопроводительных писем

**Файл:** `data_folder/output/cover_letters.txt`

```
==========================================
Компания: ООО "Рога и Копыта"
Вакансия: Senior Python Developer
URL: https://hh.ru/vacancy/95157421
Дата: 2025-11-07 15:30:45
==========================================

Здравствуйте!

Меня заинтересовала вакансия Senior Python Developer в вашей компании.
У меня 7 лет опыта разработки на Python...

С уважением,
Иван Сидоров
Telegram: @ivan_example

==========================================
==========================================


==========================================
Компания: АО "Банк России"
Вакансия: Backend Developer (Python)
URL: https://hh.ru/vacancy/95200123
Дата: 2025-11-07 15:32:10
==========================================

Добрый день!

Хочу откликнуться на вакансию Backend Developer...

С уважением,
Иван Сидоров
Telegram: @ivan_example

==========================================
==========================================
```

**Код:**
```python
def _save_cover_letter(self, company_name: str, cover_letter: str, vacancy_url: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open("data_folder/output/cover_letters.txt", "a", encoding="utf-8") as f:
        f.write("=" * 42 + "\n")
        f.write(f"Компания: {company_name}\n")
        f.write(f"URL: {vacancy_url}\n")
        f.write(f"Дата: {timestamp}\n")
        f.write("=" * 42 + "\n\n")
        f.write(cover_letter)
        f.write("\n\n" + "=" * 42 + "\n")
        f.write("=" * 42 + "\n\n\n")
```

---

## Сохранение статистики

**Файл:** `data_folder/output/last_run.yaml`

### Структура файла

```yaml
last_search:
  date: "2025-11-07T15:30:00"
  success_applies_num: 15        # Успешных откликов за сессию
  total_applies_num: 147         # Общее количество откликов (все время)
  max_applies_num: 200           # Лимит за сессию
  max_total_applies_num: 1500    # Общий лимит (опционально)
  last_apply: "2025-11-07T15:45:30"
  
statistics:
  total_vacancies_found: 347     # Всего найдено вакансий
  filtered_by_score: 298         # Отфильтровано по Score < 70
  blacklisted_companies: 12      # В черном списке
  already_applied: 7             # Уже откликались
  skipped_external: 5            # Внешние формы
  test_required: 3               # Требовали тест
  errors: 2                      # Ошибки API
  success: 15                    # Успешно
  
llm_usage:
  cover_letters_generated: 18    # Сгенерировано писем
  questions_answered: 7          # Отвечено на вопросы
  total_tokens_used: 125000      # Всего токенов
  estimated_cost_usd: 0.12       # Примерная стоимость
```

### Обновление счетчиков

**Файл:** `src/job_manager/job_applier.py` → `send_repsonse()`

```python
# Увеличиваем счетчики
self.applies_num += 1

if result == "Success":
    self.success_applies_num += 1
    self.total_applies_num += 1
    
    # Сохраняем в кэш
    self.cache["success_applies_num"] = self.success_applies_num
    self.cache["total_applies_num"] = self.total_applies_num
    self.cache["last_apply"] = datetime.now().isoformat()
    
    # Записываем на диск
    self._write_the_last_search_time()
    
    logger.info(f"✅ Количество вакансий, на которые успешно откликнулись: {self.success_applies_num}")
    logger.info(f"📊 Общее количество успешных откликов: {self.total_applies_num}")
```

### Проверка лимитов

```python
stop_reason = ""

# Лимит за сессию
if self.success_applies_num >= self.max_applies_num:
    stop_reason = f"Достигнуто максимально допустимое число откликов за запуск: {self.success_applies_num}/{self.max_applies_num}"

# Общий лимит (опционально)
elif self.max_total_applies_num is not None and self.total_applies_num >= self.max_total_applies_num:
    stop_reason = f"Достигнут общий лимит откликов: {self.total_applies_num}/{self.max_total_applies_num}"

if stop_reason:
    logger.info(stop_reason)
    return "Limit"
```

### Логирование расходов LLM

**Файл:** `data_folder/output/llm_api_calls.yaml`

```yaml
calls:
  - timestamp: "2025-11-07T15:30:45"
    type: "cover_letter"
    vacancy_id: "95157421"
    company: "ООО Рога и Копыта"
    input_tokens: 3500
    output_tokens: 420
    cost_usd: 0.000777
    model: "gpt-4o-mini"
    
  - timestamp: "2025-11-07T15:31:20"
    type: "answer_question"
    vacancy_id: "95200123"
    question: "Какой у вас опыт с Python?"
    input_tokens: 2800
    output_tokens: 85
    cost_usd: 0.000471
    model: "gpt-4o-mini"

summary:
  total_calls: 25
  total_input_tokens: 87500
  total_output_tokens: 10500
  total_cost_usd: 0.119625
  average_cost_per_call: 0.004785
```

---

## Режимы работы

**Файл:** `src/app_config.py`

### 1. Обычный режим (Production)

```python
MONKEY_MODE = False
COVER_LETTER_MODE = False
SKILL_STAT_MODE = False
RESUME_MODE = False
```

**Поведение:**
- ✅ Полная фильтрация через LLM (Score >= 70)
- ✅ Генерация персональных писем
- ✅ Отправка откликов через API
- ✅ Сохранение всех результатов

### 2. Режим обезьяны (Monkey Mode)

```python
MONKEY_MODE = True
```

**Поведение:**
- ❌ Отключена фильтрация через LLM
- ✅ **Откликаемся на ВСЕ вакансии** без оценки соответствия
- ✅ Генерация писем продолжается
- ⚠️ Используется для тестирования или массовых рассылок

**Применение:**
```python
if MONKEY_MODE is True:
    job_is_interesting = True  # Любая вакансия считается интересной
else:
    job_is_interesting = self.gpt_answerer.job_is_interesting()
```

### 3. Режим проверки писем (Cover Letter Mode)

```python
COVER_LETTER_MODE = True
```

**Поведение:**
- ✅ Фильтрация через LLM работает
- ✅ Генерация писем работает
- ❌ **Отклики НЕ отправляются**
- ✅ Все письма сохраняются в `cover_letters.txt`

**Применение:** Проверка качества генерируемых писем перед запуском

### 4. Режим сбора статистики по навыкам (Skill Stat Mode)

```python
SKILL_STAT_MODE = True
```

**Поведение:**
- ✅ Фильтрация работает
- ❌ Письма НЕ генерируются
- ❌ Отклики НЕ отправляются
- ✅ Собирается статистика по требуемым навыкам

**Файл:** `data_folder/output/skill_statistics.yaml`

```yaml
skills:
  Python: 347
  Django: 156
  FastAPI: 89
  PostgreSQL: 234
  Docker: 178
  Redis: 145
  Kafka: 67
  ...
```

### 5. Режим создания резюме (Resume Mode) - экспериментальный

```python
RESUME_MODE = True
```

**Поведение:**
- ✅ Анализ вакансий
- ❌ Отклики НЕ отправляются
- ✅ Генерация рекомендаций по улучшению резюме

---

## Обработка ошибок

### Типы ошибок и их обработка

#### 1. Ошибки API HeadHunter

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `already_applied` | Уже откликались | Пропустить, сохранить в skipped.yaml |
| `limit_exceeded` | Лимит откликов | Остановка, логирование |
| `resume_not_published` | Резюме не опубликовано | Критическая ошибка, остановка |
| `vacancy_archived` | Вакансия удалена | Пропустить |
| `captcha_required` | Требуется CAPTCHA | Пропустить или ручная обработка |
| `auth_failed` | Истек токен | Обновить токен, повторить |

#### 2. Ошибки LLM

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `RateLimitError` | Превышен лимит запросов | Ждать 60 секунд, повторить |
| `AuthenticationError` | Неверный API ключ | Проверить secrets.yaml |
| `APIConnectionError` | Нет интернета | Повторить через 10 секунд |
| `InvalidRequestError` | Слишком большой промпт | Сократить контекст |
| `TimeoutError` | Долгий ответ | Повторить или пропустить |

**Обработка:**
```python
try:
    cover_letter = self.gpt_answerer.write_cover_letter()
except RateLimitError:
    logger.warning("⚠️ Rate limit LLM. Ждем 60 секунд")
    time.sleep(60)
    cover_letter = self.gpt_answerer.write_cover_letter()
except Exception as e:
    logger.error(f"❌ Ошибка при генерации письма: {str(e)}")
    return "Error", f"LLM error: {str(e)}"
```

#### 3. Ошибки Selenium

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `NoSuchElementException` | Элемент не найден | Изменилась верстка сайта |
| `TimeoutException` | Долгая загрузка | Увеличить timeout |
| `WebDriverException` | Проблема с драйвером | Обновить ChromeDriver |
| `SessionNotCreatedException` | Chrome не установлен | Установить Chrome |

**Обработка:**
```python
try:
    answer_result = self.find_and_handle_questions(vacancy, cover_letter_text)
except NoSuchElementException:
    logger.error("❌ Не удалось найти форму вопросов. Возможно, изменилась верстка")
    return "Skip", "Form not found"
except Exception as e:
    logger.error(f"❌ Ошибка Selenium: {str(e)}")
    return "Skip", f"Selenium error: {str(e)}"
finally:
    if self.driver:
        self.driver.close()
        self.driver = None
```

### Retry механизм

```python
def api_request_with_retry(self, url: str, params: dict, max_retries: int = 3):
    """API запрос с повторными попытками"""
    for attempt in range(max_retries):
        try:
            response = self.api.api_request(url=url, params=params)
            return response
        except APIConnectionError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"⚠️ Попытка {attempt + 1}/{max_retries}. Ждем {wait_time}с")
                time.sleep(wait_time)
            else:
                logger.error("❌ Все попытки исчерпаны")
                raise
```

---

## Примеры работы

### Пример 1: Успешный отклик

**Лог:**
```
2025-11-07 15:30:00 INFO - Обрабатываем вакансию: Senior Python Developer (ООО Рога и Копыта)
2025-11-07 15:30:01 INFO - Проверяем, насколько вакансия может быть интересна
2025-11-07 15:30:05 INFO - Степень 'интересности' вакансии: 85
2025-11-07 15:30:06 INFO - Генерируем сопроводительное письмо
2025-11-07 15:30:12 INFO - Сопроводительное письмо сгенерировано
2025-11-07 15:30:13 INFO - Деанонимизация персональных данных
2025-11-07 15:30:14 INFO - Отправка отклика через API
2025-11-07 15:30:16 INFO - ✅ Успешно откликнулись на вакансию компании ООО Рога и Копыта
2025-11-07 15:30:16 INFO - Количество вакансий, на которые успешно откликнулись: 15
2025-11-07 15:30:16 INFO - Общее количество успешных откликов: 147
```

**Файлы:**
- ✅ `success.yaml` - запись добавлена
- ✅ `cover_letters.txt` - письмо сохранено
- ✅ `last_run.yaml` - счетчики обновлены

### Пример 2: Вакансия не интересна

**Лог:**
```
2025-11-07 15:28:00 INFO - Обрабатываем вакансию: Junior Python Developer (ООО Низкая ЗП)
2025-11-07 15:28:01 INFO - Проверяем, насколько вакансия может быть интересна
2025-11-07 15:28:04 INFO - Степень 'интересности' вакансии: 55
2025-11-07 15:28:04 INFO - Работа не интересна: Salary significantly below expectations (80k vs 300k required) -20, Experience requirement too low for candidate -10
2025-11-07 15:28:04 DEBUG - Вакансия не интересна, пропускаем
```

**Файлы:**
- ✅ `skipped.yaml` - запись с причиной

### Пример 3: Компания в черном списке

**Лог:**
```
2025-11-07 15:29:00 INFO - Обрабатываем вакансию: Backend Developer (Яндекс)
2025-11-07 15:29:01 WARNING - Компания Яндекс в черном списке, пропускаем
```

**Файлы:**
- ✅ `skipped.yaml` - причина: "Company in blacklist"

### Пример 4: Требуется тест (Selenium)

**Лог:**
```
2025-11-07 15:31:00 INFO - Обрабатываем вакансию: Python Developer (ООО Тестовая)
2025-11-07 15:31:01 INFO - Проверяем, насколько вакансия может быть интересна
2025-11-07 15:31:05 INFO - Степень 'интересности' вакансии: 82
2025-11-07 15:31:06 INFO - Генерируем сопроводительное письмо
2025-11-07 15:31:12 INFO - Сопроводительное письмо сгенерировано
2025-11-07 15:31:13 INFO - Деанонимизация персональных данных
2025-11-07 15:31:14 INFO - Отправка отклика через API
2025-11-07 15:31:16 INFO - 📝 Для отклика требуется пройти тест
2025-11-07 15:31:17 INFO - Инициализация Selenium WebDriver
2025-11-07 15:31:20 INFO - Авторизация на hh.ru
2025-11-07 15:31:25 INFO - Переход на страницу вакансии
2025-11-07 15:31:27 INFO - Найдено 3 вопроса
2025-11-07 15:31:28 INFO - Вопрос 1: "Какой у вас опыт работы с Python?"
2025-11-07 15:31:29 INFO - Ответ найден в кэше
2025-11-07 15:31:30 INFO - Вопрос 2: "Готовы ли вы работать в офисе?"
2025-11-07 15:31:34 INFO - Ответ сгенерирован через LLM
2025-11-07 15:31:35 INFO - Вопрос 3: "Ваши ожидания по зарплате?"
2025-11-07 15:31:36 INFO - Ответ найден в кэше
2025-11-07 15:31:37 INFO - Отправка формы
2025-11-07 15:31:40 INFO - ✅ Успешно откликнулись на вакансию компании ООО Тестовая
2025-11-07 15:31:41 INFO - Закрытие браузера
```

### Пример 5: Достигнут лимит

**Лог:**
```
2025-11-07 16:45:00 INFO - Обрабатываем вакансию: Full Stack Developer (ООО Последняя)
2025-11-07 16:45:05 INFO - Степень 'интересности' вакансии: 91
2025-11-07 16:45:12 INFO - Сопроводительное письмо сгенерировано
2025-11-07 16:45:16 INFO - ✅ Успешно откликнулись на вакансию компании ООО Последняя
2025-11-07 16:45:16 INFO - Количество вакансий, на которые успешно откликнулись: 200
2025-11-07 16:45:16 INFO - 🛑 Достигнуто максимально допустимое число откликов за запуск: 200/200
2025-11-07 16:45:16 INFO - Завершение работы
```

---

## Отладка и мониторинг

### Логирование

**Уровни логирования:**

| Уровень | Назначение | Примеры |
|---------|------------|---------|
| `DEBUG` | Детальная отладка | Содержимое писем, параметры API |
| `INFO` | Основные события | Начало/конец обработки, успехи |
| `WARNING` | Предупреждения | Пропущенные вакансии, rate limits |
| `ERROR` | Ошибки | Сбои API, ошибки LLM |
| `CRITICAL` | Критические ошибки | Отсутствие токенов, невалидный конфиг |

**Настройка:** `src/logger_config.py`

```python
logger = logging.getLogger("job_applier")
logger.setLevel(logging.INFO)

# Вывод в файл
file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

# Вывод в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
```

### Мониторинг в реальном времени

```bash
# Следить за логами
tail -f logs/app.log

# Фильтр по успешным откликам
tail -f logs/app.log | grep "✅"

# Фильтр по ошибкам
tail -f logs/app.log | grep "ERROR\|WARNING"
```

### Проверка результатов

```bash
# Количество успешных откликов
grep -c "company:" data_folder/output/success.yaml

# Количество пропущенных
grep -c "reason:" data_folder/output/skipped.yaml

# Топ причин пропуска
grep "reason:" data_folder/output/skipped.yaml | sort | uniq -c | sort -rn

# Общая стоимость LLM
grep "total_cost_usd:" data_folder/output/llm_api_calls.yaml
```

### Аналитика

**Скрипт:** `scripts/analyze_results.py` (создать отдельно)

```python
import yaml
from collections import Counter

# Загрузка данных
with open("data_folder/output/success.yaml") as f:
    success = yaml.safe_load(f)["success"]

with open("data_folder/output/skipped.yaml") as f:
    skipped = yaml.safe_load(f)["skipped"]

# Статистика
print(f"✅ Успешных откликов: {len(success)}")
print(f"⏭️ Пропущено: {len(skipped)}")

# Топ причин пропуска
reasons = Counter([s["reason"] for s in skipped])
print("\n📊 Топ причин пропуска:")
for reason, count in reasons.most_common(5):
    print(f"  {count:3d} - {reason}")

# Топ компаний, на которые откликнулись
companies = Counter([s["company"] for s in success])
print("\n🏢 Топ компаний:")
for company, count in companies.most_common(10):
    print(f"  {count:2d} - {company}")
```

### Полезные метрики

| Метрика | Как посчитать |
|---------|---------------|
| Conversion Rate | `(success / (success + skipped)) × 100%` |
| Средняя стоимость отклика | `total_llm_cost / success_count` |
| Среднее время на отклик | `total_time / success_count` |
| Процент отклика через Selenium | `(test_required / success) × 100%` |

---

## Дополнительные ресурсы

### Связанная документация

- **Фаза поиска:** [phase-search.md](phase-search.md)
- **Основная документация:** [README.md](README.md)
- **Архитектура:** [docs/architecture.md](docs/architecture.md)
- **API HeadHunter:** [hh-api-methods.md](hh-api-methods.md)
- **Промпты LLM:** [docs/prompts/](docs/prompts/)

### Полезные ссылки

- **API HeadHunter:** https://github.com/hhru/api
- **Документация по откликам:** https://github.com/hhru/api/blob/master/docs/negotiations.md
- **OpenAI Pricing:** https://openai.com/pricing
- **Selenium Python:** https://selenium-python.readthedocs.io/

### Конфигурационные файлы

| Файл | Назначение |
|------|------------|
| `data_folder/search_config/search_config.yaml` | Параметры поиска и откликов |
| `data_folder/secrets/secrets.yaml` | Токены и ключи API |
| `src/app_config.py` | Режимы работы, пороги |
| `src/llm/prompts.py` | Промпты для LLM |

---

## FAQ

### 1. Почему отклики не отправляются?

**Проверьте:**
- ❓ Режим работы: `COVER_LETTER_MODE` или `SKILL_STAT_MODE` должны быть `False`
- ❓ Токен доступа: `access_token` в `secrets.yaml` актуален?
- ❓ Резюме опубликовано на hh.ru?
- ❓ Лимит откликов не достигнут?

### 2. Почему письма одинаковые?

**Причины:**
- 📝 Используется `fixed_cover_letter` в конфиге
- 🔁 LLM кэширует похожие запросы

**Решение:** Убрать `cover_letter` из конфига, LLM будет генерировать уникальные

### 3. Как снизить расходы на LLM?

**Способы:**
- 💰 Использовать более дешевую модель (`gpt-4o-mini` вместо `gpt-4o`)
- 💰 Использовать готовое письмо (`fixed_cover_letter`)
- 💰 Сократить резюме (убрать лишние детали)
- 💰 Включить кэширование ответов на вопросы

### 4. Что делать, если появляется CAPTCHA?

**Решения:**
- 🤖 Интеграция с сервисом распознавания (2captcha)
- 👤 Ручная обработка через уведомления в Telegram
- ⏰ Увеличить паузы между откликами

### 5. Как проверить качество писем перед запуском?

```python
# В app_config.py
COVER_LETTER_MODE = True  # Только генерация, без отправки
```

Затем проверить `data_folder/output/cover_letters.txt`

---

**Версия документа:** 1.0  
**Дата создания:** 7 ноября 2025  
**Автор:** AI Assistant на основе анализа кодовой базы

