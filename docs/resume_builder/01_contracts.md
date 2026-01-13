# Контракты и интерфейсы модуля resume_builder

## Соглашения о типах данных для Go

**Базовые типы**:
- `string` - строки
- `int` - целые числа
- `bool` - булевы значения
- `[]Type` - слайсы (списки)
- `map[string]Type` - словари
- `*Type` - указатели (опциональные значения)
- `error` - ошибки

**Структуры**:
- Используются для группировки данных
- Поля с тегами `json` для сериализации
- Опциональные поля через указатели

---

## 1. FacadeManager

### Описание

Главный координатор процесса генерации резюме. Управляет жизненным циклом всех компонентов и предоставляет простой интерфейс для внешнего использования.

---

### Структура данных

```go
type FacadeManager struct {
    styleManager    *StyleManager
    resumeGenerator *ResumeGenerator
    selectedStyle   *string  // nil если стиль не выбран
    logger          Logger
}
```

**Поля**:
- `styleManager` - менеджер CSS стилей
- `resumeGenerator` - генератор HTML резюме
- `selectedStyle` - выбранный пользователем стиль (опционально)
- `logger` - логгер для записи событий

---

### Конструктор

```
NewFacadeManager(
    apiKey string,
    styleManager *StyleManager,
    resumeGenerator *ResumeGenerator,
    logPath string
) *FacadeManager
```

**Параметры**:
- `apiKey` - API ключ для LLM (сохраняется в конфигурации)
- `styleManager` - инстанция менеджера стилей
- `resumeGenerator` - инстанция генератора резюме
- `logPath` - путь к файлу логов

**Возвращает**: Инстанцию FacadeManager

**Логика инициализации**:
1. Создать инстанцию FacadeManager
2. Определить путь к папке модуля (текущая директория)
3. Построить путь к папке стилей: `{module_dir}/resume_style`
4. Вызвать `styleManager.SetStylesDirectory(styles_directory)`
5. Сохранить ссылки на style_manager и resume_generator
6. Инициализировать selected_style как nil
7. Вернуть инстанцию

---

### Методы

#### PromptUser()

```
PromptUser(choices []string, message string) (string, error)
```

**Назначение**: Показать интерактивное меню выбора пользователю

**Параметры**:
- `choices` - список доступных вариантов
- `message` - сообщение для пользователя

**Возвращает**: 
- Выбранный вариант (string)
- Ошибка (если пользователь отменил выбор)

**Логика**:
1. Создать вопрос с типом List (меню выбора)
2. Установить message как текст вопроса
3. Установить choices как варианты ответа
4. Показать меню через CLI библиотеку (например, survey в Go)
5. Дождаться выбора пользователя
6. Вернуть выбранный вариант
7. Если пользователь отменил (Ctrl+C) - вернуть ошибку

**Обработка ошибок**:
- Пользователь отменил выбор → вернуть error
- Ошибка отображения меню → вернуть error

---

#### ChooseStyle()

```
ChooseStyle() error
```

**Назначение**: Показать меню выбора стиля резюме и сохранить выбор

**Параметры**: Нет

**Возвращает**: Ошибку, если выбор не удался

**Логика**:
1. Вызвать `styleManager.GetStyles()` → получить `map[string]StyleInfo`
2. Если styles пустой:
   - Логировать warning "Нет доступных стилей"
   - Вернуть error "No styles available"
3. Создать список вариантов для меню:
   - Вызвать `styleManager.FormatChoices(styles)` → получить `[]string`
4. Добавить в конец списка: "Создать свой стиль в CSS"
5. Вызвать `PromptUser(formatted_choices, "Какой стиль резюме вы бы хотели использовать?")`
6. Получить selected_choice (выбранный вариант)
7. Проверить selected_choice:
   - Если == "Создать свой стиль в CSS":
     - Определить URL туториала
     - Логировать "Открываем туториал в вашем браузере..."
     - Открыть URL в браузере (webbrowser.open)
     - Завершить программу (exit)
   - Иначе:
     - Извлечь имя стиля: split по " (" и взять первую часть
     - Сохранить в this.selectedStyle
     - Вернуть nil (успех)
8. Если возникла ошибка - вернуть её

**Обработка ошибок**:
- Нет доступных стилей → error
- Пользователь отменил выбор → error
- Ошибка открытия браузера → логировать, но не падать

---

#### PDFBase64()

