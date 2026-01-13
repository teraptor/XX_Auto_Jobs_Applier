# Быстрый старт - XX Auto Jobs Applier

> **⏱️ Время настройки:** 15-30 минут  
> **💡 Уровень сложности:** Начальный

---

## 📋 Чек-лист перед началом

- [ ] Python 3.12+ установлен
- [ ] Google Chrome установлен
- [ ] Есть аккаунт на hh.ru с резюме
- [ ] Есть API ключ для LLM (Google Gemini рекомендуется)
- [ ] Git установлен (для клонирования репозитория)

---

## 🚀 5 шагов до запуска

### Шаг 1: Установка проекта (5 минут)

```bash
# Клонируйте репозиторий
git clone https://github.com/beatwad/XX_Auto_Jobs_Applier.git
cd XX_Auto_Jobs_Applier

# Создайте виртуальное окружение
python -m venv virtual

# Активируйте его
# На Mac/Linux:
source virtual/bin/activate
# На Windows:
# .\virtual\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

**✅ Проверка:** Запустите `python --version` - должно быть 3.12 или выше.

---

### Шаг 2: Регистрация приложения на hh.ru (10 минут)

1. **Зайдите на:** https://dev.hh.ru/admin

2. **Заполните форму:**
   - Название: `Любое` (например, "Job Assistant")
   - Redirect URI: `https://localhost`
   - Для кого: `Только соискатели`

3. **В поле "Какие задачи должно решать":**
   ```
   - Рекомендации по улучшению резюме
   - Помощь в создании сопроводительных писем
   - Подбор релевантных вакансий
   ```

4. **Ждите одобрения** (обычно 1-3 дня)

5. **После одобрения:**
   - Получите `Client ID` и `Client Secret`
   - Скопируйте их - понадобятся на следующем шаге

