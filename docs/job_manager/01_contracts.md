# Контракты и интерфейсы модуля Job Manager

## Введение

Данный документ описывает контракты (интерфейсы) всех компонентов модуля `job_manager` для реализации на языке Go. Описания предоставлены без примеров кода, в форме спецификации.

---

## Соглашения о типах данных

### Базовые типы
- **String** - строка UTF-8
- **Int** - целое число
- **Int64** - 64-битное целое число
- **Float64** - число с плавающей точкой
- **Bool** - логическое значение
- **DateTime** - дата/время в формате ISO 8601
- **Map[K]V** - словарь (ключ K, значение V)
- **List[T]** - список элементов типа T
- **Bytes** - массив байтов

### Nullable типы
Обозначаются символом `?` после типа: `String?` - nullable строка

---

## 1. HeadHunterAPI

### Назначение
HTTP клиент для взаимодействия с REST API HeadHunter.

### Структура данных

```
HeadHunterAPI:
    secrets: Map[String]Any
    access_token: String
    refresh_token: String
    secrets_file: String
```

### Конструктор

**Входные параметры**:
- `secrets` - Map[String]Any - секретные данные из secrets.yaml

**Инициализация**:
1. Сохранить secrets
2. Извлечь access_token из secrets["access_token"]
3. Извлечь refresh_token из secrets["refresh_token"]
4. Установить secrets_file = "data_folder/secrets/secrets.yaml"
5. Если secrets["user_id"] отсутствует или пусто:
   - Вызвать _get_user_id()

**Побочные эффекты**:
- Может обновить secrets["user_id"]
- Может записать в secrets_file

---

### Методы

#### api_request

**Сигнатура**:
```
api_request(url: String, type: String = "get", params: Map[String]String = {}) -> Map[String]Any
```

**Назначение**: Выполнить HTTP запрос к API с обработкой ошибок

**Входные параметры**:
- `url` - URL эндпоинта
- `type` - тип запроса: "get" или "post"
- `params` - параметры запроса

**Возвращаемое значение**:
- Map[String]Any - JSON ответ от API

**Исключения**:
- ValueError - если response содержит "error" или необработанные "errors"

**Логика**:
1. Вызвать _send_request(url, type, params)
2. Если response["error"] существует:
   - Выбросить ValueError с описанием ошибки
3. Если response["errors"] существует:
   - Для каждой ошибки в response["errors"]:
     - Если error["type"] == "too_many_requests":
       - Вывести WARNING в лог
       - Вызвать pause(3600, 7200) // пауза 1-2 часа
       - Повторить _send_request(url, type, params)
       - Выйти из цикла
     - Если error["value"] == "token_expired":
       - Вывести WARNING в лог
       - Вызвать refress_access_token()
       - Повторить _send_request(url, type, params)
       - Выйти из цикла
     - Если error["value"] in ["test_required", "limit_exceeded", "application_denied", "already_applied"]:
       - Выйти из цикла (не ошибка)
   - Если дошли до конца цикла (ошибка не обработана):
     - Выбросить ValueError
4. Вернуть response

---

#### refress_access_token

**Сигнатура**:
```
refress_access_token() -> void
```

**Назначение**: Обновить токены доступа через OAuth refresh token flow

**Исключения**:
- ValueError - если обновление не удалось

**Логика**:
1. Вывести INFO в лог: "Пытаемся обновить токен доступа"
2. Сформировать POST запрос:
   - URL: "https://api.hh.ru/token"
   - Данные:
     ```
     {
       "grant_type": "refresh_token",
       "refresh_token": this.refresh_token
     }
     ```
3. Выполнить запрос без Authorization header
4. Парсинг ответа:
   - Если "access_token" И "refresh_token" присутствуют:
     - Обновить this.secrets["access_token"]
     - Обновить this.secrets["refresh_token"]
     - Обновить this.access_token
     - Обновить this.refresh_token
     - Вызвать _update_secretes()
     - Вывести INFO: "Токен доступа обновлен"
     - Выйти из функции
   - Если "error" присутствует:
     - Выбросить ValueError
   - Если "errors" присутствует:
     - Выбросить ValueError
   - Если "error_description" == "token not expired":
     - Вывести INFO: "Обновление не требуется"
     - Выйти из функции
5. Выбросить ValueError: "Неизвестная ошибка"

---

#### _send_request (приватный)

**Сигнатура**:
```
_send_request(url: String, type: String, params: Map[String]String?) -> Map[String]Any
```

**Назначение**: Непосредственная отправка HTTP запроса