```
PDFBase64(
    gptResumeGenerator GPTResumeGenerator,
    jobDescriptionText string
) (string, error)
```

**Назначение**: Сгенерировать PDF резюме и вернуть его в формате base64

**Параметры**:
- `gptResumeGenerator` - инстанция генератора резюме с LLM
- `jobDescriptionText` - текст описания вакансии

**Возвращает**:
- PDF в формате base64 (string)
- Ошибка (если генерация не удалась)

**Логика**:
1. **Валидация стиля**:
   - Если this.selectedStyle == nil:
     - Вернуть error "Перед созданием PDF-файла необходимо выбрать стиль"
2. **Получение пути к стилю**:
   - Вызвать `styleManager.GetStylePath(this.selectedStyle)` → style_path
3. **Создание временного HTML файла**:
   - Создать временный файл через ioutil.TempFile()
   - Параметры:
     - Директория: системная temp (os.TempDir())
     - Префикс: "resume_"
     - Суффикс: ".html"
   - Получить путь к файлу: temp_html_path
   - Не удалять файл сразу (нужен для WebDriver)
4. **Генерация HTML резюме**:
   - Вызвать:
     ```
     resumeGenerator.CreateResume(
         gptResumeGenerator,
         style_path,
         jobDescriptionText,
         temp_html_path
     )
     ```
   - Это записывает HTML в temp_html_path
5. **Конвертация HTML → PDF**:
   - Вызвать `HTMLToPDF(temp_html_path)` → pdf_base64
   - Получить PDF в base64 формате
6. **Очистка**:
   - Удалить временный файл: os.Remove(temp_html_path)
   - Использовать defer для гарантированного удаления
7. **Возврат результата**:
   - Вернуть pdf_base64, nil (успех)

**Обработка ошибок**:
- selectedStyle == nil → error "Style not selected"
- Ошибка создания временного файла → error
- Ошибка генерации HTML → error (прокинуть из CreateResume)
- Ошибка конвертации PDF → error (прокинуть из HTMLToPDF)
- Ошибка удаления файла → логировать, но не падать

**Гарантии**:
- Временный файл всегда удаляется (через defer)
- Возврат ошибки не прерывает очистку

---

## 2. StyleManager

### Описание

Менеджер CSS стилей резюме. Сканирует папку со стилями, парсит метаданные и предоставляет список доступных стилей.

---

### Структура данных

```go
type StyleManager struct {
    stylesDirectory *string  // nil если не установлено
    logger          Logger
}

type StyleInfo struct {
    FileName   string  // Имя файла CSS
    AuthorLink string  // Ссылка на автора
}
```

**Поля StyleManager**:
- `stylesDirectory` - путь к папке со стилями (опционально)
- `logger` - логгер для записи событий

**Поля StyleInfo**:
- `FileName` - имя файла CSS (например, "style_cloyola.css")
- `AuthorLink` - ссылка на автора (например, "https://github.com/author")

---

### Конструктор

```
NewStyleManager() *StyleManager
```

**Параметры**: Нет

**Возвращает**: Инстанцию StyleManager

**Логика**:
1. Создать инстанцию StyleManager
2. Инициализировать stylesDirectory как nil
3. Инициализировать logger
4. Вернуть инстанцию

---

### Методы

#### SetStylesDirectory()

```
SetStylesDirectory(stylesDirectory string) error
```

**Назначение**: Установить путь к папке со стилями

**Параметры**:
- `stylesDirectory` - путь к папке (относительный или абсолютный)

**Возвращает**: Ошибку, если путь недоступен

**Логика**:
1. Проверить, что stylesDirectory не пустой
2. Проверить существование папки: os.Stat(stylesDirectory)
3. Проверить, что это директория (не файл)
4. Сохранить в this.stylesDirectory
5. Вернуть nil (успех)

**Обработка ошибок**:
- Пустой путь → error "Empty path"
- Папка не существует → error "Directory not found"
- Это файл, а не папка → error "Not a directory"
- Нет прав доступа → error "Permission denied"

---

#### GetStyles()

```
GetStyles() (map[string]StyleInfo, error)
```

**Назначение**: Получить список доступных стилей с метаданными

**Параметры**: Нет

**Возвращает**:
- Словарь: имя стиля → информация о стиле
- Ошибка (если сканирование не удалось)

**Логика**:
1. **Инициализация**:
   - Создать пустой map: `styles := make(map[string]StyleInfo)`
