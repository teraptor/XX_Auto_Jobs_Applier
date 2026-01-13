# JobApplier - Контракты и интерфейсы

## Назначение

JobApplier - это ядро модуля job_manager, реализующее основную бизнес-логику поиска вакансий и подачи откликов.

---

## Структура данных

```
JobApplier:
    # Зависимости
    api: HeadHunterAPI
    resume_component: ResumeScraper
    search_component: SearchCustomizer
    gpt_answerer: GPTAnswerer?
    
    # Параметры конфигурации
    user_id: String
    hh_login: String
    hh_password: String
    resume_id: String
    resume_titles: List[String]
    job_title: String
    max_applies_num: Int
    max_total_applies_num: Int?
    apply_once_at_company: Bool
    skip_companies_with_test: Bool
    fixed_cover_letter: String?
    job_blacklist: List[String]
    
    # Состояние и кэш
    success_companies: Map[String]Map[String]List[JobInfo]  # resume_id -> company_id -> []job_info
    skipped_companies: Map[String]Map[String]List[JobInfo]
    failed_companies: Map[String]Map[String]List[JobInfo]
    seen_answers: List[AnswerCache]
    skill_stat: Map[String]Int
    cache: Map[String]Any
    
    # Текущее состояние выполнения
    driver: WebDriver?
    resume: Map[String]Any
    resume_recommendations: String
    job_key_skills: List[String]
    jobs_no_info: List[JobNoInfo]
    page_num: Int
    resume_vac_page_num: Int
    error_num: Int
    applies_num: Int
    success_applies_num: Int
    total_applies_num: Int
    previous_apply_number: Int
```

### Вложенные структуры

```
JobInfo:
    vacancy_id: String
    job_title: String
    link: String
    reason: String

AnswerCache:
    question: String
    answer: String

JobNoInfo:
    job_title: String
    link: String
    reason: String
```

---

## Конструктор

**Сигнатура**:
```
NewJobApplier(api: HeadHunterAPI, resume_component: ResumeScraper, search_component: SearchCustomizer) -> JobApplier
```

**Входные параметры**:
- `api` - клиент HeadHunter API
- `resume_component` - компонент сбора резюме
- `search_component` - компонент настройки поиска

**Инициализация**:
1. Сохранить зависимости
2. Установить gpt_answerer = null
3. Инициализировать пустые коллекции:
   - jobs_no_info = []
   - job_key_skills = []
4. Установить начальные значения:
   - driver = null
   - resume_recommendations = ""
   - page_num = 0
   - resume_vac_page_num = -1
   - error_num = 0
   - total_applies_num = 0
5. Вывести INFO в лог

---

## Публичные методы

### set_parameters

**Сигнатура**:
```
set_parameters(parameters: Map[String]Any) -> void
```

**Назначение**: Установить параметры конфигурации

**Входные параметры**:
- `parameters` - параметры из search_config.yaml + дополнительные

**Логика**:
1. Вывести INFO: "Установка параметров JobApplier"
2. Извлечь обязательные параметры:
   - user_id = parameters["user_id"]
   - resume_id = parameters["resume_id"]
   - resume_titles = parameters["resume_titles"]
   - job_title = resume_component.job_title
3. Извлечь опциональные параметры с дефолтами:
   - hh_login = parameters.get("hh_login", "")
   - hh_password = parameters.get("hh_password", "")
   - max_applies_num = parameters.get("max_applies_num", 100)
   - max_total_applies_num = parameters.get("max_total_applies_num", 1500)
   - apply_once_at_company = parameters.get("apply_once_at_company", true)
   - skip_companies_with_test = parameters.get("skip_companies_with_test", false)
   - fixed_cover_letter = parameters.get("cover_letter", null)
4. Обработать job_blacklist:
   - job_blacklist = parameters.get("job_blacklist", [])
   - Если не пусто: санитизировать каждый элемент (_sanitize_text)
5. Загрузить данные из файлов:
   - success_companies = _load_companies_from_yaml("success.yaml")
   - skipped_companies = _load_companies_from_yaml("skipped.yaml")
   - failed_companies = _load_companies_from_yaml("failed.yaml")
   - seen_answers = _load_data_from_yaml("answers.yaml")
   - skill_stat = _load_data_from_yaml("skill_stat.yaml")