**Входные параметры**:
- `url` - URL эндпоинта
- `type` - "get" или "post"
- `params` - параметры запроса (nullable)

**Возвращаемое значение**:
- Map[String]Any - распарсенный JSON или {"response_text": text}

**Логика**:
1. Если params == null, установить params = {}
2. Сформировать headers:
   ```
   {
     "Authorization": "Bearer " + this.access_token
   }
   ```
3. Если type == "get":
   - Выполнить GET запрос с headers и params
4. Если type == "post":
   - Выполнить POST запрос с headers и params
5. Иначе:
   - Выбросить ValueError: "type_ parameter can only be 'post' or 'get'"
6. Попытаться распарсить response.body как JSON:
   - Успех: вернуть JSON
   - Ошибка парсинга: вернуть {"response_text": response.text}

---

#### _get_user_id (приватный)

**Сигнатура**:
```
_get_user_id() -> String
```

**Назначение**: Получить ID пользователя через API

**Возвращаемое значение**:
- String - user_id

**Побочные эффекты**:
- Обновляет this.secrets["user_id"]
- Вызывает _update_secretes()

**Логика**:
1. url = "https://api.hh.ru/me"
2. response = this.api_request(url, type="get")
3. this.secrets["user_id"] = response["id"]
4. Вывести INFO в лог
5. Вызвать _update_secretes()

---

#### _update_secretes (приватный)

**Сигнатура**:
```
_update_secretes() -> void
```

**Назначение**: Сохранить обновленные секреты в файл

**Логика**:
1. Загрузить secrets из this.secrets_file (YAML)
2. Обновить secrets["user_id"] = this.secrets["user_id"]
3. Обновить secrets["access_token"] если изменился
4. Обновить secrets["refresh_token"] если изменился
5. Сохранить secrets в this.secrets_file (YAML)

---

## 2. Authenticator

### Назначение
Управление веб-автоматизацией для входа на hh.ru через Selenium.

### Структура данных

```
Authenticator:
    driver: WebDriver?
    login: String?
    password: String?
```

### Конструктор

**Входные параметры**:
- `driver` - WebDriver? - Selenium драйвер (nullable)

**Инициализация**:
1. Сохранить driver
2. Установить login = null
3. Установить password = null
4. Вывести INFO в лог

---

### Методы

#### set_parameters

**Сигнатура**:
```
set_parameters(login: String, password: String) -> void
```

**Назначение**: Установить учетные данные

**Входные параметры**:
- `login` - логин пользователя на hh.ru
- `password` - пароль пользователя

**Логика**:
1. Сохранить this.login = login
2. Сохранить this.password = password
3. Вывести INFO в лог

---

#### start

**Сигнатура**:
```
start() -> Bool
```

**Назначение**: Запустить процесс входа на сайт

**Возвращаемое значение**:
- Bool - true если вход успешен

**Логика**:
1. Вывести INFO: "Запускаем Chrome для захода на сайт"
2. Если is_logged_in() == true:
   - Вывести INFO: "Пользователь уже вошел"
   - Вернуть true
3. Иначе:
   - Вывести INFO: "Запускаем процесс входа"
   - Вернуть handle_login()

---

#### is_logged_in

**Сигнатура**:
```
is_logged_in() -> Bool
```

**Назначение**: Проверить статус авторизации

**Возвращаемое значение**:
- Bool - true если пользователь авторизован

**Исключения**:
- Обрабатывает TimeoutException внутри

**Логика**:
1. driver.get("https://www.hh.ru")
2. Вывести INFO: "Проверка входа..."
3. Ждать появления элемента (10 сек):
   - Селектор: class="supernova-logo-wrapper"
4. Если TimeoutException:
   - Вывести ERROR: "Превышен лимит ожидания"
   - Вернуть false
5. Найти элементы:
   - resume_element: [data-qa="mainmenu_myResumes"]
   - Если найдено > 0:
     - Вывести INFO: "Найдено меню резюме"
     - Вернуть true
6. Найти элементы:
   - profile_element: [data-qa="mainmenu_applicantProfile"]
   - Если найдено > 0:
     - Вывести INFO: "Найдено меню профиля"
     - Вернуть true
7. Вывести WARNING: "Не найдено меню"
8. Вернуть false

---

#### handle_login

**Сигнатура**:
```
handle_login() -> Bool
```

**Назначение**: Выполнить вход на сайт

**Возвращаемое значение**:
- Bool - true если вход успешен

**Исключения**:
- Обрабатывает NoSuchElementException

**Логика**:
1. Вывести INFO: "Заходим на сайт"
2. driver.get("https://hh.ru")
3. Попытка:
   - Вернуть enter_credentials()