2. **Проверка директории**:
   - Если this.stylesDirectory == nil:
     - Вернуть error "Styles directory not set"
3. **Чтение содержимого папки**:
   - Вызвать `ioutil.ReadDir(this.stylesDirectory)` → files
   - Обработать ошибки (см. ниже)
4. **Обработка каждого файла**:
   - Для каждого file в files:
     - Если !file.IsDir() (это файл):
       - Получить имя файла: file_name = file.Name()
       - Построить полный путь: file_path = path.Join(stylesDirectory, file_name)
       - **Парсинг метаданных**:
         - Открыть файл: os.Open(file_path)
         - Прочитать первую строку: bufio.Scanner.Scan()
         - Получить текст: first_line = scanner.Text()
         - Закрыть файл
       - **Извлечение метаданных**:
         - Обрезать пробелы: first_line = strings.TrimSpace(first_line)
         - Проверить формат: strings.HasPrefix("/*") && strings.HasSuffix("*/")
         - Если формат верный:
           - Убрать `/*` и `*/`: content = first_line[2:len-2]
           - Обрезать пробелы: content = strings.TrimSpace(content)
           - Проверить наличие `$`: strings.Contains(content, "$")
           - Если есть `$`:
             - Разделить по `$`: parts = strings.Split(content, "$")
             - style_name = strings.TrimSpace(parts[0])
             - author_link = strings.TrimSpace(parts[1])
             - Сохранить в map:
               ```
               styles[style_name] = StyleInfo{
                   FileName: file_name,
                   AuthorLink: author_link
               }
               ```
5. **Возврат результата**:
   - Вернуть styles, nil (успех)

**Обработка ошибок**:
- Папка не найдена → логировать error, вернуть error
- Нет прав доступа → логировать error, вернуть error
- Ошибка чтения файла → пропустить файл, продолжить
- Неверный формат метаданных → пропустить файл, продолжить

**Примеры метаданных**:
```css
/* Josylad Blue $ https://github.com/josylad */
```

---

#### FormatChoices()

```
FormatChoices(styles map[string]StyleInfo) []string
```

**Назначение**: Отформатировать список стилей для отображения в меню

**Параметры**:
- `styles` - словарь стилей (результат GetStyles)

**Возвращает**: Список отформатированных строк

**Логика**:
1. Создать пустой слайс: `choices := make([]string, 0, len(styles))`
2. Для каждого style_name, style_info в styles:
   - Создать строку формата:
     ```
     "{style_name} (style author -> {author_link})"
     ```
   - Добавить в choices
3. Отсортировать choices по алфавиту (опционально)
4. Вернуть choices

**Пример результата**:
```
[
  "Josylad Blue (style author -> https://github.com/josylad)",
  "Cloyola (style author -> https://github.com/cloyola)",
  "Krishna (style author -> https://github.com/krishnavalliappan)"
]
```

---

#### GetStylePath()

```
GetStylePath(selectedStyle string) (string, error)
```

**Назначение**: Получить полный путь к файлу CSS выбранного стиля

**Параметры**:
- `selectedStyle` - имя выбранного стиля

**Возвращает**:
- Полный путь к CSS файлу
- Ошибка (если стиль не найден)

**Логика**:
1. Вызвать `GetStyles()` → styles, err
2. Проверить ошибку: if err != nil → вернуть error
3. Проверить наличие стиля:
   - `style_info, ok := styles[selectedStyle]`
   - Если !ok → вернуть error "Style not found"
4. Получить имя файла: file_name = style_info.FileName
5. Построить полный путь:
   ```
   style_path := path.Join(this.stylesDirectory, file_name)
   ```
6. Проверить существование файла: os.Stat(style_path)
7. Вернуть style_path, nil (успех)

**Обработка ошибок**:
- Ошибка GetStyles → прокинуть
- Стиль не найден → error "Style '{name}' not found"
- Файл не существует → error "Style file not found"

---

## 3. ResumeGenerator

### Описание

Генератор HTML резюме. Получает готовые HTML секции от LLM, вставляет их в базовый шаблон и записывает результат в файл.

---

### Структура данных

```go
type ResumeGenerator struct {
    htmlTemplate string
    logger       Logger
}
```

**Поля**:
- `htmlTemplate` - базовый HTML шаблон с плейсхолдерами
- `logger` - логгер для записи событий