6. Загрузить кэш:
   - cache = _load_cache()
7. Инициализировать счетчики:
   - applies_num = 0
   - previous_apply_number = _check_the_previous_apply_number()
   - success_applies_num = previous_apply_number
   - total_applies_num = cache.get("total_applies_num", 0)
8. Вывести INFO: "Параметры установлены"

---

### set_gpt_answerer

**Сигнатура**:
```
set_gpt_answerer(gpt_answerer: GPTAnswerer) -> void
```

**Назначение**: Установить компонент LLM

**Входные параметры**:
- `gpt_answerer` - компонент для работы с AI

**Логика**:
1. Сохранить this.gpt_answerer = gpt_answerer

---

### set_resume

**Сигнатура**:
```
set_resume(resume: Map[String]Any) -> void
```

**Назначение**: Установить данные резюме

**Входные параметры**:
- `resume` - структурированные данные резюме

**Логика**:
1. Сохранить this.resume = resume

---

### search_vacancies

**Сигнатура**:
```
search_vacancies(page_num: Int = 0) -> List[Map[String]Any]
```

**Назначение**: Поиск вакансий (комбинация похожих на резюме + общий поиск)

**Входные параметры**:
- `page_num` - номер страницы (начиная с 0)

**Возвращаемое значение**:
- List[Map[String]Any] - список вакансий

**Логика**:
1. Создать search_params = {"page": page_num, "per_page": 10}
2. Добавить параметры из search_component.search_params
3. Инициализировать vacancies = []

4. **Первый этап - вакансии похожие на резюме**:
   - Если resume_vac_page_num == -1 (еще не начинали поиск похожих):
     - url = f"https://api.hh.ru/resumes/{resume_id}/similar_vacancies"
     - resume_vacancies = api.api_request(url, params=search_params)
     - Если resume_vacancies["items"] пусто:
       - resume_vac_page_num = page_num (закончились похожие)
     - Иначе:
       - vacancies = resume_vacancies["items"]

5. **Второй этап - общий поиск**:
   - Если page_num == 0 ИЛИ resume_vac_page_num > -1:
     - search_params_copy = копия search_params
     - search_params_copy["page"] = page_num - max(resume_vac_page_num, 0)
     - search_params_copy["text"] = job_title
     - url = "https://api.hh.ru/vacancies"
     - main_vacancies = api.api_request(url, params=search_params_copy)
     - Если resume_vac_page_num > -1:
       - vacancies = main_vacancies["items"]

6. **Логирование статистики**:
   - Если page_num == 0 И resume_vac_page_num == -1:
     - total_found = resume_vacancies["found"] + main_vacancies["found"]
     - Вывести INFO: f"Найдено {total_found} вакансий"

7. Вернуть vacancies

---

### scrape_vacancy

**Сигнатура**:
```
scrape_vacancy(vacancy: Map[String]Any) -> Map[String]Any
```

**Назначение**: Собрать детальную информацию о вакансии

**Входные параметры**:
- `vacancy` - краткая информация о вакансии из списка

**Возвращаемое значение**:
- Map[String]Any - детальная информация о вакансии

**Логика**:
1. Создать job = {}
2. Извлечь базовую информацию:
   - job["job_title"] = vacancy["name"]
   - job["vacancy_id"] = vacancy["id"]
   - job["company_id"] = vacancy["employer"]["id"]
   - job["company_name"] = vacancy["employer"]["name"]
   - job["area"] = vacancy["area"]["name"]
3. Извлечь опциональные поля (если присутствуют):
   - salary
   - address
   - contacts
   - department (company_department)
   - accredited_it_employer
   - work_format
   - work_schedule_by_days
   - employment_form
   - experience (required_experience)
   - professional_roles
   - night_shifts
   - internship (is_internship)
   - accept_temporary (accept_temporary_employment)
4. Извлечь из snippet:
   - requirement
   - responsibility
5. Сохранить has_test_task = vacancy["has_test"]
6. Получить детали вакансии:
   - url = f"https://api.hh.ru/vacancies/{vacancy['id']}"
   - vacancy_description = api.api_request(url)
