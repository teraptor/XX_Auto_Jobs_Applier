# Обзор модуля resume_builder

## Назначение модуля

Модуль `resume_builder` предназначен для автоматической генерации профессиональных резюме в формате PDF на основе данных пользователя и описания вакансии с использованием LLM (Large Language Models).

**Основная задача**: Преобразовать структурированные данные резюме (JSON) в красиво оформленное HTML-резюме с CSS стилизацией, а затем конвертировать его в PDF.

---

## Архитектурные принципы

### 1. Разделение ответственности (SRP)

Модуль разделен на специализированные компоненты:
- **FacadeManager** - координация процесса генерации
- **ResumeGenerator** - генерация HTML
- **StyleManager** - управление стилями
- **PromptManager** - управление промптами для LLM
- **PDFConverter** - конвертация HTML в PDF

### 2. Паттерн Facade

`FacadeManager` скрывает сложность взаимодействия между компонентами и предоставляет простой интерфейс для внешнего использования.

### 3. Шаблонный метод (Template Method)

Резюме генерируется из набора секций, каждая секция генерируется по шаблону HTML с заполнением данными через LLM.

### 4. Стратегия (Strategy)

Разные CSS стили применяются к одному и тому же HTML контенту, меняя внешний вид резюме.

---

## Структура модуля

```
resume_builder/
├── manager_facade.py          # Фасад для управления процессом
├── resume_generator.py        # Генерация HTML резюме
├── style_manager.py           # Управление CSS стилями
├── config.py                  # Глобальная конфигурация
├── utils.py                   # Утилиты (HTML→PDF)
├── template_base.py           # Базовые HTML шаблоны секций
├── resume_prompt/             # Промпты для LLM
│   ├── __init__.py
│   ├── main_prompt.py        # Промпты без привязки к вакансии
│   └── job_description_prompt.py  # Промпты с учетом вакансии
└── resume_style/              # CSS стили для резюме
    ├── style_cloyola.css
    ├── style_josylad_blue.css
    ├── style_josylad_grey.css
    ├── style_krishnavalliappan.css
    └── style_samodum_bold.css
```

---

## Компоненты модуля

### 1. FacadeManager

**Роль**: Главный координатор процесса генерации резюме

**Ответственность**:
- Инициализация всех компонентов
- Управление жизненным циклом генерации
- Взаимодействие с пользователем (выбор стиля)
- Координация между StyleManager, ResumeGenerator и PDFConverter
- Управление временными файлами

**Зависимости**:
- StyleManager - для работы со стилями
- ResumeGenerator - для генерации HTML
- Utils.HTML_to_PDF - для конвертации в PDF
- Logger - для логирования

---

### 2. ResumeGenerator

**Роль**: Генератор HTML резюме

**Ответственность**:
- Создание HTML документа из секций
- Применение CSS стиля к HTML
- Подстановка данных в HTML шаблон
- Запись HTML в файл

**Ключевые особенности**:
- Использует строковую подстановку (Template)
- Не зависит напрямую от LLM (получает готовый HTML)
- Создает полный HTML документ с мета-тегами и ссылками на ресурсы

---

### 3. StyleManager

**Роль**: Менеджер CSS стилей резюме

**Ответственность**:
- Сканирование доступных стилей в папке
- Парсинг метаданных стилей (имя автора, ссылка)
- Предоставление списка стилей для выбора
- Получение пути к выбранному стилю

**Формат метаданных в CSS**:
```css
/* Style Name $ Author Link */
```

**Пример**:
```css
/* Josylad Blue $ https://github.com/josylad */
```

---

### 4. GlobalConfig

**Роль**: Централизованное хранилище конфигурации

**Ответственность**:
- Хранение путей к ресурсам
- Хранение API ключей
- Хранение HTML шаблона
- Предоставление глобального доступа к конфигурации

**Паттерн**: Singleton (одна глобальная инстанция `global_config`)

---

### 5. PromptManager (resume_prompt/)

**Роль**: Управление промптами для LLM

**Ответственность**:
- Хранение промптов для каждой секции резюме
- Предоставление промптов с подстановкой данных
- Поддержка двух режимов:
  - Базовый (main_prompt.py) - без учета вакансии
  - С учетом вакансии (job_description_prompt.py)

**Секции резюме**:
1. Header (заголовок с контактами)
2. Education (образование)
3. Working Experience (опыт работы)
4. Side Projects (проекты)
5. Achievements (достижения)
6. Certifications (сертификаты)
7. Additional Skills (дополнительные навыки)

---

### 6. TemplateBase

**Роль**: Базовые HTML шаблоны секций

**Ответственность**:
- Предоставление HTML структуры для каждой секции
- Определение плейсхолдеров для данных
- Стандартизация CSS классов

**Особенности**:
- Использует Font Awesome иконки
- Использует семантические HTML теги
- CSS классы унифицированы для всех стилей

