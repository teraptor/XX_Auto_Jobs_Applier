# Пагинация при поиске вакансий на hh.ru

## 📋 Оглавление

1. [Введение](#введение)
2. [Архитектура пагинации](#архитектура-пагинации)
3. [Параметры пагинации](#параметры-пагинации)
4. [Двухэтапная стратегия поиска](#двухэтапная-стратегия-поиска)
5. [Алгоритм пагинации](#алгоритм-пагинации)
6. [Управление состоянием](#управление-состоянием)
7. [Обработка ошибок](#обработка-ошибок)
8. [Оптимизация и улучшения](#оптимизация-и-улучшения)
9. [Примеры использования](#примеры-использования)

---

## Введение

Система автоматического поиска вакансий использует **постраничную загрузку** (пагинацию) для обработки больших объемов вакансий. API hh.ru возвращает результаты порциями, что требует последовательной обработки страниц.

### Ключевые характеристики:

- ✅ **Постраничная обработка** - вакансии обрабатываются блоками по 10 шт.
- ✅ **Двухэтапный поиск** - сначала похожие на резюме, потом общий поиск
- ✅ **Автоматическое продолжение** - переход на следующую страницу
- ✅ **Контроль лимитов** - остановка при достижении максимума откликов
- ⚠️ **Фиксированный размер страницы** - `per_page = 10` (захардкожено)

---

## Архитектура пагинации

```
┌─────────────────────────────────────────────────────────────────┐
│                    Инициализация поиска                         │
│                   page_num = 0                                  │
│                   resume_vac_page_num = -1                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              ЭТАП 1: Похожие на резюме вакансии                 │
│   API: /resumes/{resume_id}/similar_vacancies                   │
│                                                                  │
│   while resume_vac_page_num == -1:                              │
│     ├─ Запрос страницы page_num                                 │
│     ├─ Обработка 10 вакансий                                    │
│     ├─ page_num++                                               │
│     └─ Если items пустой → resume_vac_page_num = page_num      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              ЭТАП 2: Общий поиск вакансий                       │
│   API: /vacancies                                               │
│                                                                  │
│   while не достигнут лимит:                                     │
│     ├─ adjusted_page = page_num - resume_vac_page_num           │
│     ├─ Запрос страницы adjusted_page                            │
│     ├─ Обработка 10 вакансий                                    │
│     ├─ page_num++                                               │
│     └─ Если items пустой → СТОП                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    Завершение поиска
```

---

## Параметры пагинации

### Основные параметры

**Файл:** `src/job_manager/job_applier.py`

```python
# Строка 121
search_params = {"page": page_num, "per_page": 10}
```

| Параметр | Тип | Значение | Описание |
|----------|-----|----------|----------|
| `page` | int | `0, 1, 2, ...` | Номер страницы (индексация с 0) |
| `per_page` | int | `10` | Количество вакансий на странице |

### Переменные состояния

**Инициализация в `__init__` (строка 55-56):**

```python
self.page_num = 0                  # Текущая страница (общий счетчик)
self.resume_vac_page_num = -1      # Страниц с похожими вакансиями (-1 = не определено)
```

| Переменная | Начальное значение | Назначение |
|------------|-------------------|------------|
| `page_num` | `0` | Глобальный счетчик страниц |
| `resume_vac_page_num` | `-1` | Количество страниц с похожими вакансиями |
| `applies_num` | `0` | Общее количество обработанных вакансий |
| `success_applies_num` | `0` | Количество успешных откликов |

### Контрольные значения

```python
# Строка 243
while self.success_applies_num < self.max_applies_num and self.applies_num < 400:
```

| Лимит | Значение | Источник | Описание |
|-------|----------|----------|----------|
| `max_applies_num` | 200 (по умолчанию) | `search_config.yaml` | Максимум откликов за запуск |
| `applies_num` | < 400 | Захардкожено | Защита от бесконечного цикла |
| `max_total_applies_num` | 1500 (опционально) | `search_config.yaml` | Общий лимит за все запуски |

---

## Двухэтапная стратегия поиска

### Зачем два этапа?

1. **Этап 1** - приоритет вакансиям, которые hh.ru сам считает похожими на резюме
2. **Этап 2** - расширение поиска вакансиями по заданным параметрам

### Этап 1: Похожие на резюме вакансии

**Файл:** `src/job_manager/job_applier.py`, строки 127-136

```python
# Сначала ищем вакансии, похожие на данное резюме
if self.resume_vac_page_num == -1:
    resume_vacancies = self.api.api_request(
        f"https://api.hh.ru/resumes/{self.resume_id}/similar_vacancies",
        params=search_params,
    )
    # Если не нашли - записываем общее количество страниц
    if len(resume_vacancies["items"]) == 0:
        self.resume_vac_page_num = page_num  # Фиксируем момент окончания
    else:
        vacancies = resume_vacancies["items"]
```

**Характеристики:**

- 🎯 **API Endpoint:** `/resumes/{resume_id}/similar_vacancies`
- 📊 **Алгоритм hh.ru:** Автоматическое сопоставление с резюме
- 🔄 **Условие выполнения:** `resume_vac_page_num == -1`
- ⏹️ **Условие остановки:** `items` пустой → переход к этапу 2

**Схема работы:**

```
page_num = 0, resume_vac_page_num = -1
  ↓
Запрос: /similar_vacancies?page=0&per_page=10
  ↓
Получили 10 вакансий → Обработка
  ↓
page_num = 1, resume_vac_page_num = -1
  ↓
Запрос: /similar_vacancies?page=1&per_page=10
  ↓
Получили 10 вакансий → Обработка
  ↓
page_num = 2, resume_vac_page_num = -1
  ↓
Запрос: /similar_vacancies?page=2&per_page=10
  ↓
Получили 0 вакансий → resume_vac_page_num = 2 (ПЕРЕХОД К ЭТАПУ 2)
```

### Этап 2: Общий поиск

**Файл:** `src/job_manager/job_applier.py`, строки 139-148

```python
# Обращаемся сюда только после обработки всех похожих вакансий
if page_num == 0 or self.resume_vac_page_num > -1:
    search_params_ = search_params.copy()
    # Корректируем номер страницы!
    search_params_["page"] = page_num - max(self.resume_vac_page_num, 0)
    search_params_["text"] = self.job_title
    main_vacancies = self.api.api_request(
        "https://api.hh.ru/vacancies",
        params=search_params_,
    )
    if self.resume_vac_page_num > -1:
        vacancies = main_vacancies["items"]
```

**Ключевая особенность: Корректировка номера страницы**

```python
adjusted_page = page_num - max(self.resume_vac_page_num, 0)
```

**Пример:**
```
resume_vac_page_num = 2  (закончились на странице 2)
page_num = 2             (глобальный счетчик)

adjusted_page = 2 - 2 = 0  ← Начинаем с 0 для общего поиска!

page_num = 3
adjusted_page = 3 - 2 = 1  ← Запрашиваем страницу 1
```

**Характеристики:**

- 🎯 **API Endpoint:** `/vacancies`
- 📊 **Параметры:** Все фильтры из `search_config.yaml` + `text = job_title`
- 🔄 **Условие выполнения:** `resume_vac_page_num > -1` ИЛИ `page_num == 0`
- ⏹️ **Условие остановки:** `items` пустой ИЛИ лимиты достигнуты

---

## Алгоритм пагинации

### Основной цикл обработки

**Файл:** `src/job_manager/job_applier.py`, строки 227-277

```python
def start_applying(self) -> None:
    """Разослать отклики всем работодателям на всех страницах"""
    
    # Инициализация
    result = ""
    
    # Главный цикл пагинации
    while self.success_applies_num < self.max_applies_num and self.applies_num < 400:
        # 1. Получить вакансии с текущей страницы
        vacancies = self.search_vacancies(self.page_num)
        
        # 2. Проверка на окончание результатов
        if len(vacancies) == 0:
            if self.page_num == 1:
                logger.warning("По данному поисковому запросу не найдено ни одной вакансии")
            break  # Больше нет вакансий
        
        # 3. Обработка каждой вакансии на странице
        for vacancy in vacancies:
            url = vacancy.get("alternate_url")
            try:
                result = self.send_repsonse(vacancy)
                if result == "Limit":
                    logger.warning("Достигнуто максимально допустимое число откликов")
                    break
            except Exception:
                tb_str = traceback.format_exc()
                logger.error(f"Неизвестная ошибка на странице: {url}\n{tb_str}")
                self.error_num += 1
                if self.error_num == MAX_APPLIES_NUM:
                    result = "Error"
                    break
                continue
            else:
                self.error_num = 0
        
        # 4. Проверка условий остановки
        if result == "Limit" or result == "Error":
            break
        
        # 5. Переход на следующую страницу
        self.page_num += 1
        logger.info(f"Переходим на страницу {self.page_num}")
    
    logger.info(f"Откликов отправлено: {self.success_applies_num}")
```

### Метод `search_vacancies`

**Файл:** `src/job_manager/job_applier.py`, строки 119-153

```python
def search_vacancies(self, page_num: int = 0) -> List[Any]:
    """Начать поиск"""
    
    # 1. Подготовка базовых параметров
    search_params = {"page": page_num, "per_page": 10}
    vacancies = []
    
    # 2. Добавление фильтров
    for key, value in self.search_component.search_params.items():
        if value:
            search_params[key] = value
    
    # 3. ЭТАП 1: Похожие на резюме вакансии
    if self.resume_vac_page_num == -1:
        resume_vacancies = self.api.api_request(
            f"https://api.hh.ru/resumes/{self.resume_id}/similar_vacancies",
            params=search_params,
        )
        if len(resume_vacancies["items"]) == 0:
            self.resume_vac_page_num = page_num  # Фиксируем окончание
        else:
            vacancies = resume_vacancies["items"]
    
    # 4. ЭТАП 2: Общий поиск (параллельно на первой странице)
    if page_num == 0 or self.resume_vac_page_num > -1:
        search_params_ = search_params.copy()
        search_params_["page"] = page_num - max(self.resume_vac_page_num, 0)
        search_params_["text"] = self.job_title
        main_vacancies = self.api.api_request(
            "https://api.hh.ru/vacancies",
            params=search_params_,
        )
        if self.resume_vac_page_num > -1:
            vacancies = main_vacancies["items"]
    
    # 5. Логирование на первой странице
    if page_num == 0 and self.resume_vac_page_num == -1:
        total_found = resume_vacancies["found"] + main_vacancies["found"]
        logger.info(f"Найдено {total_found} вакансий")
    
    return vacancies
```

### Диаграмма состояний

```
┌──────────────┐
│   START      │
│  page=0      │
│  resume=-1   │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────┐
│  Запрос /similar_vacancies       │◄──────┐
│  page = current_page             │       │
└──────┬───────────────────────────┘       │
       │                                   │
       ▼                                   │
   items > 0?                              │
   ┌───┴───┐                               │
   │       │                               │
  Да      Нет                              │
   │       │                               │
   │       ▼                               │
   │  resume_vac_page_num = current_page  │
   │       │                               │
   ▼       ▼                               │
Обработка                                  │
вакансий                                   │
   │                                       │
   ▼                                       │
page_num++────────────────────────────────┘
   │
   │ resume_vac_page_num > -1?
   │
   ▼
┌──────────────────────────────────┐
│  Запрос /vacancies               │◄──────┐
│  adjusted = page - resume_page   │       │
└──────┬───────────────────────────┘       │
       │                                   │
       ▼                                   │
   items > 0?                              │
   ┌───┴───┐                               │
   │       │                               │
  Да      Нет                              │
   │       │                               │
   ▼       ▼                               │
Обработка STOP                             │
вакансий                                   │
   │                                       │
   ▼                                       │
page_num++────────────────────────────────┘
   │
   ▼
Проверка лимитов
   │
   ▼
Лимит достигнут? ──Да──> STOP
   │
  Нет
   │
   └─> Продолжить цикл
```

---

## Управление состоянием

### Переменные состояния

```python
# Инициализация (строки 55-59)
self.page_num = 0                   # Глобальная страница
self.resume_vac_page_num = -1       # Страниц похожих вакансий
self.error_num = 0                  # Счетчик последовательных ошибок
self.total_applies_num = 0          # Общее количество откликов
self.applies_num = 0                # Откликов в текущем сеансе
self.success_applies_num = 0        # Успешных откликов
```

### Кэширование состояния

**Файл:** `src/job_manager/job_applier.py`, строки 587-595

```python
def _load_cache(self) -> Dict[str, str]:
    """Загружаем кэш из файла"""
    try:
        with open(LAST_RUN_FILE, "r") as f:
            cache = yaml.safe_load(f) or {}
            return cache
    except Exception:
        logger.warning("Не удалось загрузить кэш из локального файла")
        return {}
```

**Содержимое кэша (`last_run.yaml`):**

```yaml
last_run: "2024-11-06T15:30:00"      # Время последнего запуска
last_apply: "2024-11-06T15:45:23"    # Время последнего отклика
success_applies_num: 87              # Количество успешных откликов
total_applies_num: 1234              # Общее количество откликов за все время
```

### Сохранение состояния

**Файл:** `src/job_manager/job_applier.py`, строки 632-642

```python
def _write_the_last_search_time(self) -> None:
    """Записываем время последнего поиска работы"""
    save_yaml_file(LAST_RUN_FILE, self.cache)
    cache_path = self._define_output_file("last_run.yaml")
    try:
        save_yaml_file(cache_path, self.cache)
    except Exception:
        tb_str = traceback.format_exc()
        logger.error(f"Ошибка при сохранении информации о последнем поиске\n{tb_str}")
```

**Обновление кэша (строки 362-365):**

```python
if result == "Success":
    self.success_applies_num += 1
    self.total_applies_num += 1
    self.cache["success_applies_num"] = self.success_applies_num
    self.cache["total_applies_num"] = self.total_applies_num
    self.cache["last_apply"] = datetime.now().isoformat()
    self._write_the_last_search_time()  # Сохраняем после каждого успешного отклика
```

### Восстановление после сбоя

**Файл:** `src/job_manager/job_applier.py`, строки 615-630

```python
def _check_the_previous_apply_number(self) -> bool:
    """
    Проверяем, были ли отклики без завершенного поиска.
    Если да, то возвращаем их количество
    """
    logger.info("Проверяем время последнего отклика")
    if self.cache.get("last_apply"):
        last_apply = datetime.fromisoformat(self.cache["last_apply"])
    else:
        return 0
    
    # Если предыдущий поиск не был завершен, а значит с момента последнего 
    # отклика прошло меньше часа, то мы считаем начиная с предыдущего количества откликов
    if (datetime.now() - last_apply).total_seconds() < 59 * 60:
        prev_apply_num = self.cache.get("success_applies_num", 0)
        return prev_apply_num
    return 0
```

**Логика восстановления:**

```
last_apply = "2024-11-06 15:45:00"
now = "2024-11-06 16:20:00"
delta = 35 минут

delta < 59 минут?  ✅ ДА
  ↓
Продолжаем с success_applies_num из кэша
previous_apply_number = 87

max_applies_num = 200
Нужно еще откликнуться: 200 - 87 = 113 вакансий
```

⚠️ **Проблема:** Не сохраняется `page_num`, поиск начинается с начала!

---

## Обработка ошибок

### Типы ошибок

#### 1. Пустая страница (нет результатов)

```python
# Строки 246-249
if len(vacancies) == 0:
    if self.page_num == 1:
        logger.warning("По данному поисковому запросу не найдено ни одной вакансии")
    break  # Выход из цикла пагинации
```

#### 2. Лимиты API hh.ru

**Файл:** `src/job_manager/api.py`, строки 34-40

```python
if error.get("type") == "too_many_requests":
    logger.warning("Слишком много запросов, ждем 1-2 часа")
    pause(3600, 7200)  # Пауза на 1-2 часа!
    # Повторяем запрос
    response = self._send_request(url, type_, params)
    break
```

#### 3. Ошибка при обработке вакансии

```python
# Строки 257-270
try:
    result = self.send_repsonse(vacancy)
except Exception:
    tb_str = traceback.format_exc()
    logger.error(f"Неизвестная ошибка на странице: {url}\n{tb_str}")
    
    # Защита от бесконечного цикла ошибок
    if self.error_num == MAX_APPLIES_NUM:
        logger.error(f"Критическое количество идущих подряд ошибок {MAX_APPLIES_NUM}")
        result = "Error"
        break
    else:
        self.error_num += 1
    continue
else:
    self.error_num = 0  # Сброс счетчика при успехе
```

#### 4. Достижение лимита откликов

```python
# Строки 380-391
stop_reason = ""
if self.success_applies_num >= self.max_applies_num:
    stop_reason = f"Достигнуто максимально допустимое число откликов за запуск: {self.success_applies_num}/{self.max_applies_num}"
elif (
    self.max_total_applies_num is not None
    and self.total_applies_num >= self.max_total_applies_num
):
    stop_reason = f"Достигнут общий лимит откликов: {self.total_applies_num}/{self.max_total_applies_num}"

if stop_reason:
    logger.info(stop_reason)
    return "Limit"
```

### Стратегии обработки

| Ошибка | Действие | Продолжение? |
|--------|----------|--------------|
| Пустая страница | Логирование + break | ❌ Нет |
| `too_many_requests` | Пауза 1-2 часа + retry | ✅ Да |
| Ошибка обработки вакансии | Счетчик + continue | ✅ Да (до 100 раз) |
| Лимит откликов | Логирование + return "Limit" | ❌ Нет |
| Критические ошибки (100 подряд) | return "Error" | ❌ Нет |

---

## Оптимизация и улучшения

### Текущие проблемы

#### 1. **Фиксированный размер страницы**

**Проблема:**
```python
"per_page": 10  # Захардкожено, нельзя изменить
```

**Влияние:**
- Для 200 вакансий = 20 API запросов
- Для 1000 вакансий = 100 API запросов
- Дополнительная задержка между запросами

**Решение:**
```yaml
# search_config.yaml
pagination:
  per_page: 50  # Увеличить до максимального разрешенного API
```

```python
# job_applier.py
def search_vacancies(self, page_num: int = 0) -> List[Any]:
    per_page = self.search_component.search_params.get("per_page", 10)
    search_params = {"page": page_num, "per_page": per_page}
```

**Выгода:** Уменьшение запросов в 5 раз (10 → 50)

#### 2. **Отсутствие checkpoint для страниц**

**Проблема:**
```python
# При восстановлении после сбоя
page_num = 0  # Всегда начинаем с начала!
```

**Влияние:**
- Повторная обработка уже просмотренных вакансий
- Лишние API запросы
- Потеря прогресса

**Решение:**
```python
# Сохранение в кэш
self.cache["page_num"] = self.page_num
self.cache["resume_vac_page_num"] = self.resume_vac_page_num

# Восстановление
self.page_num = self.cache.get("page_num", 0)
self.resume_vac_page_num = self.cache.get("resume_vac_page_num", -1)
```

#### 3. **Нет дедупликации между этапами**

**Проблема:**
```python
# Одна вакансия может попасть в оба этапа
similar_vacancies = [...vacancy_123...]
main_vacancies = [...vacancy_123...]  # Та же самая!
```

**Влияние:**
- Дублирование обработки
- Двойные отклики (защита есть, но это расход ресурсов)

**Решение:**
```python
def search_vacancies(self, page_num: int = 0) -> List[Any]:
    seen_ids = set()
    vacancies = []
    
    # Этап 1
    if self.resume_vac_page_num == -1:
        resume_vacancies = self.api.api_request(...)
        for v in resume_vacancies["items"]:
            if v["id"] not in seen_ids:
                vacancies.append(v)
                seen_ids.add(v["id"])
    
    # Этап 2
    if page_num == 0 or self.resume_vac_page_num > -1:
        main_vacancies = self.api.api_request(...)
        for v in main_vacancies["items"]:
            if v["id"] not in seen_ids:
                vacancies.append(v)
                seen_ids.add(v["id"])
    
    return vacancies
```

#### 4. **Двойные API запросы на первой странице**

**Проблема:**
```python
# Строки 139
if page_num == 0 or self.resume_vac_page_num > -1:
    # На странице 0 запрашиваем ОБА endpoint'а одновременно!
```

**Влияние:**
- На первой странице = 2 API запроса вместо 1
- Нарушение логики последовательности

**Решение:**
```python
if page_num == 0:
    # Только similar_vacancies
    pass
elif self.resume_vac_page_num > -1:
    # Только vacancies
    pass
```

#### 5. **Жесткий лимит 400 обработок**

**Проблема:**
```python
# Строка 243
while ... and self.applies_num < 400:
    # Почему именно 400?
```

**Влияние:**
- Искусственное ограничение
- Непонятная логика

**Решение:**
```yaml
# search_config.yaml
max_processed_vacancies: 500  # Или убрать совсем
```

### Рекомендуемые улучшения

#### **Приоритет 1: Критические**

1. **Увеличить `per_page` до 50-100**
   ```python
   search_params = {"page": page_num, "per_page": 50}
   ```
   Экономия: **80% API запросов**

2. **Добавить checkpoint для страниц**
   ```python
   cache["page_num"] = page_num
   cache["resume_vac_page_num"] = resume_vac_page_num
   ```
   Выгода: **Восстановление с места остановки**

3. **Дедупликация по vacancy_id**
   ```python
   if vacancy["id"] in seen_ids:
       continue
   ```
   Выгода: **Нет повторной обработки**

#### **Приоритет 2: Важные**

4. **Убрать двойной запрос на page=0**
   ```python
   if page_num == 0 and self.resume_vac_page_num == -1:
       # Только similar_vacancies
   ```
   Экономия: **1 API запрос на старте**

5. **Progress bar с ETA**
   ```python
   progress = (page_num * per_page) / estimated_total * 100
   eta = (estimated_total - processed) * avg_time_per_vacancy
   logger.info(f"Progress: {progress:.1f}% | ETA: {eta//60} min")
   ```
   Выгода: **UX и контроль**

6. **Параметр для max_processed**
   ```yaml
   max_processed_vacancies: 1000  # Вместо захардкоженного 400
   ```

#### **Приоритет 3: Оптимизации**

7. **Динамическое изменение per_page**
   ```python
   # Начинаем с 10, потом увеличиваем
   if page_num < 3:
       per_page = 10
   else:
       per_page = 50
   ```

8. **Предзагрузка следующей страницы**
   ```python
   # Асинхронная загрузка page+1 пока обрабатываем page
   future = async_load_page(page_num + 1)
   ```

9. **Кэш метаданных страниц**
   ```python
   page_cache[page_num] = {
       "vacancy_ids": [...],
       "timestamp": "...",
       "has_next": True
   }
   ```

---

## Примеры использования

### Пример 1: Стандартный поиск

```python
# Конфигурация
max_applies_num: 50
per_page: 10  # 10 вакансий на странице

# Выполнение
page 0: similar_vacancies → 10 вакансий → 3 отклика
page 1: similar_vacancies → 10 вакансий → 5 откликов
page 2: similar_vacancies → 10 вакансий → 4 отклика
page 3: similar_vacancies → 0 вакансий → resume_vac_page_num = 3

page 3: vacancies (adjusted=0) → 10 вакансий → 6 откликов
page 4: vacancies (adjusted=1) → 10 вакансий → 5 откликов
...
page 10: vacancies (adjusted=7) → 10 вакансий → 4 отклика

ИТОГО: 50 откликов из ~110 вакансий (7 страниц)
API запросов: 11
```

### Пример 2: Быстрое исчерпание similar_vacancies

```python
# Конфигурация
max_applies_num: 100
per_page: 10

# Выполнение
page 0: similar_vacancies → 10 вакансий → 4 отклика
page 1: similar_vacancies → 0 вакансий → resume_vac_page_num = 1

page 1: vacancies (adjusted=0) → 10 вакансий → 5 откликов
page 2: vacancies (adjusted=1) → 10 вакансий → 6 откликов
...
page 15: vacancies (adjusted=14) → 10 вакансий → 5 откликов

ИТОГО: 100 откликов из ~150 вакансий (15 страниц)
API запросов: 16
```

### Пример 3: Восстановление после сбоя

```python
# Первый запуск
page 0-5: Обработано 60 вакансий, 30 откликов
СБОЙ на странице 5

# Кэш сохранен:
cache = {
    "success_applies_num": 30,
    "last_apply": "2024-11-06T15:45:00"
}

# Повторный запуск (через 20 минут)
page_num восстанавливается = 0  ⚠️ ПРОБЛЕМА!
success_applies_num = 30  ✅ Восстановлен

# Продолжение
page 0: ПОВТОРНАЯ обработка тех же вакансий
page 1: ПОВТОРНАЯ обработка тех же вакансий
...
Дубликаты пропускаются, но API запросы расходуются!
```

### Пример 4: Лимит на странице

```python
# Конфигурация
max_applies_num: 20
per_page: 10

# Выполнение
page 0: similar_vacancies → 10 вакансий
  vacancy 1-5: 5 откликов (total: 5)
  vacancy 6-10: 5 откликов (total: 10)

page 1: similar_vacancies → 10 вакансий
  vacancy 1-5: 5 откликов (total: 15)
  vacancy 6: 1 отклик (total: 16)
  vacancy 7: 1 отклик (total: 17)
  vacancy 8: 1 отклик (total: 18)
  vacancy 9: 1 отклик (total: 19)
  vacancy 10: 1 отклик (total: 20) → LIMIT!

СТОП: Достигнут лимит 20 откликов
API запросов: 2
```

---

## Диагностика проблем

### Проблема: "Слишком мало вакансий"

**Симптомы:**
```
INFO - Найдено 50 вакансий
INFO - Переходим на страницу 1
INFO - Переходим на страницу 2
WARNING - По данному поисковому запросу не найдено ни одной вакансии
```

**Причины:**
1. Слишком строгие фильтры в `search_config.yaml`
2. Малый период поиска (`period: one_day`)
3. Редкая специализация

**Решение:**
```yaml
# Ослабить фильтры
period:
  month: true  # Вместо one_day
area: ""  # Убрать региональные ограничения
```

### Проблема: "Too many requests"

**Симптомы:**
```
WARNING - Слишком много запросов, ждем 1-2 часа
```

**Причины:**
1. Слишком много API запросов за короткое время
2. `per_page = 10` → много страниц

**Решение:**
```python
# Увеличить per_page
search_params = {"page": page_num, "per_page": 50}

# Добавить задержки между страницами
time.sleep(random.uniform(2, 5))
```

### Проблема: "Повторная обработка вакансий"

**Симптомы:**
```
WARNING - Вакансия уже встречалась, пропускаем
```

**Причины:**
1. Дубликаты между `similar_vacancies` и `vacancies`
2. Восстановление после сбоя без checkpoint

**Решение:**
1. Добавить дедупликацию по `vacancy_id`
2. Сохранять `page_num` в кэш

---

## Заключение

### Текущее состояние

✅ **Работает:**
- Постраничная обработка вакансий
- Двухэтапный поиск (похожие + общие)
- Обработка ошибок и лимитов
- Сохранение прогресса откликов

⚠️ **Требует улучшения:**
- Фиксированный `per_page = 10`
- Отсутствие checkpoint для страниц
- Дубликаты между этапами
- Двойной запрос на первой странице

### Рекомендации

**Quick Wins (1-2 часа):**
1. Увеличить `per_page` до 50
2. Добавить дедупликацию
3. Сохранять `page_num` в кэш

**Средний приоритет (1 день):**
4. Убрать двойной запрос на page=0
5. Progress bar с ETA
6. Параметризовать лимиты

**Долгосрочные (1 неделя):**
7. Асинхронная предзагрузка
8. Кэш метаданных страниц
9. A/B тестирование стратегий

---

**Версия документа:** 1.0  
**Дата создания:** 10 ноября 2024  
**Автор:** AI Assistant на основе анализа кодовой базы