7. Обработать описание:
   - job_description = vacancy_description["description"]
   - Удалить HTML теги (regex: <[^>]+>)
   - job["job_description"] = очищенное описание
8. Дополнительные поля из детального описания:
   - accept_handicapped_employers
   - driver_license_types (required_driver_licenses)
   - key_skills → сохранить в this.job_key_skills
9. Вернуть job

---

### start_applying

**Сигнатура**:
```
start_applying() -> void
```

**Назначение**: Главный цикл поиска и откликов

**Логика**:
1. **Инициализация времени поиска**:
   - Если cache["last_run"] существует:
     - last_run = parse(cache["last_run"])
     - cache["last_run"] = (last_run + 24 часа).format()
   - Иначе:
     - cache["last_run"] = текущее время

2. **Генерация рекомендаций по резюме**:
   - Вызвать resume_improvement_recommendations()

3. **Главный цикл**:
   - result = ""
   - WHILE success_applies_num < max_applies_num И applies_num < 400:
     
     - **Получение вакансий**:
       - vacancies = search_vacancies(page_num)
       - Если vacancies пусто:
         - Если page_num == 1:
           - Вывести WARNING: "Вакансии не найдены"
         - Выйти из цикла
     
     - **Обработка каждой вакансии**:
       - Для каждой vacancy в vacancies:
         - url = vacancy["alternate_url"]
         - Попытка:
           - result = send_response(vacancy)
           - Если result == "Limit":
             - Вывести WARNING: "Достигнут лимит"
             - Выйти из цикла
         - При Exception:
           - Получить stack trace
           - Вывести ERROR в лог
           - Увеличить error_num
           - Если error_num == MAX_APPLIES_NUM:
             - Вывести ERROR: "Критическое число ошибок"
             - result = "Error"
             - Выйти из цикла
           - Продолжить следующую вакансию
         - Иначе (успех):
           - error_num = 0
     
     - **Проверка на выход**:
       - Если result in ["Limit", "Error"]:
         - Выйти из главного цикла
       - page_num += 1
       - Вывести INFO: f"Страница {page_num}"

4. **Завершение**:
   - Вывести INFO: f"Откликов отправлено: {success_applies_num}"
   - Если НЕ (COVER_LETTER_MODE ИЛИ SKILL_STAT_MODE ИЛИ RESUME_MODE) И result != "Error":
     - Если previous_apply_number < success_applies_num:
       - Вывести INFO: "Отсылаем отчет"
       - Вызвать send_report()
       - Вызвать _write_the_last_search_time()

---

### send_response

**Сигнатура**:
```
send_response(vacancy: Map[String]Any) -> String
```

**Назначение**: Обработать одну вакансию (проверки + отклик)

**Входные параметры**:
- `vacancy` - данные вакансии

**Возвращаемое значение**:
- String - результат: "Success", "Skip", "Error", "Limit"

**Логика**:
1. **Сбор информации**:
   - job = scrape_vacancy(vacancy)
   - minimum_job_time = текущее_время + MINIMUM_WAIT_TIME_SEC
   - company_name = job["company_name"]
   - company_job_title = job["job_title"]
   - Вывести INFO: f"Найдена вакансия {company_job_title}"

2. **Проверка черного списка**:
   - Если _is_blacklisted(_sanitize_text(company_name)):
     - apply_result = ("Skip", "Вакансия в черном списке")
     - Вывести WARNING
     - Пауза 1-2 сек

3. **Проверка на тестовое задание**:
   - Если (НЕ hh_login ИЛИ НЕ hh_password) И job["has_test_task"]:
     - apply_result = ("Skip", "Нет возможности обработать тест")
     - Вывести WARNING
     - _collect_job_info(company_job_title, url, reason)
     - Пауза 1-2 сек

4. **Проверка на дубликаты**:
   - Иначе:
     - (is_applied, reason) = _is_already_applied_to_job_or_company(job)
     - Если is_applied:
       - apply_result = ("Skip", reason)
       - Вывести WARNING
       - Пауза 1-2 сек