**Шаблон** (хранится как константа):
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume</title>
    <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&display=swap" rel="stylesheet" />
    <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" />
    <link rel="stylesheet" href="$style_path">
</head>
$markdown
</body>
</html>
```

---

### Конструктор

```
NewResumeGenerator() *ResumeGenerator
```

**Параметры**: Нет

**Возвращает**: Инстанцию ResumeGenerator

**Логика**:
1. Создать инстанцию ResumeGenerator
2. Установить htmlTemplate (константа выше)
3. Инициализировать logger
4. Вернуть инстанцию

---

### Методы

#### CreateResume()

```
CreateResume(
    gptResumeGenerator GPTResumeGenerator,
    stylePath string,
    jobDescriptionText string,
    tempHTMLPath string
) error
```

**Назначение**: Сгенерировать HTML резюме и записать в файл

**Параметры**:
- `gptResumeGenerator` - генератор HTML через LLM
- `stylePath` - полный путь к CSS файлу стиля
- `jobDescriptionText` - текст описания вакансии
- `tempHTMLPath` - путь для записи готового HTML

**Возвращает**: Ошибку, если генерация не удалась

**Логика**:
1. **Установка описания вакансии в LLM**:
   - Вызвать `gptResumeGenerator.SetJobDescriptionFromText(jobDescriptionText)`
   - Это заставляет LLM учитывать вакансию при генерации
2. **Вызов внутреннего метода**:
   - Вызвать `this._createResume(gptResumeGenerator, stylePath, tempHTMLPath)`
3. **Возврат результата**:
   - Вернуть ошибку (если есть) или nil

**Обработка ошибок**:
- Ошибка установки описания → прокинуть
- Ошибка генерации → прокинуть из _createResume

---

#### _createResume() (приватный)

```
_createResume(
    gptResumeGenerator GPTResumeGenerator,
    stylePath string,
    tempHTMLPath string
) error
```

**Назначение**: Внутренний метод для генерации HTML резюме

**Параметры**:
- `gptResumeGenerator` - генератор HTML через LLM
- `stylePath` - полный путь к CSS файлу стиля
- `tempHTMLPath` - путь для записи готового HTML

**Возвращает**: Ошибку, если генерация не удалась

**Логика**:
1. **Генерация HTML контента через LLM**:
   - Вызвать `gptResumeGenerator.GenerateHTMLResume()` → html_resume
   - Получить полный HTML всех секций резюме
2. **Подстановка в шаблон**:
   - Создать копию this.htmlTemplate
   - Заменить `$style_path` на stylePath
   - Заменить `$markdown` на html_resume
   - Получить итоговый HTML: message
3. **Запись в файл**:
   - Открыть файл для записи: os.Create(tempHTMLPath)
   - Записать message в файл
   - Закрыть файл
   - Обработать ошибки (см. ниже)
4. **Возврат результата**:
   - Вернуть nil (успех) или error

**Обработка ошибок**:
- Ошибка генерации HTML → прокинуть
- Ошибка создания файла → error
- Ошибка записи в файл → error
- Ошибка закрытия файла → логировать, но не падать

**Используемый метод подстановки**:
- Go: strings.ReplaceAll()
- Замена всех вхождений плейсхолдеров

---

## 4. GlobalConfig

### Описание

Глобальная конфигурация модуля. Хранит пути к ресурсам, API ключи и другие настройки.

**Паттерн**: Singleton (одна инстанция на приложение)

---

### Структура данных

```go
type GlobalConfig struct {
    StringsModuleResumePath            *string
    StringsModuleResumeJobDescPath     *string
    StringsModuleName                  *string
    StylesDirectory                    *string
    LogOutputFilePath                  *string
    APIKey                             *string
    HTMLTemplate                       string
}
```

**Поля**:
- `StringsModuleResumePath` - путь к модулю промптов (main_prompt)
- `StringsModuleResumeJobDescPath` - путь к модулю промптов (job_description_prompt)
- `StringsModuleName` - имя модуля
- `StylesDirectory` - путь к папке со стилями
- `LogOutputFilePath` - путь к файлу логов
- `APIKey` - API ключ для LLM
- `HTMLTemplate` - базовый HTML шаблон

**Все поля опциональные** (кроме HTMLTemplate) - указатели на строки

---

### Глобальная инстанция

```go
var globalConfig = &GlobalConfig{
    HTMLTemplate: `<!DOCTYPE html>...`,
}
```

**Использование**:
```go
import "resume_builder"