---

### 7. Utils

**Роль**: Утилиты для конвертации и работы с браузером

**Ответственность**:
- Конвертация HTML в PDF через Chrome DevTools Protocol
- Настройка параметров Selenium WebDriver
- Управление браузером для рендеринга PDF

**Ключевые функции**:
- `HTML_to_PDF(FilePath)` - конвертация HTML файла в PDF (base64)
- `create_driver_selenium()` - создание настроенного WebDriver
- `chrome_browser_options()` - настройки Chrome для headless режима

---

## Поток данных

### Общий процесс генерации резюме

```
┌─────────────────────────────────────────────────────────────┐
│                    1. Инициализация                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ FacadeManager(api_key, style_manager,                │   │
│  │               resume_generator, log_path)            │   │
│  │   ├─> StyleManager.set_styles_directory()            │   │
│  │   └─> Сохранить зависимости                          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    2. Выбор стиля                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ FacadeManager.choose_style()                         │   │
│  │   ├─> StyleManager.get_styles()                      │   │
│  │   │    └─> Сканировать папку resume_style/           │   │
│  │   │    └─> Парсить метаданные из CSS                 │   │
│  │   │    └─> Вернуть Dict[name → (file, author)]       │   │
│  │   ├─> StyleManager.format_choices()                  │   │
│  │   │    └─> Создать список для UI выбора              │   │
│  │   ├─> prompt_user() - показать меню выбора           │   │
│  │   └─> Сохранить selected_style                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              3. Генерация HTML через LLM                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ GPTResumeGenerator (внешний компонент)               │   │
│  │   ├─> set_job_description_from_text(job_desc)        │   │
│  │   │    └─> LLM: суммаризация описания вакансии       │   │
│  │   ├─> generate_header() → HTML заголовок             │   │
│  │   ├─> generate_education_section() → HTML            │   │
│  │   ├─> generate_work_experience_section() → HTML      │   │
│  │   ├─> generate_side_projects_section() → HTML        │   │
│  │   ├─> generate_achievements_section() → HTML         │   │
│  │   ├─> generate_certifications_section() → HTML       │   │
│  │   ├─> generate_additional_skills_section() → HTML    │   │
│  │   └─> generate_html_resume() → полное HTML резюме    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              4. Создание PDF                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ FacadeManager.pdf_base64()                           │   │
│  │   ├─> Проверить selected_style                       │   │
│  │   ├─> StyleManager.get_style_path(selected_style)    │   │
│  │   ├─> Создать временный HTML файл                    │   │
│  │   ├─> ResumeGenerator.create_resume()                │   │
│  │   │    ├─> GPTResumeGenerator.set_job_description()  │   │
│  │   │    ├─> GPTResumeGenerator.generate_html_resume() │   │
│  │   │    ├─> Подставить HTML и style_path в шаблон     │   │
│  │   │    └─> Записать в temp_html_path                 │   │
│  │   ├─> HTML_to_PDF(temp_html_path)                    │   │
│  │   │    ├─> Создать Selenium WebDriver                │   │
│  │   │    ├─> driver.get(file:/// + temp_html_path)     │   │
│  │   │    ├─> driver.execute_cdp_cmd("Page.printToPDF") │   │
│  │   │    │    └─> Параметры: A4, margins, base64       │   │
│  │   │    └─> Вернуть PDF в base64                      │   │
│  │   ├─> Удалить временный HTML файл                    │   │
│  │   └─> Вернуть pdf_base64                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Взаимодействие с внешними системами

### 1. LLM (GPTResumeGenerator)

**Направление**: resume_builder → LLM

**Интерфейс**:
```
GPTResumeGenerator {
    set_resume(resume: Dict)
    set_job_description_from_text(job_desc: str)
    generate_header() → str (HTML)
    generate_education_section() → str (HTML)
    generate_work_experience_section() → str (HTML)
    generate_side_projects_section() → str (HTML)
    generate_achievements_section() → str (HTML)
    generate_certifications_section() → str (HTML)
    generate_additional_skills_section() → str (HTML)
    generate_html_resume() → str (полный HTML)
}
```

**Используемые промпты**:
- `prompt_header` - генерация заголовка
- `prompt_education` - генерация секции образования
- `prompt_working_experience` - генерация опыта работы
- `prompt_side_projects` - генерация проектов
- `prompt_achievements` - генерация достижений
- `prompt_certifications` - генерация сертификатов
- `prompt_additional_skills` - генерация навыков
- `summarize_prompt_template` - суммаризация вакансии

**Особенности**:
- Каждая секция генерируется отдельным вызовом LLM
- LLM возвращает чистый HTML без обёрток
- Промпты содержат инструкции по ATS-оптимизации

---

### 2. Selenium WebDriver (Chrome)

**Направление**: resume_builder → Chrome DevTools Protocol

**Цель**: Конвертация HTML в PDF

**Метод**: Chrome DevTools Protocol команда `Page.printToPDF`

**Параметры PDF**:
- Формат: A4 (8.27 × 11.69 дюймов)
- Ориентация: Portrait (вертикальная)
- Margins: top/bottom 0.8", left/right 0.5"
- printBackground: true (печатать фоны)
- preferCSSPageSize: true (использовать CSS @page)
- transferMode: ReturnAsBase64

**Chrome опции**:
- --headless (без GUI)
- --no-sandbox
- --disable-gpu
- --single-process
- --disable-extensions
- --disable-cache
- window-size=1200x800

---

### 3. Файловая система

**Операции чтения**:
- Чтение CSS стилей из `resume_style/`
- Парсинг метаданных стилей (первая строка CSS)

**Операции записи**:
- Создание временного HTML файла (tempfile.NamedTemporaryFile)
- Удаление временного файла после конвертации

**Структура папок**:
```
resume_style/
├── style_cloyola.css
├── style_josylad_blue.css
├── style_josylad_grey.css
├── style_krishnavalliappan.css
└── style_samodum_bold.css
```

**Формат CSS файла**:
```css
/* Style Name $ Author Link */