4. При NoSuchElementException:
   - Вывести ERROR: "Элемент не найден"
   - Вернуть false

---

#### enter_credentials

**Сигнатура**:
```
enter_credentials() -> Bool
```

**Назначение**: Ввести логин и пароль

**Возвращаемое значение**:
- Bool - true если успешно

**Логика**:
1. Вывести INFO: "Ввод данных..."
2. driver.get("https://hh.ru/employer")
3. Найти и кликнуть: [data-qa~="login"]
4. Найти поле логина:
   - Селектор: [data-qa="login-input-username"] ИЛИ [data-qa="account-signup-email"]
5. Очистить поле (отправка BACKSPACE для каждого символа)
6. Ввести this.login
7. Найти кнопку переключения на пароль:
   - Селектор: [data-qa^="expand-login-by"]
   - Если найдено: кликнуть, пауза
8. Найти поле пароля: [data-qa="login-input-password"]
9. Ввести this.password
10. Пауза
11. Найти кнопку входа: [data-qa="account-login-submit"]
12. Кликнуть
13. Пауза 2-3 секунды
14. Вызвать process_captcha(submit_button)
15. Если НЕ check_password_is_correct():
    - Вывести ERROR: "Неверный пароль"
    - Вернуть false
16. Вернуть true

---

#### check_password_is_correct

**Сигнатура**:
```
check_password_is_correct() -> Bool
```

**Назначение**: Проверить корректность введенного пароля

**Возвращаемое значение**:
- Bool - true если пароль корректен

**Логика**:
1. Пауза
2. Найти элементы ошибки: [data-qa="account-login-error"]
3. Если найдено > 0:
   - Вернуть false
4. Вернуть true

---

#### process_captcha

**Сигнатура**:
```
process_captcha(submit_button: WebElement) -> void
```

**Назначение**: Обработать капчу если появилась

**Входные параметры**:
- `submit_button` - кнопка отправки формы

**Логика**:
1. dt_now = текущее время
2. Загрузить tg_token, tg_api_id, tg_api_hash из SECRETS_FILE
3. Найти элементы капчи: [data-qa="account-captcha-picture"]
4. Если найдено > 0:
   - Вывести INFO: "Обнаружена капча"
5. WHILE элементы капчи найдены:
   - Если (текущее_время - dt_now) > 3600 секунд:
     - Вывести ERROR: "Капча не решена за час"
     - Выйти из цикла
   - Если НЕ check_password_is_correct():
     - Выйти из цикла
   - captcha_filename = "captcha_image.png"
   - message = строка из timestamp * 10^6 (уникальный ID)
   - Если файл НЕ существует:
     - image_url = captcha_element.get_attribute("src")
     - Если url пуст: выйти из цикла
     - cookies = driver.get_cookies()
     - Создать HTTP session с cookies
     - Скачать изображение капчи
     - Сохранить в captcha_filename
     - Вызвать process_captcha(tg_token, ..., captcha_filename, message) асинхронно
   - Иначе:
     - answer = process_captcha(..., listen=True) асинхронно // ждать ответа из Telegram
     - Найти поле ввода: [data-qa="account-captcha-input"]
     - Если answer получен:
       - Вывести INFO: "Получена расшифровка"
       - Ввести answer в поле
       - Пауза
       - Кликнуть submit_button
       - Удалить captcha_filename
       - Пауза 10 секунд
   - Обновить captcha_element (проверить наличие)
6. Если капча решена или не появилась:
   - Вывести INFO: "Капча решена"

---

## 3. BotFacade

### Назначение
Фасад для координации компонентов модуля.

### Структура данных

```
BotState:
    parameters_set: Bool
    search_parameters_set: Bool
    resume_set: Bool
    gpt_answerer_set: Bool

BotFacade:
    resume_component: ResumeScraper
    search_component: SearchCustomizer
    apply_component: JobApplier
    state: BotState
    resume: Map[String]Any?
    resume_readable: String?
    parameters: Map[String]Any?
```

### Конструктор BotState

**Инициализация**:
1. Вывести INFO в лог
2. Вызвать reset()

**Метод reset**:
- Установить все флаги в false

**Метод validate_state**:

**Сигнатура**:
```
validate_state(required_keys: List[String]) -> void
```

**Исключения**:
- ValueError - если какой-то ключ не установлен

**Логика**:
1. Для каждого key в required_keys:
   - Если getattr(this, key) == false:
     - Вывести ERROR в лог
     - Выбросить ValueError

---