**💡 Подсказка:** Подробная инструкция в главном [README.md](../README.md#получение-токенов-для-доступа-к-api-hhru)

---

### Шаг 3: Получение токенов (5 минут)

**Вариант A: Jupyter Notebook (рекомендуется)**

```bash
# Установите Jupyter (если еще не установлен)
pip install jupyter

# Откройте ноутбук
jupyter notebook notebooks/get_tokens.ipynb

# Следуйте инструкциям в ноутбуке
```

**Вариант B: Вручную**

1. Создайте ссылку авторизации:
```python
client_id = "ваш_client_id"
redirect_uri = "https://localhost"

url = f"https://hh.ru/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
print(url)
```

2. Перейдите по ссылке, одобрите доступ

3. Из адресной строки скопируйте `code=...`

4. Получите токены:
```python
import requests

response = requests.post("https://api.hh.ru/token", data={
    'grant_type': 'authorization_code',
    'client_id': "ваш_client_id",
    'client_secret': "ваш_client_secret",
    'code': "ваш_auth_code",
    'redirect_uri': "https://localhost"
})

tokens = response.json()
print(f"Access token: {tokens['access_token']}")
print(f"Refresh token: {tokens['refresh_token']}")
```

**📝 Сохраните:** `access_token` и `refresh_token`

---

### Шаг 4: Настройка конфигурации (5 минут)

#### 4.1. Скопируйте примеры

```bash
# Создайте файлы конфигурации
cp data_folder_example/secrets/secrets.yaml data_folder/secrets/
cp data_folder_example/search_config/search_config.yaml data_folder/search_config/
```

#### 4.2. Отредактируйте secrets.yaml

Откройте `data_folder/secrets/secrets.yaml` и заполните:

```yaml
# ✅ ОБЯЗАТЕЛЬНЫЕ ПОЛЯ:
access_token: YOUR_ACCESS_TOKEN_HERE          # Из шага 3
refresh_token: YOUR_REFRESH_TOKEN_HERE        # Из шага 3

hh_login: your_email@example.com              # Логин на hh.ru
hh_password: your_password                    # Пароль на hh.ru

llm_api_key: YOUR_GEMINI_API_KEY              # Получить: https://ai.google.dev/

# ⚙️ ОПЦИОНАЛЬНЫЕ ПОЛЯ:
llm_proxy: []                                 # Оставьте пустым если не нужен прокси

tg_token: ""                                  # Telegram бот (опционально)
tg_api_id: ""                                 # Для капчи (опционально)
tg_api_hash: ""                               # Для капчи (опционально)
```

**🔑 Где взять Gemini API ключ:**
1. Перейдите: https://ai.google.dev/
2. Нажмите "Get API key"
3. Создайте или выберите проект
4. Скопируйте ключ

#### 4.3. Отредактируйте search_config.yaml

Откройте `data_folder/search_config/search_config.yaml` и измените:

```yaml
# ✅ ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ:
job_title: "Ваша должность"                   # ТОЧНО как в резюме на hh.ru!
user_id: "YOUR_HH_USER_ID"                    # Из URL резюме на hh.ru

# ⚙️ НАСТРОЙТЕ ПОД СЕБЯ:
keywords: "Python, Django, API"               # Ключевые слова
salary: 100000                                # Минимальная зарплата (в рублях)
area: "Москва"                                # Город/регион

# Опыт (ТОЛЬКО ОДНО значение true!):
experience:
  doesntMatter: false
  noExperience: false
  between1And3: false
  between3And6: true                          # Пример: 3-6 лет
  moreThan6: false

# График (можно несколько true):
schedule:
  fullDay: true
  shift: false
  flexible: true
  remote: true                                # Удаленка
  flyInFlyOut: false

# Лимиты:
max_applies_num: 50                           # Начните с малого для теста
apply_once_at_company: true                   # Только 1 отклик на компанию

# Черный список компаний (через запятую):
job_blacklist: ""                             # Оставьте пустым или добавьте: Google, Meta

# Сопроводительное письмо (если хотите одно для всех):
cover_letter: ""                              # Пустое = AI будет генерировать
```

**❓ Где найти user_id:**
- Зайдите на hh.ru → Мои резюме
- URL будет вида: `https://hh.ru/applicant/resumes/view?resume=12345678`
- `12345678` - это ваш user_id

---

### Шаг 5: Первый запуск! (2 минуты)

```bash
# Убедитесь что виртуальное окружение активно
# (должно быть (virtual) в начале строки терминала)

# Запустите приложение
python main.py
```

**Что произойдет:**

1. **При первом запуске:**
   - Откроется браузер Chrome
   - Нужно будет ввести логин/пароль от hh.ru
   - Возможно, потребуется пройти капчу
   - Сессия сохранится - следующий раз авторизация не нужна

2. **Процесс работы:**
   ```
   [INFO] Начало работы...
   [INFO] Получение данных резюме...
   [INFO] Настройка параметров поиска...
   [INFO] Найдено вакансий: 123
   [INFO] Обработка вакансии 1/123...
   [INFO] Вакансия оценена: 85/100
   [INFO] Генерация сопроводительного письма...
   [INFO] Отклик отправлен успешно!
   ...
   ```

3. **По окончании:**
   - Статистика в терминале
   - Результаты в `data_folder/output/`

**🛑 Остановка:** Нажмите `Ctrl + C`

---

## 📊 Проверка результатов

После запуска проверьте файлы в `data_folder/output/`:

### success.yaml - Успешные отклики
```yaml
- vacancy_url: https://hh.ru/vacancy/123456
  company: "ООО Рога и Копыта"
  position: "Python разработчик"
  timestamp: "2025-10-22 14:30:00"
```

### skipped.yaml - Пропущенные вакансии
```yaml
- vacancy_url: https://hh.ru/vacancy/789012
  reason: "Низкая оценка соответствия (45/100)"
  timestamp: "2025-10-22 14:31:00"
```

### cover_letters.txt - Сопроводительные письма
```
=== Вакансия: Python разработчик ===
Здравствуйте!

С большим интересом ознакомился с вакансией Python разработчика...
...
```

### llm_api_calls.yaml - Запросы к AI (+ стоимость)
```yaml
- timestamp: "2025-10-22 14:30:15"
  input_tokens: 1234
  output_tokens: 56
  cost_usd: 0.000234
```

---

## ⚙️ Тонкая настройка

После первого запуска можете настроить поведение в `src/app_config.py`:

```python
# Режимы работы
MONKEY_MODE = False          # True = откликаться на ВСЁ подряд

# Порог "интересности" (1-100)
JOB_IS_INTERESTING_THRESH = 70   # Только ≥ 70 баллов

# Поднимать резюме при запуске (раз в 4 часа)
RAISE_RESUME = True

# Минимальное время на один отклик (сек)
MINIMUM_WAIT_TIME_SEC = 10

# Выбор AI модели
LLM_MODEL_TYPE = "gemini"         # openai, gemini, claude
LLM_MODEL = "gemini-2.0-flash"    # Конкретная модель

# "Креативность" AI (0 = строгий, 1.5 = креативный)
TEMPERATURE = 0.4
```

---

## 🔧 Решение проблем

### ❌ "ModuleNotFoundError"
**Решение:**
```bash
pip install -r requirements.txt --force-reinstall
```

### ❌ "Ошибка конфигурации: Отсутствует ключ..."
**Решение:**
- Проверьте `secrets.yaml` и `search_config.yaml`
- Убедитесь что все обязательные поля заполнены
- Проверьте правильность отступов в YAML (используйте пробелы, не табы!)

### ❌ "Error code: 401" (hh.ru API)
**Решение:**
- Токены истекли - повторите Шаг 3
- Проверьте `access_token` и `refresh_token` в `secrets.yaml`

### ❌ "Error code: 403" (OpenAI/Gemini)
**Решение:**
- Для OpenAI: включите VPN (европейская страна/США)
- Проверьте баланс API ключа
- Убедитесь что `llm_api_key` правильный

### ❌ Selenium ошибки
**Решение:**
- Закройте все окна Chrome
- Удалите папку `chrome_profile/`
- Обновите Chrome до последней версии

### ❌ Капча при входе
**Решение:**
1. Решите капчу вручную при первом входе
2. Настройте Telegram бот для автоматического уведомления
3. Используйте режим с меньшим количеством откликов

---

## 💡 Полезные советы

### Для экономии средств на LLM
1. ✅ Используйте `gemini-2.0-flash` (самый дешевый)
2. ✅ Заполните `cover_letter` в search_config (одно письмо для всех)
3. ✅ Не удаляйте `answers.yaml` (кэш ответов)
4. ✅ Начните с малого `max_applies_num: 20`

### Для лучших результатов
1. ✅ Детально заполните резюме на hh.ru
2. ✅ Точно укажите желаемую должность в `job_title`
3. ✅ Настройте фильтры в `search_config.yaml`
4. ✅ Проверяйте `cover_letters.txt` и корректируйте промпты при необходимости
5. ✅ Используйте `COVER_LETTER_MODE = True` для предварительной проверки писем

### Для безопасности
1. ✅ Исключите `secrets.yaml` из Git:
   ```bash
   git update-index --assume-unchanged data_folder/secrets/secrets.yaml
   ```
2. ✅ Не делитесь содержимым `data_folder/`
3. ✅ Регулярно меняйте пароли

### Для мониторинга
1. ✅ Настройте Telegram бот для уведомлений об ошибках
2. ✅ Проверяйте логи в `logs/`
3. ✅ Анализируйте `llm_api_calls.yaml` для контроля расходов

---

## 🎯 Типичные сценарии использования

### Сценарий 1: Максимальная экономия
```yaml
# search_config.yaml
max_applies_num: 20
cover_letter: "Здравствуйте! ..." # Готовое письмо
```
```python
# app_config.py
MONKEY_MODE = True              # Без AI фильтрации
LLM_MODEL = "gemini-2.0-flash"  # Самая дешевая модель
```

### Сценарий 2: Максимальное качество
```yaml
# search_config.yaml
max_applies_num: 100
cover_letter: ""                # AI генерирует под каждую
```
```python
# app_config.py
MONKEY_MODE = False
JOB_IS_INTERESTING_THRESH = 80  # Только топовые вакансии
LLM_MODEL = "gpt-4o"            # Лучшее качество
TEMPERATURE = 0.6               # Более креативные ответы
```

### Сценарий 3: Предварительная проверка
```python
# app_config.py
COVER_LETTER_MODE = True        # Только генерация писем
```
Запустите, проверьте `cover_letters.txt`, при необходимости скорректируйте промпты.

### Сценарий 4: Генерация резюме
```python
# app_config.py
RESUME_MODE = True              # Генерация HTML/PDF резюме
```
Результаты в `data_folder/generated_cv/`

---

## 📚 Что дальше?

### Изучите документацию
- 📖 [README.md](../README.md) - подробная инструкция
- 📂 [data_folders_guide.md](data_folders_guide.md) - про конфигурацию
- 🏗️ [architecture.md](architecture.md) - архитектура (для разработчиков)

### Оптимизируйте работу
1. Анализируйте результаты в `output/`
2. Корректируйте фильтры в `search_config.yaml`
3. Настраивайте промпты в `src/llm/prompts.py`
4. Регулируйте порог `JOB_IS_INTERESTING_THRESH`

### Присоединяйтесь к сообществу
- 💬 [Telegram чат](https://t.me/xx_auto_job)
- 🐛 [GitHub Issues](https://github.com/beatwad/XX_Auto_Jobs_Applier/issues)

---

## ✅ Финальный чек-лист

Перед регулярным использованием убедитесь:

- [ ] Приложение успешно запускается
- [ ] Отклики отправляются (проверьте на hh.ru)
- [ ] Сопроводительные письма читабельные (см. `cover_letters.txt`)
- [ ] Расходы на LLM в рамках бюджета (см. `llm_api_calls.yaml`)
- [ ] `secrets.yaml` исключен из Git
- [ ] Резервная копия токенов сохранена в безопасном месте

---

<div align="center">

## 🎉 Готово! Удачи в поиске работы! 🚀

**Вопросы? → [Telegram чат](https://t.me/xx_auto_job)**

**[⬆ Наверх](#быстрый-старт---xx-auto-jobs-applier)**

</div>

---

**Версия:** 1.0  
**Обновлено:** 22 октября 2025  
**Автор:** beatwad