/* Остальные CSS правила */
body { ... }
header { ... }
```

---

## Модели данных

### ResumeData (входные данные)

**Структура**:
```
ResumeData {
    personal_information: {
        full_name: str
        city: str
        country: str
        phone: str
        email: str
        linkedin: str (опционально)
        github: str (опционально)
    }
    
    education_details: [{
        university: str
        location: str
        degree: str
        field_of_study: str
        grade: str (опционально)
        start_year: str
        end_year: str
        coursework: [str] (опционально)
    }]
    
    experience_details: [{
        company: str
        location: str
        job_title: str
        start_date: str
        end_date: str
        responsibilities: [str]
        achievements: [str]
    }]
    
    projects: [{
        name: str
        link: str (GitHub или др.)
        description: [str]
        technologies: [str]
    }] (опционально)
    
    achievements: [{
        award: str
        description: str
    }] (опционально)
    
    certifications: [{
        name: str
        description: str
    }] (опционально)
    
    languages: [str]
    interests: [str]
    skills: [str]
}
```

---

### Style (метаданные стиля)

**Структура**:
```
Style {
    name: str          // Имя стиля
    file_name: str     // Имя файла CSS
    author_link: str   // Ссылка на автора
}
```

**Парсинг**:
- Читается первая строка CSS файла
- Формат: `/* name $ author_link */`
- Разбивается по символу `$`

---

### HTMLTemplate

**Структура базового шаблона**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume</title>
    <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" />
    <link rel="stylesheet" href="$style_path">
</head>
$markdown
</body>
</html>
```

**Плейсхолдеры**:
- `$style_path` - путь к CSS файлу стиля
- `$markdown` - сгенерированный HTML контент резюме

---

## Обработка ошибок

### Уровни обработки

**1. Уровень FacadeManager**:
- ValueError: если стиль не выбран перед генерацией PDF
- Проверка наличия выбранного стиля

**2. Уровень StyleManager**:
- FileNotFoundError: папка стилей не найдена
- PermissionError: нет доступа к папке стилей
- Логирование ошибок через logger

**3. Уровень Utils**:
- FileNotFoundError: HTML файл не найден
- WebDriverException: ошибка WebDriver
- RuntimeError: обёртка ошибок WebDriver
- finally: гарантированное закрытие драйвера

**4. Уровень ResumeGenerator**:
- IOError: ошибка записи HTML файла
- Нет явной обработки (полагается на вызывающий код)

---

## Безопасность и валидация

### Валидация данных

**1. Проверка стиля**:
- selected_style не должен быть None
- Стиль должен существовать в списке доступных

**2. Проверка файлов**:
- HTML файл должен существовать перед конвертацией
- Путь к HTML файлу проверяется через os.path.isfile()

**3. Валидация данных резюме**:
- Проверка на None для опциональных полей
- Промпты LLM содержат инструкции по обработке None

### Безопасность файловой системы

**1. Временные файлы**:
- Используется tempfile.NamedTemporaryFile
- delete=False (требуется ручное удаление)
- Файлы удаляются после использования

**2. Пути к файлам**:
- Относительные пути разрешаются через Path.resolve()
- Использование os.path.abspath для абсолютных путей
- file:/// протокол для локальных файлов в WebDriver

---

## Ограничения и особенности

### Технические ограничения

**1. Зависимость от Selenium**:
- Требуется установленный Chrome/Chromium
- Требуется ChromeDriver
- Медленная конвертация (~2-5 секунд на PDF)

