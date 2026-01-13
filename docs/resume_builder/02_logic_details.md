# Детальная логика работы модуля resume_builder

## Содержание

1. [Жизненный цикл генерации резюме](#жизненный-цикл-генерации-резюме)
2. [Парсинг метаданных CSS стилей](#парсинг-метаданных-css-стилей)
3. [Интеграция с LLM](#интеграция-с-llm)
4. [Конвертация HTML в PDF](#конвертация-html-в-pdf)
5. [Управление временными файлами](#управление-временными-файлами)
6. [Обработка ошибок](#обработка-ошибок)
7. [Оптимизации и узкие места](#оптимизации-и-узкие-места)

---

## Жизненный цикл генерации резюме

### Полный процесс от начала до конца

```
┌──────────────────────────────────────────────┐
│ Шаг 1: Инициализация модуля                  │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 1.1 Создание компонентов                     │
│  - NewStyleManager()                         │
│  - NewResumeGenerator()                      │
│  - NewFacadeManager(...)                     │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 1.2 Настройка путей                          │
│  - Определить путь к модулю                  │
│  - Построить путь к папке стилей             │
│  - StyleManager.SetStylesDirectory()         │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ Шаг 2: Выбор стиля                           │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 2.1 Сканирование стилей                      │
│  - StyleManager.GetStyles()                  │
│    ├─> ReadDir(stylesDirectory)             │
│    ├─> Для каждого файла:                   │
│    │    ├─> Открыть файл                    │
│    │    ├─> Прочитать первую строку         │
│    │    ├─> Парсить метаданные              │
│    │    └─> Сохранить в map                 │
│    └─> Вернуть map[name → StyleInfo]        │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 2.2 Форматирование выбора                    │
│  - StyleManager.FormatChoices()              │
│    └─> ["Name (author -> link)", ...]       │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 2.3 Взаимодействие с пользователем           │
│  - FacadeManager.ChooseStyle()               │
│    ├─> Показать меню (inquirer)             │
│    ├─> Пользователь выбирает вариант        │
│    ├─> Если "Создать свой" → открыть URL    │
│    └─> Иначе → сохранить selectedStyle      │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ Шаг 3: Подготовка данных                     │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 3.1 Создание GPTResumeGenerator              │
│  - NewGPTResumeGenerator(api_key, llm)       │
│  - SetResume(resume_data)                    │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 3.2 Получение описания вакансии              │
│  - job_description_text = "..."              │
│    (из внешнего источника)                   │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ Шаг 4: Генерация PDF                         │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.1 Вызов FacadeManager.PDFBase64()          │
│  ├─> Проверить selectedStyle != nil         │
│  └─> Получить путь к стилю                  │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.2 Создание временного HTML файла           │
│  - ioutil.TempFile("", "resume_*.html")      │
│  - Получить temp_html_path                   │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.3 Генерация HTML резюме                    │
│  - ResumeGenerator.CreateResume()            │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.3.1 Установка описания вакансии            │
│  - GPTResumeGenerator.                       │
│    SetJobDescriptionFromText(job_desc)       │
│    ├─> LLM вызов с summarize_prompt          │
│    ├─> Получить краткое описание             │
│    └─> Сохранить в this.jobDescription      │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.3.2 Генерация HTML секций через LLM        │
│  - GPTResumeGenerator.GenerateHTMLResume()   │
│    ├─> generateHeader()                      │
│    │    ├─> Промпт: prompt_header            │
│    │    ├─> Данные: personal_information     │
│    │    └─> LLM → HTML заголовка             │
│    ├─> generateEducationSection()            │
│    │    ├─> Промпт: prompt_education         │
│    │    ├─> Данные: education_details        │
│    │    ├─> Контекст: job_description        │
│    │    └─> LLM → HTML образования           │
│    ├─> generateWorkExperienceSection()       │
│    │    ├─> Промпт: prompt_working_exp       │
│    │    ├─> Данные: experience_details       │
│    │    ├─> Контекст: job_description        │
│    │    └─> LLM → HTML опыта                 │
│    ├─> generateSideProjectsSection()         │
│    │    ├─> Промпт: prompt_side_projects     │
│    │    ├─> Данные: projects                 │
│    │    ├─> Контекст: job_description        │
│    │    └─> LLM → HTML проектов              │
│    ├─> generateAchievementsSection()         │
│    │    ├─> Промпт: prompt_achievements      │
│    │    ├─> Данные: achievements             │
│    │    ├─> Контекст: job_description        │
│    │    └─> LLM → HTML достижений            │
│    ├─> generateCertificationsSection()       │
│    │    ├─> Промпт: prompt_certifications    │
│    │    ├─> Данные: certifications           │
│    │    ├─> Контекст: job_description        │
│    │    └─> LLM → HTML сертификатов          │
│    ├─> generateAdditionalSkillsSection()     │
│    │    ├─> Промпт: prompt_additional_skills │
│    │    ├─> Данные: languages/interests/skills │
│    │    ├─> Контекст: job_description        │
│    │    └─> LLM → HTML навыков               │
│    └─> Конкатенировать все секции → HTML    │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.3.3 Вставка в базовый шаблон               │
│  - ResumeGenerator._createResume()           │
│    ├─> Взять htmlTemplate                    │
│    ├─> Заменить $style_path на путь CSS     │
│    ├─> Заменить $markdown на HTML секций    │
│    └─> Записать в temp_html_path            │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.4 Конвертация HTML → PDF                   │
│  - HTMLToPDF(temp_html_path)                 │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.4.1 Создание WebDriver                     │
│  - CreateDriverSelenium()                    │
│    ├─> ChromeBrowserOptions()               │
│    ├─> Найти ChromeDriver                    │
│    └─> NewChromeDriver(service, options)     │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.4.2 Рендеринг и печать в PDF               │
│  - driver.Get("file:///" + abs_path)         │
│  - time.Sleep(2 seconds)                     │
│  - driver.ExecuteCDP("Page.printToPDF", {    │
│      printBackground: true,                  │
│      paperWidth: 8.27,                       │
│      paperHeight: 11.69,                     │
│      margins: ...,                           │
│      transferMode: "ReturnAsBase64"          │
│    })                                        │
│  - Получить pdf_base64 из результата         │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.4.3 Закрытие драйвера                      │
│  - driver.Quit()                             │
│    (гарантировано через defer)               │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ 4.5 Очистка                                  │
│  - os.Remove(temp_html_path)                 │
│    (гарантировано через defer)               │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│ Шаг 5: Возврат результата                    │
│  - Вернуть pdf_base64 (string)               │
└──────────────────────────────────────────────┘
```

---

## Парсинг метаданных CSS стилей

### Формат метаданных в CSS файле

**Первая строка CSS файла** должна содержать метаданные в формате:
```css
/* Style Name $ Author Link */
```

**Компоненты**:
- `/* */` - обязательные маркеры комментария CSS
- `Style Name` - имя стиля (произвольная строка)
- `$` - разделитель (обязательный символ)
- `Author Link` - ссылка на автора (URL или произвольный текст)

**Примеры валидных метаданных**:
```css
/* Josylad Blue $ https://github.com/josylad */
/* Cloyola $ https://github.com/cloyola */
/* Krishna Valliappan $ https://github.com/krishnavalliappan */
/* Samodum Bold $ https://example.com */
```

---

### Алгоритм парсинга

**Входные данные**: Путь к CSS файлу

**Выходные данные**: `(styleName string, fileName string, authorLink string, error)`

**Шаги**:

1. **Открытие файла**:
   ```
   file, err := os.Open(filePath)
   if err != nil {
       return "", "", "", err
   }
   defer file.Close()
   ```

2. **Чтение первой строки**:
   ```
   scanner := bufio.NewScanner(file)
   if !scanner.Scan() {
       return "", "", "", errors.New("Empty file")
   }
   firstLine := scanner.Text()
   ```

3. **Обрезка пробелов**:
   ```
   firstLine = strings.TrimSpace(firstLine)
   ```

4. **Проверка формата комментария**:
   ```
   if !strings.HasPrefix(firstLine, "/*") {
       return "", "", "", errors.New("Invalid format: missing /*")
   }
   if !strings.HasSuffix(firstLine, "*/") {
       return "", "", "", errors.New("Invalid format: missing */")
   }
   ```

5. **Извлечение содержимого комментария**:
   ```
   content := firstLine[2:len(firstLine)-2]  // Убрать /* и */
   content = strings.TrimSpace(content)
   ```

6. **Проверка наличия разделителя**:
   ```
   if !strings.Contains(content, "$") {
       return "", "", "", errors.New("Invalid format: missing $")
   }
   ```

7. **Разделение по $**:
   ```
   parts := strings.Split(content, "$")
   if len(parts) != 2 {
       return "", "", "", errors.New("Invalid format: multiple $")
   }
   ```

8. **Извлечение данных**:
   ```
   styleName := strings.TrimSpace(parts[0])
   authorLink := strings.TrimSpace(parts[1])
   fileName := filepath.Base(filePath)
   ```

9. **Валидация**:
   ```
   if styleName == "" {
       return "", "", "", errors.New("Empty style name")
   }
   if authorLink == "" {
       return "", "", "", errors.New("Empty author link")
   }
   ```

10. **Возврат результата**:
    ```
    return styleName, fileName, authorLink, nil
    ```

---

### Обработка ошибок парсинга

**Уровень StyleManager.GetStyles()**:

```
styles := make(map[string]StyleInfo)

for _, file := range files {
    if file.IsDir() {
        continue  // Пропустить папки
    }
    
    styleName, fileName, authorLink, err := parseStyleMetadata(filepath)
    
    if err != nil {
        logger.Warning("Пропущен файл %s: %s", fileName, err)
        continue  // Пропустить невалидный файл
    }
    
    styles[styleName] = StyleInfo{
        FileName: fileName,
        AuthorLink: authorLink,
    }
}

return styles, nil
```

**Стратегия**: Невалидные файлы пропускаются, не прерывая процесс.

---

## Интеграция с LLM

### Архитектура взаимодействия

```
resume_builder (модуль)
    ↓ использует
GPTResumeGenerator (внешний компонент)
    ↓ использует
LLM API (OpenAI, Google Gemini, и т.д.)
```

**Разделение ответственности**:
- `resume_builder` - только структура и форматирование
- `GPTResumeGenerator` - логика вызовов LLM
- LLM API - генерация контента

---

### Процесс генерации одной секции

**Пример**: Генерация секции опыта работы

**Шаг 1: Подготовка промпта**
```
Промпт = prompt_working_experience

Плейсхолдеры:
- {experience_details} = JSON данные опыта
- {job_description} = суммаризированное описание вакансии
```

**Шаг 2: Подстановка данных**
```
finalPrompt = strings.ReplaceAll(Промпт, "{experience_details}", experienceJSON)
finalPrompt = strings.ReplaceAll(finalPrompt, "{job_description}", jobDesc)
```

**Шаг 3: Создание цепочки LLM**
```
chain := CreateChain(finalPrompt)
// Создает: Prompt → LLM → StringOutputParser
```

**Шаг 4: Вызов LLM**
```
htmlOutput := chain.Invoke(context.Background())
```

**Шаг 5: Валидация ответа**
```
// LLM должен вернуть чистый HTML без обёрток
if strings.Contains(htmlOutput, "```html") {
    // Удалить markdown обёртки
    htmlOutput = cleanHTMLFromMarkdown(htmlOutput)
}
```

**Шаг 6: Возврат HTML**
```
return htmlOutput, nil
```

---

### Параллелизация вызовов LLM

**Текущая реализация** (Python): Последовательная
```
header = generateHeader()         // ~1-3 сек
education = generateEducation()   // ~1-3 сек
experience = generateExperience() // ~2-5 сек
...
// Итого: 10-20 секунд
```

**Оптимизированная реализация** (Go): Параллельная
```go
var wg sync.WaitGroup
results := make(map[string]string)
errors := make(map[string]error)
mu := sync.Mutex{}

sections := []string{"header", "education", "experience", ...}

for _, section := range sections {
    wg.Add(1)
    go func(sec string) {
        defer wg.Done()
        html, err := generateSection(sec)
        mu.Lock()
        defer mu.Unlock()
        if err != nil {
            errors[sec] = err
        } else {
            results[sec] = html
        }
    }(section)
}

wg.Wait()

// Проверить ошибки
if len(errors) > 0 {
    return "", errors
}

// Собрать секции в правильном порядке
fullHTML := results["header"] + results["education"] + ...
```

**Выигрыш по времени**: 10-20 сек → 2-5 сек (самая медленная секция)

---

### Обработка опциональных секций

**Логика**:
```go
func (g *GPTResumeGenerator) GenerateHTMLResume() (string, error) {
    var htmlParts []string
    
    // Header (обязательный)
    if g.resume.PersonalInformation != nil {
        html, err := g.generateHeader()
        if err != nil {
            return "", err
        }
        htmlParts = append(htmlParts, html)
    }
    
    // Education (опциональный)
    if g.resume.EducationDetails != nil && len(g.resume.EducationDetails) > 0 {
        html, err := g.generateEducationSection()
        if err != nil {
            return "", err
        }
        htmlParts = append(htmlParts, html)
    }
    
    // Experience (опциональный)
    if g.resume.ExperienceDetails != nil && len(g.resume.ExperienceDetails) > 0 {
        html, err := g.generateWorkExperienceSection()
        if err != nil {
            return "", err
        }
        htmlParts = append(htmlParts, html)
    }
    
    // Projects (опциональный)
    if g.resume.Projects != nil && len(g.resume.Projects) > 0 {
        html, err := g.generateSideProjectsSection()
        if err != nil {
            return "", err
        }
        htmlParts = append(htmlParts, html)
    }
    
    // ... остальные секции
    
    // Объединить все секции
    fullHTML := strings.Join(htmlParts, "\n")
    return fullHTML, nil
}
```

**Правило**: Секция генерируется только если:
1. Данные для секции существуют (не nil)
2. Данные не пустые (len > 0 для слайсов)
3. LLM вернул валидный HTML (не пустую строку)

---

## Конвертация HTML в PDF

### Архитектура конвертации

```
HTML файл (на диске)
    ↓
Selenium WebDriver
    ↓
Chrome/Chromium браузер
    ↓
Chrome DevTools Protocol
    ↓
Page.printToPDF команда
    ↓
PDF (base64)
```

---

### Детальный процесс конвертации

**Шаг 1: Подготовка file:/// URL**

```go
func HTMLToPDF(filePath string) (string, error) {
    // 1.1 Проверка существования файла
    if _, err := os.Stat(filePath); os.IsNotExist(err) {
        return "", fmt.Errorf("Файл не найден: %s", filePath)
    }
    
    // 1.2 Получение абсолютного пути
    absPath, err := filepath.Abs(filePath)
    if err != nil {
        return "", err
    }
    
    // 1.3 Построение file:/// URL
    // Windows: file:///C:/path/to/file.html
    // Unix: file:///home/user/file.html
    fileURL := "file:///" + strings.ReplaceAll(absPath, "\\", "/")
    
    // ...
}
```

**Зачем file:/// URL**:
- Chrome не может открывать файлы по обычному пути
- file:/// протокол разрешает доступ к локальным файлам
- Абсолютный путь гарантирует правильное разрешение

---

**Шаг 2: Создание WebDriver**

```go
    // 2.1 Получение опций Chrome
    options := ChromeBrowserOptions()
    
    // 2.2 Установка ChromeDriver (если нужно)
    chromeDriverPath := findOrInstallChromeDriver()
    
    // 2.3 Создание сервиса
    service, err := selenium.NewChromeService(chromeDriverPath, options)
    if err != nil {
        return "", fmt.Errorf("Failed to create service: %w", err)
    }
    
    // 2.4 Создание драйвера
    driver, err := selenium.NewRemote(service, options)
    if err != nil {
        return "", fmt.Errorf("Failed to create driver: %w", err)
    }
    
    // 2.5 Гарантированное закрытие
    defer driver.Quit()
```

**Важно**: `defer driver.Quit()` гарантирует закрытие даже при ошибке

---

**Шаг 3: Загрузка HTML**

```go
    // 3.1 Открыть HTML в браузере
    err = driver.Get(fileURL)
    if err != nil {
        return "", fmt.Errorf("Failed to load HTML: %w", err)
    }
    
    // 3.2 Подождать загрузки (рендеринг CSS, шрифтов)
    time.Sleep(2 * time.Second)
    
    // 3.3 Опционально: дождаться готовности документа
    _, err = driver.ExecuteScript("return document.readyState", nil)
    if err != nil {
        return "", err
    }
```

**Зачем Sleep**:
- CSS стили могут загружаться асинхронно
- Веб-шрифты (Google Fonts) требуют времени
- Иконки Font Awesome требуют времени
- 2 секунды - эмпирическое значение

---

**Шаг 4: Выполнение команды printToPDF**

```go
    // 4.1 Подготовка параметров PDF
    params := map[string]interface{}{
        "printBackground":          true,    // Печатать фоны
        "landscape":                false,   // Вертикальная ориентация
        "paperWidth":               8.27,    // A4 ширина (дюймы)
        "paperHeight":              11.69,   // A4 высота (дюймы)
        "marginTop":                0.8,     // Верхнее поле (дюймы)
        "marginBottom":             0.8,     // Нижнее поле (дюймы)
        "marginLeft":               0.5,     // Левое поле (дюймы)
        "marginRight":              0.5,     // Правое поле (дюймы)
        "displayHeaderFooter":      false,   // Без колонтитулов
        "preferCSSPageSize":        true,    // Использовать CSS @page
        "generateDocumentOutline":  false,   // Без оглавления
        "generateTaggedPDF":        false,   // Без accessibility тегов
        "transferMode":             "ReturnAsBase64",  // Вернуть base64
    }
    
    // 4.2 Выполнение команды
    result, err := driver.ExecuteCDP("Page.printToPDF", params)
    if err != nil {
        return "", fmt.Errorf("Failed to print PDF: %w", err)
    }
```

**Параметры PDF**:
- **A4 формат**: 8.27 × 11.69 дюймов (210 × 297 мм)
- **Margins**: Стандартные поля резюме
- **printBackground**: Критично для CSS стилей с фонами
- **preferCSSPageSize**: Позволяет CSS управлять разбивкой на страницы
- **ReturnAsBase64**: Удобно для передачи через API

---

**Шаг 5: Извлечение и возврат PDF**

```go
    // 5.1 Извлечение base64 из результата
    pdfData, ok := result["data"].(string)
    if !ok {
        return "", errors.New("Invalid PDF data format")
    }
    
    // 5.2 Валидация base64
    if len(pdfData) == 0 {
        return "", errors.New("Empty PDF data")
    }
    
    // 5.3 Возврат PDF
    return pdfData, nil
}
```

---

### Настройки Chrome для оптимизации

**Цель**: Максимальная скорость, минимум ресурсов

```go
func ChromeBrowserOptions() *selenium.ChromeOptions {
    options := selenium.NewChromeOptions()
    
    // Производительность
    options.AddArgument("--no-sandbox")                    // Без изоляции (быстрее)
    options.AddArgument("--disable-dev-shm-usage")         // Меньше памяти
    options.AddArgument("--disable-gpu")                   // Без GPU ускорения
    options.AddArgument("--single-process")                // Один процесс
    
    // Отключение ненужных функций
    options.AddArgument("--disable-extensions")            // Без расширений
    options.AddArgument("--disable-plugins")               // Без плагинов
    options.AddArgument("--disable-animations")            // Без анимаций
    options.AddArgument("--disable-cache")                 // Без кэша
    options.AddArgument("--disable-logging")               // Без логов
    
    // Размер окна
    options.AddArgument("--window-size=1200x800")          // Фиксированный размер
    options.AddArgument("--start-maximized")               // Максимизировать
    
    // Headless режим
    options.AddArgument("--headless")                      // Без GUI
    
    // Прочее
    options.AddArgument("--ignore-certificate-errors")     // Игнорировать SSL ошибки
    options.AddArgument("--disable-popup-blocking")        // Без блокировки попапов
    options.AddArgument("--no-first-run")                  // Без первого запуска
    options.AddArgument("--no-default-browser-check")      // Без проверки браузера
    
    // Отключить автоматизацию детектирование
    options.AddExperimentalOption("excludeSwitches", []string{
        "enable-automation",
        "enable-logging",
    })
    
    return options
}
```

**Результат**: Запуск Chrome за ~1-2 секунды вместо ~5-10 секунд

---

## Управление временными файлами

### Жизненный цикл временного HTML файла

```
┌─────────────────────────────────────┐
│ 1. Создание                         │
│  - ioutil.TempFile()                │
│  - Получить путь: temp_html_path    │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 2. Запись HTML                      │
│  - ResumeGenerator.CreateResume()   │
│  - Записать полный HTML документ    │
│  - Закрыть файл                     │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 3. Использование                    │
│  - HTMLToPDF(temp_html_path)        │
│  - Chrome открывает файл            │
│  - Chrome рендерит PDF              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ 4. Удаление                         │
│  - os.Remove(temp_html_path)        │
│  - Гарантировано через defer        │
└─────────────────────────────────────┘
```

---

### Безопасное управление файлами

```go
func (f *FacadeManager) PDFBase64(
    gptResumeGenerator GPTResumeGenerator,
    jobDescriptionText string,
) (string, error) {
    // 1. Валидация
    if f.selectedStyle == nil {
        return "", errors.New("Style not selected")
    }
    
    // 2. Получение пути к стилю
    stylePath, err := f.styleManager.GetStylePath(*f.selectedStyle)
    if err != nil {
        return "", err
    }
    
    // 3. Создание временного файла
    tempFile, err := ioutil.TempFile("", "resume_*.html")
    if err != nil {
        return "", fmt.Errorf("Failed to create temp file: %w", err)
    }
    tempHTMLPath := tempFile.Name()
    tempFile.Close()  // Закрыть дескриптор
    
    // 4. Гарантированное удаление (через defer)
    defer func() {
        if err := os.Remove(tempHTMLPath); err != nil {
            f.logger.Warning("Failed to remove temp file: %s", err)
        }
    }()
    
    // 5. Генерация HTML
    err = f.resumeGenerator.CreateResume(
        gptResumeGenerator,
        stylePath,
        jobDescriptionText,
        tempHTMLPath,
    )
    if err != nil {
        return "", fmt.Errorf("Failed to create resume: %w", err)
    }
    
    // 6. Конвертация в PDF
    pdfBase64, err := HTMLToPDF(tempHTMLPath)
    if err != nil {
        return "", fmt.Errorf("Failed to convert to PDF: %w", err)
    }
    
    // 7. Возврат результата (defer удалит файл)
    return pdfBase64, nil
}
```

**Гарантии**:
1. Временный файл всегда удаляется (defer)
2. Даже если произошла ошибка (defer выполняется)
3. Даже если произошла паника (defer выполняется)

---

### Обработка race condition

**Проблема**: Несколько горутин создают временные файлы

**Решение**: ioutil.TempFile() атомарно создаёт уникальные файлы

```go
// Каждый вызов создаёт уникальный файл
tempFile1, _ := ioutil.TempFile("", "resume_*.html")
// → /tmp/resume_1234567890.html

tempFile2, _ := ioutil.TempFile("", "resume_*.html")
// → /tmp/resume_0987654321.html

// Нет конфликтов даже при параллельном вызове
```

---

## Обработка ошибок

### Иерархия обработки ошибок

```
Уровень 1: FacadeManager
  ├─> Валидация входных данных
  ├─> Координация между компонентами
  └─> Обёртка ошибок из нижних уровней

Уровень 2: Компоненты (StyleManager, ResumeGenerator, Utils)
  ├─> Обработка специфичных ошибок
  ├─> Логирование
  └─> Возврат ошибок наверх

Уровень 3: Внешние системы (LLM, Selenium, FileSystem)
  └─> Нативные ошибки (проброс наверх)
```

---

### Типы ошибок и стратегии

#### 1. Ошибки валидации

**Примеры**:
- Стиль не выбран
- Пустой путь к директории
- Пустые данные резюме

**Стратегия**: Немедленный возврат ошибки
```go
if f.selectedStyle == nil {
    return "", errors.New("Style not selected. Call ChooseStyle() first")
}
```

---

#### 2. Ошибки файловой системы

**Примеры**:
- Папка стилей не найдена
- Нет прав доступа
- Ошибка записи файла

**Стратегия**: Логирование + возврат ошибки
```go
files, err := ioutil.ReadDir(s.stylesDirectory)
if err != nil {
    s.logger.Error("Failed to read styles directory: %s", err)
    return nil, fmt.Errorf("Failed to read styles directory: %w", err)
}
```

---

#### 3. Ошибки парсинга

**Примеры**:
- Неверный формат метаданных CSS
- Пустое имя стиля

**Стратегия**: Логирование warning + пропуск файла
```go
for _, file := range files {
    styleName, fileName, authorLink, err := parseStyleMetadata(path)
    if err != nil {
        s.logger.Warning("Skipping file %s: %s", file.Name(), err)
        continue  // Пропустить, не прерывать процесс
    }
    styles[styleName] = StyleInfo{...}
}
```

---

#### 4. Ошибки LLM

**Примеры**:
- API ключ недействителен
- Превышен rate limit
- Некорректный ответ LLM

**Стратегия**: Retry + fallback + возврат ошибки
```go
func (g *GPTResumeGenerator) generateSection(prompt string) (string, error) {
    const maxRetries = 3
    
    for i := 0; i < maxRetries; i++ {
        html, err := g.llm.Invoke(prompt)
        
        if err == nil {
            // Проверка валидности ответа
            if isValidHTML(html) {
                return html, nil
            }
            // Невалидный HTML - повторить попытку
            g.logger.Warning("Invalid HTML from LLM, retry %d/%d", i+1, maxRetries)
            continue
        }
        
        // Проверка типа ошибки
        if isRateLimitError(err) {
            // Подождать перед повтором
            time.Sleep(time.Duration(i+1) * time.Second)
            continue
        }
        
        // Критическая ошибка - не повторять
        return "", fmt.Errorf("LLM error: %w", err)
    }
    
    return "", errors.New("Failed to generate section after retries")
}
```

---

#### 5. Ошибки Selenium

**Примеры**:
- ChromeDriver не найден
- Ошибка запуска Chrome
- Timeout загрузки страницы

**Стратегия**: Гарантированное закрытие ресурсов + подробная ошибка
```go
func HTMLToPDF(filePath string) (string, error) {
    driver, err := CreateDriverSelenium()
    if err != nil {
        return "", fmt.Errorf("Failed to create WebDriver: %w", err)
    }
    
    // Гарантированное закрытие
    defer func() {
        if err := driver.Quit(); err != nil {
            logger.Error("Failed to quit driver: %s", err)
        }
    }()
    
    // Загрузка HTML
    if err := driver.Get(fileURL); err != nil {
        return "", fmt.Errorf("Failed to load HTML: %w", err)
    }
    
    // Выполнение CDP команды
    result, err := driver.ExecuteCDP("Page.printToPDF", params)
    if err != nil {
        return "", fmt.Errorf("Failed to print PDF via CDP: %w", err)
    }
    
    // Извлечение PDF
    pdfData, ok := result["data"].(string)
    if !ok {
        return "", errors.New("Invalid PDF data format in CDP response")
    }
    
    return pdfData, nil
}
```

---

### Логирование

**Уровни логирования**:

```go
// DEBUG: Детальная информация для отладки
logger.Debug("Parsing style metadata for file: %s", fileName)

// INFO: Обычная информация о прогрессе
logger.Info("Found %d styles in directory", len(styles))

// WARNING: Проблемы, но процесс продолжается
logger.Warning("Skipping invalid style file: %s", fileName)

// ERROR: Критические ошибки, процесс прерывается
logger.Error("Failed to create WebDriver: %s", err)
```

**Места логирования**:
- Начало/конец каждого публичного метода
- Ошибки (все уровни)
- Пропущенные файлы/данные
- Вызовы LLM (начало/конец)
- Времена выполнения (для профилирования)

---

## Оптимизации и узкие места

### Профиль производительности

**Типичное время генерации одного резюме**:

| Этап | Время | % от total |
|------|-------|------------|
| Инициализация | 0.1 сек | 1% |
| Выбор стиля (UI) | 5 сек | 20% |
| Суммаризация вакансии (LLM) | 1-2 сек | 5% |
| Генерация секций (LLM) | 10-15 сек | 50% |
| Вставка в шаблон | 0.1 сек | <1% |
| Запись HTML | 0.1 сек | <1% |
| Запуск Selenium | 2-3 сек | 10% |
| Конвертация PDF | 2-3 сек | 10% |
| **ИТОГО** | **~20-30 сек** | **100%** |

**Узкие места**:
1. 🔴 Генерация секций LLM (50%) - самое медленное
2. 🟡 Выбор стиля UI (20%) - зависит от пользователя
3. 🟡 Selenium запуск (10%) - можно оптимизировать

---

### Оптимизация #1: Параллельная генерация секций

**Текущая реализация**:
```
generateHeader()      // 1-3 сек
generateEducation()   // 1-3 сек
generateExperience()  // 2-5 сек
generateProjects()    // 1-3 сек
...
ИТОГО: 10-20 сек (последовательно)
```

**Оптимизированная реализация**:
```go
// Все секции генерируются параллельно
go generateHeader()
go generateEducation()
go generateExperience()
go generateProjects()
...

// Ждём завершения всех
waitGroup.Wait()

ИТОГО: 2-5 сек (самая медленная секция)
```

**Выигрыш**: 10-20 сек → 2-5 сек (в 3-5 раз быстрее)

---

### Оптимизация #2: Кэширование суммаризации вакансий

**Проблема**: Одна и та же вакансия суммаризируется многократно

**Решение**: Кэширование по хешу описания
```go
type VacancySummaryCache struct {
    cache map[string]string  // hash → summary
    mu    sync.RWMutex
}

func (c *VacancySummaryCache) Get(jobDesc string) (string, bool) {
    hash := sha256Hash(jobDesc)
    c.mu.RLock()
    defer c.mu.RUnlock()
    summary, ok := c.cache[hash]
    return summary, ok
}

func (c *VacancySummaryCache) Set(jobDesc string, summary string) {
    hash := sha256Hash(jobDesc)
    c.mu.Lock()
    defer c.mu.Unlock()
    c.cache[hash] = summary
}
```

**Использование**:
```go
func (g *GPTResumeGenerator) SetJobDescriptionFromText(jobDesc string) error {
    // Проверить кэш
    if summary, ok := summaryCache.Get(jobDesc); ok {
        g.jobDescription = summary
        return nil
    }
    
    // Вызвать LLM
    summary, err := g.llm.Invoke(summarizePrompt, jobDesc)
    if err != nil {
        return err
    }
    
    // Сохранить в кэш
    summaryCache.Set(jobDesc, summary)
    g.jobDescription = summary
    return nil
}
```

**Выигрыш**: 1-2 сек → 0 сек (при повторном использовании)

---

### Оптимизация #3: Переиспользование WebDriver

**Проблема**: Selenium создаётся и закрывается для каждого PDF

**Решение**: Пул WebDriver'ов
```go
type WebDriverPool struct {
    drivers chan selenium.WebDriver
    max     int
}

func NewWebDriverPool(maxDrivers int) *WebDriverPool {
    pool := &WebDriverPool{
        drivers: make(chan selenium.WebDriver, maxDrivers),
        max:     maxDrivers,
    }
    return pool
}

func (p *WebDriverPool) Get() (selenium.WebDriver, error) {
    select {
    case driver := <-p.drivers:
        return driver, nil
    default:
        // Создать новый, если пул пустой
        return CreateDriverSelenium()
    }
}

func (p *WebDriverPool) Put(driver selenium.WebDriver) {
    select {
    case p.drivers <- driver:
        // Вернули в пул
    default:
        // Пул полон, закрыть драйвер
        driver.Quit()
    }
}
```

**Использование**:
```go
func HTMLToPDF(filePath string) (string, error) {
    driver, err := driverPool.Get()
    if err != nil {
        return "", err
    }
    defer driverPool.Put(driver)  // Вернуть в пул
    
    // Использовать driver...
}
```

**Выигрыш**: 2-3 сек → 0.5-1 сек (для повторных конвертаций)

---

### Оптимизация #4: Альтернативы Selenium

**Проблема**: Selenium тяжелый и медленный

**Альтернатива 1: chromedp (Go библиотека)**
```go
import "github.com/chromedp/chromedp"

func HTMLToPDF(filePath string) ([]byte, error) {
    ctx, cancel := chromedp.NewContext(context.Background())
    defer cancel()
    
    var pdfBuf []byte
    err := chromedp.Run(ctx,
        chromedp.Navigate("file:///" + filePath),
        chromedp.WaitReady("body"),
        chromedp.ActionFunc(func(ctx context.Context) error {
            var err error
            pdfBuf, _, err = page.PrintToPDF().
                WithPrintBackground(true).
                WithPaperWidth(8.27).
                WithPaperHeight(11.69).
                Do(ctx)
            return err
        }),
    )
    return pdfBuf, err
}
```

**Выигрыш**: 2-3 сек → 0.5-1 сек (нативная Go библиотека)

**Альтернатива 2: wkhtmltopdf (CLI утилита)**
```go
func HTMLToPDF(filePath string) ([]byte, error) {
    cmd := exec.Command("wkhtmltopdf",
        "--page-size", "A4",
        "--margin-top", "20mm",
        "--margin-bottom", "20mm",
        "--margin-left", "13mm",
        "--margin-right", "13mm",
        filePath, "-")  // stdout
    
    return cmd.Output()
}
```

**Выигрыш**: 2-3 сек → 0.2-0.5 сек (очень быстро)

---

### Итоговая производительность с оптимизациями

| Этап | До | После | Оптимизация |
|------|----|----- |-------------|
| Генерация секций | 10-15 сек | 2-5 сек | Параллелизация |
| Суммаризация | 1-2 сек | 0 сек | Кэш (повтор) |
| Запуск Selenium | 2-3 сек | 0.5 сек | Пул/chromedp |
| Конвертация PDF | 2-3 сек | 0.5 сек | chromedp |
| **ИТОГО** | **20-30 сек** | **5-10 сек** | **3-5x быстрее** |

---

## Заключение

Модуль `resume_builder` реализует сложный процесс генерации резюме через несколько этапов:
1. Парсинг метаданных стилей
2. Интерактивный выбор стиля
3. Генерация HTML секций через LLM
4. Вставка в базовый шаблон
5. Конвертация в PDF через Chrome

**Ключевые особенности реализации**:
- Модульная архитектура (разделение ответственности)
- Гарантированное управление ресурсами (defer)
- Параллелизация вызовов LLM (потенциал)
- Кэширование повторяющихся операций (потенциал)
- Альтернативные методы конвертации PDF (chromedp, wkhtmltopdf)

**Готовность к Go реализации**: ✅ Высокая

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Статус**: Готово к реализации на Go