### Конструктор BotFacade

**Входные параметры**:
- `resume_component` - ResumeScraper
- `search_component` - SearchCustomizer
- `apply_component` - JobApplier

**Инициализация**:
1. Сохранить компоненты
2. Создать this.state = новый BotState()
3. Установить все nullable поля в null
4. Вывести INFO в лог

---

### Методы

#### set_parameters

**Сигнатура**:
```
set_parameters(parameters: Map[String]Any) -> void
```

**Назначение**: Установить параметры конфигурации

**Входные параметры**:
- `parameters` - параметры из search_config.yaml

**Исключения**:
- ValueError - если parameters пусто

**Логика**:
1. Вывести INFO в лог
2. Вызвать _validate_non_empty(parameters, "Parameters")
3. Сохранить this.parameters = parameters
4. (resume_id, resume_titles) = resume_component.get_resume_parameters()
5. Установить parameters["resume_id"] = resume_id
6. Установить parameters["resume_titles"] = resume_titles
7. Вызвать apply_component.set_parameters(parameters)
8. Установить state.parameters_set = true
9. Вывести INFO: "Параметры установлены"

---

#### set_resume

**Сигнатура**:
```
set_resume() -> void
```

**Назначение**: Собрать информацию о резюме

**Логика**:
1. Вывести INFO в лог
2. (resume_info, resume_readable) = resume_component.get_resume_info()
3. Сохранить this.resume = resume_info
4. Сохранить this.resume_readable = resume_readable
5. Вызвать search_component.set_resume(resume_component.resume_id, resume_info)
6. Вызвать apply_component.set_resume(resume_info)
7. Установить state.resume_set = true
8. Вывести INFO: "Резюме собрано"

---

#### set_search_parameters

**Сигнатура**:
```
set_search_parameters(parameters: Map[String]Any) -> void
```

**Назначение**: Задать параметры поиска

**Входные параметры**:
- `parameters` - параметры поиска

**Исключения**:
- ValueError - если parameters пусто

**Логика**:
1. Вывести INFO в лог
2. Вызвать _validate_non_empty(parameters, "Parameters")
3. Вызвать search_component.set_advanced_search_params(parameters)
4. Установить state.search_parameters_set = true
5. Вывести INFO: "Параметры поиска установлены"

---

#### set_gpt_answerer

**Сигнатура**:
```
set_gpt_answerer(gpt_answerer_component: GPTAnswerer, parameters: Map[String]Any) -> void
```

**Назначение**: Подключить LLM компонент

**Входные параметры**:
- `gpt_answerer_component` - компонент LLM
- `parameters` - параметры конфигурации

**Логика**:
1. Вывести INFO в лог
2. Вызвать _ensure_resume_set()
3. Вызвать gpt_answerer_component.set_resume(this.resume, this.resume_readable)
4. Вызвать gpt_answerer_component.set_search_parameters(parameters)
5. Вызвать apply_component.set_gpt_answerer(gpt_answerer_component)
6. Установить state.gpt_answerer_set = true
7. Вывести INFO: "LLM подключен"

---

#### start_apply

**Сигнатура**:
```
start_apply() -> void
```

**Назначение**: Запустить процесс поиска и откликов

**Логика**:
1. Вызвать state.validate_state(["resume_set", "parameters_set", "search_parameters_set", "gpt_answerer_set"])
2. Вывести INFO: "Начинаем поиск"
3. Вызвать apply_component.start_applying()
4. Вывести INFO: "Поиск завершен"

---

#### _validate_non_empty (приватный)

**Сигнатура**:
```
_validate_non_empty(value: Any, name: String) -> void
```

**Исключения**:
- ValueError - если value пусто

**Логика**:
1. Если НЕ value:
   - Вывести ERROR в лог
   - Выбросить ValueError

---

#### _ensure_resume_set (приватный)

**Сигнатура**:
```
_ensure_resume_set() -> void
```

**Исключения**:
- ValueError - если резюме не установлено

**Логика**:
1. Если НЕ state.resume_set:
   - Вывести ERROR в лог
   - Выбросить ValueError

---

## Следующие документы

- [HeadHunterAPI - детальная логика](02_api.md)
- [Authenticator - детальная логика](03_authenticator.md)
- [BotFacade - детальная логика](04_bot_facade.md)
- [JobApplier - контракты](05_job_applier_contracts.md)
- [ResumeScraper - контракты](06_resume_scraper_contracts.md)
- [SearchCustomizer - контракты](07_search_customizer_contracts.md)

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Назначение**: Спецификация интерфейсов для реализации на Go