**2. Зависимость от LLM**:
- Требуется API ключ LLM
- Каждая секция = отдельный запрос к LLM
- 7-8 запросов на одно резюме
- Стоимость генерации ~$0.01-0.05 за резюме

**3. Форматирование**:
- HTML должен быть валидным
- CSS классы должны соответствовать шаблону
- Изменение структуры HTML ломает стили

### Функциональные ограничения

**1. Стили**:
- Нельзя применить несколько стилей одновременно
- Стили должны быть в формате single-file CSS
- Метаданные должны быть в первой строке

**2. Интерактивность**:
- Выбор стиля через CLI (inquirer)
- Нет GUI интерфейса
- Нет предпросмотра резюме перед генерацией

**3. Кастомизация**:
- Нельзя редактировать сгенерированный HTML
- Нельзя комбинировать секции из разных шаблонов
- Нет поддержки custom секций

---

## Оптимизации

### Производительность

**1. Кэширование**:
- ❌ Нет кэширования сгенерированных секций
- ❌ Нет кэширования стилей
- ❌ Каждая генерация = полный цикл LLM вызовов

**2. Параллелизация**:
- ❌ Секции генерируются последовательно
- ❌ Можно распараллелить генерацию секций

**3. Selenium**:
- ✅ Настройки Chrome оптимизированы для headless
- ✅ Отключены расширения, GPU, кэш
- ❌ WebDriver создается для каждой конвертации

### Рекомендации для Go реализации

**1. Использовать goroutines**:
- Параллельная генерация секций через LLM
- sync.WaitGroup для ожидания всех секций

**2. Кэширование**:
- Кэшировать список стилей (редко меняется)
- Кэшировать суммаризацию вакансий (по хешу)

**3. Альтернативы Selenium**:
- Использовать wkhtmltopdf (быстрее)
- Использовать headless Chrome API напрямую
- Использовать Go библиотеки для PDF (chromedp, go-wkhtmltopdf)

---

## Использование модуля

### Пример использования (концептуально)

**Шаг 1: Инициализация**
```
style_manager = StyleManager()
resume_generator = ResumeGenerator()
facade = FacadeManager(api_key, style_manager, resume_generator, log_path)
```

**Шаг 2: Выбор стиля**
```
facade.choose_style()
// Пользователь выбирает стиль из меню
```

**Шаг 3: Генерация PDF**
```
gpt_resume_generator = GPTResumeGenerator(api_key, llm)
gpt_resume_generator.set_resume(resume_data)

job_description = "Full Stack Developer at Company X..."
pdf_base64 = facade.pdf_base64(gpt_resume_generator, job_description)

// pdf_base64 - готовый PDF в base64
```

---

## Интеграция с основным приложением

### Текущее состояние

**Статус**: ❌ НЕ используется в текущей версии

**Причина**: 
- Код закомментирован в `main.py` и `llm_manager.py`
- Строка 106 в `main.py`: `# bot.set_resume_generator(resume_generator_manager, gpt_resume_genarator)`

**Потенциальное использование**:
- Генерация кастомных резюме для каждой вакансии
- Автоматическая адаптация резюме под требования работодателя
- Отправка PDF резюме вместо ссылки на hh.ru

### Архитектурная роль (если активирован)

**Интеграция через BotFacade**:
```
BotFacade {
    set_resume_generator(resume_generator_manager, gpt_resume_generator)
        └─> JobApplier.set_resume_generator_manager()
            └─> Использование при отклике на вакансию
}
```

**Сценарий использования**:
1. Парсинг резюме с hh.ru → ResumeScraper
2. Получение описания вакансии → JobApplier
3. Генерация адаптированного резюме → ResumeBuilder
4. Отправка PDF резюме → HeadHunter API или Email

---

## Заключение

### Ключевые особенности модуля

**✅ Плюсы**:
- Модульная архитектура
- Чистый паттерн Facade
- Гибкая система стилей
- ATS-оптимизированные промпты
- Профессиональный HTML/CSS

**❌ Минусы**:
- Зависимость от Selenium (медленно)
- Множественные вызовы LLM (дорого)
- Отсутствие кэширования
- Нет предпросмотра
- Не используется в продакшене

### Готовность к реализации на Go

**Сложность реализации**: Средняя

**Компоненты**:
- ✅ StyleManager - простой (парсинг файлов)
- ✅ ResumeGenerator - простой (строковые шаблоны)
- ⚠️ FacadeManager - средний (координация)
- ⚠️ HTML_to_PDF - средний (интеграция с Chrome)
- ✅ Промпты - тривиальный (строковые константы)

**Рекомендации для Go**:
1. Использовать `chromedp` вместо Selenium
2. Реализовать параллельную генерацию секций
3. Добавить кэширование
4. Рассмотреть альтернативы для PDF (wkhtmltopdf)

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Статус**: Готово к реализации на Go