5. **Оценка вакансии и отклик**:
   - Иначе:
     - gpt_answerer.set_job(job)
     
     - **Определение интересности**:
       - Если MONKEY_MODE == true:
         - job_is_interesting = true
       - Иначе:
         - job_is_interesting = gpt_answerer.job_is_interesting()
     
     - **Обработка результата**:
       - Если job_is_interesting == true:
         - _update_skill_stat(job_key_skills)
         - apply_result = apply_job(vacancy, company_name, company_job_title, job)
         - (result, reason) = apply_result
         - Если result == "Skip" И reason.startswith("Не смогли"):
           - _collect_job_info(company_job_title, url, reason)
       - Иначе если job_is_interesting == null:
         - apply_result = ("Error", "Ошибка LLM")
       - Иначе:
         - apply_result = ("Skip", "Вакансия не интересна")
         - Вывести DEBUG

6. **Обработка результата**:
   - (result, _) = apply_result
   
   - **Режимы сбора информации**:
     - Если COVER_LETTER_MODE ИЛИ SKILL_STAT_MODE ИЛИ RESUME_MODE:
       - Вернуть "OK"
   
   - **Обновление счетчиков**:
     - applies_num += 1
     - Если result == "Success":
       - success_applies_num += 1
       - total_applies_num += 1
       - cache["success_applies_num"] = success_applies_num
       - cache["total_applies_num"] = total_applies_num
       - cache["last_apply"] = текущее время
       - _write_the_last_search_time()
       - Вывести INFO со статистикой
   
   - **Сохранение результата**:
     - Если result != "Limit":
       - _save_company(job, apply_result, vacancy)

7. **Ожидание минимального времени**:
   - time_left = int(minimum_job_time - текущее_время)
   - Если time_left > 0:
     - sleep(time_left, time_left + 5)

8. **Проверка лимитов**:
   - Если result == "Limit":
     - Вернуть "Limit"
   - stop_reason = ""
   - Если success_applies_num >= max_applies_num:
     - stop_reason = "Достигнут лимит за запуск"
   - Если max_total_applies_num И total_applies_num >= max_total_applies_num:
     - stop_reason = "Достигнут общий лимит"
   - Если stop_reason:
     - Вывести INFO: stop_reason
     - Вернуть "Limit"

9. Вернуть result

---

### apply_job

**Сигнатура**:
```
apply_job(vacancy: Map[String]Any, company_name: String, job_title: String, job: Map[String]Any) -> (String, String)
```

**Назначение**: Отправить отклик на вакансию

**Входные параметры**:
- `vacancy` - данные вакансии
- `company_name` - название компании
- `job_title` - название должности
- `job` - детальные данные вакансии

**Возвращаемое значение**:
- (String, String) - (результат, причина)
  - результат: "Success", "Skip", "Error", "Limit"
  - причина: описание (пусто для Success)

**Логика**:
1. **Обработка внутри try-catch**:
   
   **Генерация сопроводительного письма**:
   - Если fixed_cover_letter:
     - Вывести INFO: "Берем готовое письмо"
     - cover_letter_text = fixed_cover_letter
   - Иначе если НЕ RESUME_MODE И НЕ SKILL_STAT_MODE:
     - cover_letter_text = gpt_answerer.write_cover_letter()
     - cover_letter_text = resume_component.deanonymize_personal_information(cover_letter_text)
     - _save_cover_letter(company_name, cover_letter_text, vacancy["alternate_url"])

   **Режимы работы**:
   - Если COVER_LETTER_MODE:
     - Вывести INFO: "Режим отладки писем"
     - // НЕ откликаемся
   
   - Иначе если SKILL_STAT_MODE:
     - Вывести INFO: "Режим сбора статистики"
     - // НЕ откликаемся
   
   - Иначе если RESUME_MODE:
     - Вывести INFO: "Режим резюме"
     - write_and_upload_resume(job, vacancy["alternate_url"])
     - // НЕ откликаемся

   **Отправка отклика**:
   - Иначе:
     - params = {
         "message": cover_letter_text,
         "resume_id": resume_id,
         "vacancy_id": vacancy["id"]
       }
     - response = api.api_request(type="post", url="https://api.hh.ru/negotiations", params=params)
     
     - **Обработка ответа HTML**:
       - Если "response_text" в response И "<!doctype html>" в response["response_text"]:
         - Вернуть ("Skip", "Переход на сторонний сайт")
     
     - **Обработка ошибок**:
       - Если "errors" в response:
         - errors = response["errors"]
         - Для каждой error в errors:
           
           - **Лимит откликов**:
             - Если error["value"] == "limit_exceeded":
               - Вывести WARNING
               - Вернуть ("Limit", "")
           
           - **Требуется тест**:
             - Если error["value"] == "test_required" И hh_login И hh_password:
               - Вывести INFO: "Требуется пройти тест"
               - driver = init_driver()
               - (answer_result, answer_text) = find_and_handle_questions(vacancy, cover_letter_text)
               - Если driver != null:
                 - driver.close()
                 - driver = null
               - Если НЕ answer_result:
                 - Вернуть ("Skip", answer_text)
               - Вывести INFO: "Успешно откликнулись"
               - Вернуть ("Success", "")
         
         - **Прочие ошибки**:
           - error_message = join([error["value"] для error в errors], ";")
           - Вывести WARNING
           - Вернуть ("Skip", error_message)
     
     - **Успех**:
       - Вывести INFO: "Успешно откликнулись"
   
   - Пауза