resume_builder.globalConfig.APIKey = "sk-..."
```

---

### Методы

#### SetAPIKey()

```
SetAPIKey(apiKey string)
```

**Назначение**: Установить API ключ

**Параметры**:
- `apiKey` - ключ для LLM

**Логика**:
- Сохранить в globalConfig.APIKey

---

#### GetAPIKey()

```
GetAPIKey() (string, error)
```

**Назначение**: Получить API ключ

**Возвращает**:
- API ключ
- Ошибка, если не установлен

**Логика**:
- Если APIKey == nil → error "API key not set"
- Вернуть *APIKey

---

## 5. Utils - HTML to PDF

### Описание

Утилиты для конвертации HTML в PDF через Chrome DevTools Protocol.

---

### Функции

#### HTMLToPDF()

```
HTMLToPDF(filePath string) (string, error)
```

**Назначение**: Конвертировать HTML файл в PDF (base64)

**Параметры**:
- `filePath` - путь к HTML файлу

**Возвращает**:
- PDF в base64 формате
- Ошибка (если конвертация не удалась)

**Логика**:
1. **Валидация файла**:
   - Проверить существование: os.Stat(filePath)
   - Если не существует → error "Файл не найден"
2. **Подготовка URL**:
   - Получить абсолютный путь: filepath.Abs(filePath)
   - Создать file:/// URL:
     ```
     fileURL := "file:///" + strings.ReplaceAll(absPath, "\\", "/")
     ```
3. **Создание WebDriver**:
   - Вызвать `CreateDriverSelenium()` → driver
   - Получить инстанцию Chrome WebDriver
4. **Конвертация** (в блоке defer для гарантированного закрытия):
   - defer driver.Quit() - закрыть драйвер в конце
   - Открыть HTML: driver.Get(fileURL)
   - Подождать загрузки: time.Sleep(2 * time.Second)
   - Выполнить Chrome DevTools команду:
     ```
     result := driver.ExecuteCDP("Page.printToPDF", map[string]interface{}{
         "printBackground":       true,
         "landscape":             false,
         "paperWidth":            8.27,   // A4 ширина
         "paperHeight":           11.69,  // A4 высота
         "marginTop":             0.8,
         "marginBottom":          0.8,
         "marginLeft":            0.5,
         "marginRight":           0.5,
         "displayHeaderFooter":   false,
         "preferCSSPageSize":     true,
         "generateDocumentOutline": false,
         "generateTaggedPDF":     false,
         "transferMode":          "ReturnAsBase64",
     })
     ```
   - Извлечь PDF из результата: pdf_base64 = result["data"]
5. **Возврат результата**:
   - Вернуть pdf_base64, nil (успех)

**Обработка ошибок**:
- Файл не найден → error
- Ошибка создания драйвера → RuntimeError
- Ошибка WebDriver → RuntimeError с обёрткой
- finally: драйвер всегда закрывается (defer)

---

#### CreateDriverSelenium()

```
CreateDriverSelenium() (selenium.WebDriver, error)
```

**Назначение**: Создать настроенный Selenium WebDriver

**Параметры**: Нет

**Возвращает**:
- Инстанция WebDriver
- Ошибка (если создание не удалось)

**Логика**:
1. **Получение опций Chrome**:
   - Вызвать `ChromeBrowserOptions()` → options
2. **Определение пути к ChromeDriver**:
   - Вызвать ChromeDriverManager.Install() → chrome_install
   - Получить директорию: folder = path.Dir(chrome_install)
   - Определить имя исполняемого файла:
     - Windows: "chromedriver.exe"
     - Linux/Mac: "chromedriver"
   - Построить полный путь: chromedriver_path = path.Join(folder, exe_name)
3. **Создание WebDriver**:
   - Создать Service: service = selenium.NewChromeService(chromedriver_path)
   - Создать WebDriver: driver = selenium.NewChromeDriver(service, options)
   - Вернуть driver, nil
4. **Обработка ошибок**:
   - Любая ошибка → вернуть nil, error

---

#### ChromeBrowserOptions()

```
ChromeBrowserOptions() selenium.ChromeOptions
```

**Назначение**: Получить настройки Chrome для headless режима

**Параметры**: Нет

**Возвращает**: Объект с опциями Chrome

**Логика**:
1. Создать объект опций: options = selenium.NewChromeOptions()
2. Добавить аргументы:
   ```
   --start-maximized
   --no-sandbox
   --disable-dev-shm-usage
   --ignore-certificate-errors
   --disable-extensions
   --disable-gpu
   --window-size=1200x800
   --disable-background-timer-throttling
   --disable-backgrounding-occluded-windows
   --disable-translate
   --disable-popup-blocking
   --no-first-run
   --no-default-browser-check
   --single-process
   --disable-logging
   --disable-autofill
   --disable-plugins
   --disable-animations
   --disable-cache
   ```
3. Добавить experimental опции:
   ```
   "excludeSwitches": ["enable-automation", "enable-logging"]
   ```
4. Вернуть options

**Назначение опций**:
- Максимальная производительность
- Минимум логирования
- Отключение ненужных функций
- Стабильность работы в headless режиме

---

## 6. PromptManager (resume_prompt)

### Описание

Управление промптами для LLM. Предоставляет промпты для генерации каждой секции резюме.

---

### Константы промптов

#### prompt_header

**Назначение**: Генерация заголовка резюме с контактами

**Плейсхолдеры**:
- `{personal_information}` - JSON с личной информацией

**Структура промпта**:
- Роль: "HR expert and resume writer specializing in ATS-friendly resumes"
- Задача: Создать профессиональный заголовок
- Требования:
  1. Контактная информация (имя, город, телефон, email, LinkedIn, GitHub)
  2. Чистое форматирование
- Правило: Если поле None - опустить
- HTML шаблон: prompt_header_template

---

#### prompt_education

**Назначение**: Генерация секции образования

**Плейсхолдеры**:
- `{education_details}` - JSON с данными об образовании
- `{job_description}` - текст описания вакансии (опционально)

**Структура промпта**:
- Роль: "HR expert specializing in ATS-friendly resumes"
- Задача: Описать образование с учетом вакансии
- Требования:
  1. Название и локация учреждения
  2. Степень и область обучения
  3. Оценка (если высокая)
  4. Релевантные курсы (если есть)
- Правило: Если coursework None - пропустить
- HTML шаблон: prompt_education_template

---

#### prompt_working_experience

**Назначение**: Генерация секции опыта работы

**Плейсхолдеры**:
- `{experience_details}` - JSON с опытом работы
- `{job_description}` - текст описания вакансии (опционально)

**Структура промпта**:
- Роль: "HR expert specializing in ATS-friendly resumes"
- Задача: Описать опыт с учетом вакансии
- Требования:
  1. Название и локация компании
  2. Должность
  3. Даты работы
  4. Обязанности и достижения (с метриками)
- Правило: Подсветить релевантный опыт
- HTML шаблон: prompt_working_experience_template

---

#### prompt_side_projects

**Назначение**: Генерация секции проектов

**Плейсхолдеры**:
- `{projects}` - JSON с проектами
- `{job_description}` - текст описания вакансии (опционально)

**Структура промпта**:
- Роль: "HR expert specializing in ATS-friendly resumes"
- Задача: Описать проекты с учетом вакансии
- Требования:
  1. Название и ссылка на проект
  2. Достижения (GitHub stars, feedback)
  3. Технологии и вклад
- Правило: Показать релевантные навыки
- HTML шаблон: prompt_side_projects_template

---

#### prompt_achievements

**Назначение**: Генерация секции достижений

**Плейсхолдеры**:
- `{achievements}` - JSON с достижениями
- `{job_description}` - текст описания вакансии (опционально)

**Структура промпта**:
- Роль: "HR expert specializing in ATS-friendly resumes"
- Задача: Перечислить достижения
- Требования:
  1. Название награды/признания
  2. Описание и релевантность
- HTML шаблон: prompt_achievements_template

---

#### prompt_certifications

**Назначение**: Генерация секции сертификатов

**Плейсхолдеры**:
- `{certifications}` - JSON с сертификатами
- `{job_description}` - текст описания вакансии (опционально)

**Структура промпта**:
- Роль: "HR expert specializing in ATS-friendly resumes"
- Задача: Перечислить сертификаты
- Требования:
  1. Название сертификата
  2. Описание и релевантность
- Правило: Если description None - опустить
- HTML шаблон: prompt_certifications_template

---

#### prompt_additional_skills

**Назначение**: Генерация секции дополнительных навыков

**Плейсхолдеры**:
- `{languages}` - JSON с языками
- `{interests}` - JSON с интересами
- `{skills}` - JSON с навыками
- `{job_description}` - текст описания вакансии (опционально)

**Структура промпта**:
- Роль: "HR expert specializing in ATS-friendly resumes"
- Задача: Перечислить навыки релевантные вакансии
- Требования:
  1. Категория навыка
  2. Конкретные технологии
  3. Уровень владения
- Правило: НЕ добавлять информацию вне предоставленных полей
- HTML шаблон: prompt_additional_skills_template

---

#### summarize_prompt_template

**Назначение**: Суммаризация описания вакансии

**Плейсхолдеры**:
- `{text}` - полный текст описания вакансии

**Структура промпта**:
- Роль: "Seasoned HR expert"
- Задача: Извлечь ключевые требования из вакансии
- Анализ:
  1. Technical Skills
  2. Soft Skills
  3. Educational Qualifications
  4. Professional Experience
  5. Role Evolution (будущие тренды)
- Правило: Убрать шаблонный текст, оставить суть

---

## 7. Интерфейс GPTResumeGenerator (внешний)

### Описание

Компонент, который использует resume_builder для генерации HTML через LLM. Находится в модуле `llm_manager`.

**Примечание**: Это внешний интерфейс, который должен быть реализован отдельно.

---

### Методы (требуемые resume_builder)

#### SetResume()

```
SetResume(resume map[string]interface{})
```

**Назначение**: Установить данные резюме для генерации

**Параметры**:
- `resume` - структурированные данные резюме (JSON-like)

---

#### SetJobDescriptionFromText()

```
SetJobDescriptionFromText(jobDescriptionText string) error
```

**Назначение**: Суммаризировать описание вакансии через LLM

**Параметры**:
- `jobDescriptionText` - полный текст описания вакансии

**Логика**:
1. Вызвать LLM с промптом `summarize_prompt_template`
2. Подставить `{text}` = jobDescriptionText
3. Получить summary от LLM
4. Сохранить в this.jobDescription
5. Вернуть nil (успех) или error

---

#### GenerateHTMLResume()

```
GenerateHTMLResume() (string, error)
```

**Назначение**: Сгенерировать полное HTML резюме из всех секций

**Возвращает**:
- Полный HTML всех секций (без обёртки)
- Ошибка (если генерация не удалась)

**Логика**:
1. Сгенерировать каждую секцию (если данные есть):
   - Вызвать `generateHeader()` → header_html
   - Вызвать `generateEducationSection()` → education_html
   - Вызвать `generateWorkExperienceSection()` → experience_html
   - Вызвать `generateSideProjectsSection()` → projects_html
   - Вызвать `generateAchievementsSection()` → achievements_html
   - Вызвать `generateCertificationsSection()` → certifications_html
   - Вызвать `generateAdditionalSkillsSection()` → skills_html
2. Конкатенировать все секции:
   ```
   html := header_html + education_html + experience_html + ...
   ```
3. Вернуть html, nil

**Условия генерации секций**:
- Header: если personal_information существует
- Education: если education_details существует
- Experience: если experience_details существует
- Projects: если projects существует
- Achievements: если achievements существует
- Certifications: если certifications существует
- Skills: если languages/interests/skills существуют

---

#### generateHeader()

```
generateHeader() (string, error)
```

**Назначение**: Сгенерировать HTML заголовка

**Логика**:
1. Получить промпт: `prompt_header`
2. Подставить `{personal_information}` из this.resume
3. Вызвать LLM с промптом
4. Получить HTML от LLM
5. Вернуть HTML

---

#### generateEducationSection()

```
generateEducationSection() (string, error)
```

**Назначение**: Сгенерировать HTML секции образования

**Логика**:
1. Получить промпт: `prompt_education`
2. Подставить `{education_details}` из this.resume
3. Подставить `{job_description}` из this.jobDescription
4. Вызвать LLM с промптом
5. Получить HTML от LLM
6. Вернуть HTML

---

(Аналогично для остальных секций)

---

## Заключение

Все контракты и интерфейсы определены. Модуль готов к реализации на Go.

**Ключевые точки интеграции**:
1. FacadeManager - главный координатор
2. GPTResumeGenerator - внешний компонент (из llm_manager)
3. Selenium WebDriver - для конвертации PDF
4. Файловая система - для стилей и временных файлов

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Статус**: Готово к реализации на Go