2. **Обработка исключений**:
   - При Exception:
     - Получить stack trace
     - Вывести ERROR в лог
     - Если driver != null:
       - driver.close()
       - driver = null
     - Вернуть ("Error", str(exception))

3. Вернуть ("Success", "")

---

### find_and_handle_questions

**Сигнатура**:
```
find_and_handle_questions(vacancy: Map[String]Any, cover_letter_text: String) -> (Bool, String)
```

**Назначение**: Ответить на вопросы работодателя через Selenium

**Входные параметры**:
- `vacancy` - данные вакансии
- `cover_letter_text` - текст сопроводительного письма

**Возвращаемое значение**:
- (Bool, String) - (успех, сообщение об ошибке)

**Логика**:
1. **Аутентификация**:
   - authenticator = новый Authenticator(driver)
   - authenticator.set_parameters(hh_login, hh_password)
   - result = authenticator.start()
   - Если НЕ result:
     - Вывести WARNING: "Не смогли зайти"
     - Закрыть driver
     - Вернуть (false, "Не смогли зайти на сайт")

2. **Переход на страницу отклика**:
   - url = f"https://hh.ru/applicant/vacancy_response?vacancyId={vacancy['id']}"
   - driver.get(url)
   - Пауза 2-3 сек

3. **Очистка мешающих элементов**:
   - _handle_interfering_messages()

4. **Поиск и обработка вопросов**:
   - questions = driver.find_elements(xpath="//*[@data-qa='task-body']")
   - Если questions пусто:
     - Вывести WARNING: "Вопросы не найдены"
     - Вернуть (false, "Вопросы не найдены")
   - Вывести INFO: "Найдены вопросы"
   - Для каждого question в questions:
     - (answer, answer_text) = handle_question(question)
     - Если НЕ answer:
       - Вывести WARNING: "Прерываем отклик"
       - Вернуть (false, answer_text)

5. **Выбор резюме**:
   - _handle_interfering_messages()
   - (answer, answer_text) = _select_correct_resume()
   - Если НЕ answer:
     - Вернуть (false, answer_text)

6. **Ввод сопроводительного письма**:
   - (answer, answer_text) = _enter_cover_letter(cover_letter_text)
   - Если НЕ answer:
     - Вернуть (false, answer_text)

7. **Отправка отклика**:
   - _handle_interfering_messages()
   - apply_element = driver.find_elements(xpath="//*[text()='Откликнуться']")
   - Если НЕ apply_element:
     - Вывести ERROR: "Не нашли кнопку"
     - Вернуть (false, "Не нашли кнопку отклика")
   - scroll_slow(driver, apply_element[0])
   - apply_element[0].click()
   - Пауза 3-5 сек

8. Вернуть (true, "")

---

## Продолжение в следующих документах

Следующие методы и логика описаны в:
- [JobApplier - Обработка вопросов](05_job_applier_questions.md)
- [JobApplier - Вспомогательные методы](05_job_applier_helpers.md)
- [JobApplier - Управление данными](05_job_applier_data.md)

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Назначение**: Спецификация JobApplier для реализации на Go

