# JobApplier - Обработка вопросов работодателя

## Назначение

Данный документ описывает логику обработки различных типов вопросов работодателя через Selenium WebDriver и интеграцию с LLM.

---

## Типы вопросов

### 1. Radio вопросы
Вопросы с выбором одного варианта ответа из списка.

**Селектор**: `[data-qa="radio-container"]`

### 2. Checkbox вопросы
Вопросы с выбором нескольких вариантов ответа.

**Селектор**: `[data-qa="checkbox-container"]`

### 3. Текстовые вопросы
Открытые вопросы, требующие текстового ответа.

**Селектор**: `textarea`

---

## Методы обработки

### handle_question

**Сигнатура**:
```
handle_question(question: WebElement) -> (Bool, String)
```

**Назначение**: Определить тип вопроса и вызвать соответствующий обработчик

**Входные параметры**:
- `question` - WebElement вопроса (элемент с `data-qa="task-body"`)

**Возвращаемое значение**:
- (Bool, String) - (успех, сообщение об ошибке)

**Логика**:
1. **Проверка на Radio вопрос**:
   - radio_fields = question.find_elements(xpath=".//*[@data-qa='radio-container']")
   - Если radio_fields НЕ пусто:
     - Вернуть _handle_radio_question(question, radio_fields)

2. **Проверка на Checkbox вопрос**:
   - checkbox_fields = question.find_elements(xpath=".//*[@data-qa='checkbox-container']")
   - Если checkbox_fields НЕ пусто:
     - Вернуть _handle_checkbox_question(question, checkbox_fields)

3. **Проверка на текстовый вопрос**:
   - text_fields = question.find_elements(xpath=".//textarea")
   - Если text_fields НЕ пусто:
     - Вернуть _handle_textbox_question(question, text_fields[0])

4. **Вопрос не распознан**:
   - output = f"Не найдено поля для ввода: {question.text}"
   - Вывести ERROR в лог
   - Вернуть (false, output)

---

### _handle_radio_question

**Сигнатура**:
```
_handle_radio_question(question: WebElement, radio_fields: List[WebElement]) -> (Bool, String)
```

**Назначение**: Обработать вопрос с единственным выбором

**Входные параметры**:
- `question` - элемент вопроса
- `radio_fields` - список radio кнопок

**Возвращаемое значение**:
- (Bool, String) - (успех, сообщение об ошибке)

**Логика**:
1. **Прокрутка к вопросу**:
   - scroll_slow(driver, question)

2. **Извлечение текста вопроса**:
   - question_text = question.text
   - Вывести INFO: f"Найден radio вопрос: {question_text}"

3. **Извлечение вариантов ответа**:
   - options = []
   - Для каждого radio_field в radio_fields:
     - parent = radio_field.find_element(xpath="../..")
     - option_text = parent.text
     - options.append(option_text)
   - options.append("No info") // опция "нет информации"

4. **Получение ответа от LLM**:
   - answer = gpt_answerer.select_one_answer_from_options(question_text, options)

5. **Поиск и выбор варианта**:
   - Для каждого (idx, option) в enumerate(options):
     - Если option == answer И option != "No info":
       - scroll_slow(driver, radio_fields[idx])
       - radio_fields[idx].click()
       - Пауза
       - Вернуть (true, "")

6. **Подходящий ответ не найден**:
   - output = f"Не найден подходящий ответ: {question.text}"
   - Вывести WARNING в лог
   - Вернуть (false, output)

---

### _handle_checkbox_question

**Сигнатура**:
```
_handle_checkbox_question(question: WebElement, checkbox_fields: List[WebElement]) -> (Bool, String)
```

**Назначение**: Обработать вопрос с множественным выбором

**Входные параметры**:
- `question` - элемент вопроса
- `checkbox_fields` - список checkbox элементов

**Возвращаемое значение**:
- (Bool, String) - (успех, сообщение об ошибке)

**Логика**:
1. **Прокрутка к вопросу**:
   - scroll_slow(driver, question)

2. **Извлечение текста вопроса**:
   - question_text = question.text
   - Вывести INFO: f"Найден checkbox вопрос: {question_text}"

3. **Извлечение вариантов ответа**:
   - options = []
   - Для каждого checkbox_field в checkbox_fields:
     - parent = checkbox_field.find_element(xpath="../..")
     - option_text = parent.text
     - options.append(option_text)
   - options.append("No info")

4. **Получение ответов от LLM**:
   - answers = gpt_answerer.select_many_answers_from_options(question_text, options)
   - // answers - список выбранных вариантов

5. **Выбор всех подходящих вариантов**:
   - result = false
   - Для каждого (idx, option) в enumerate(options):
     - Если option в answers И option != "No info":
       - scroll_slow(driver, checkbox_fields[idx])
       - checkbox_fields[idx].click()
       - result = true
       - Пауза

6. **Проверка результата**:
   - Если result == true:
     - Вернуть (true, "")
   - Иначе:
     - output = f"Не найден подходящий ответ: {question.text}"
     - Вывести WARNING в лог
     - Вернуть (false, output)

---

### _handle_textbox_question

**Сигнатура**:
```
_handle_textbox_question(question: WebElement, text_field: WebElement) -> (Bool, String)
```

**Назначение**: Обработать текстовый вопрос

**Входные параметры**:
- `question` - элемент вопроса
- `text_field` - textarea элемент для ввода

**Возвращаемое значение**:
- (Bool, String) - (успех, сообщение об ошибке)

**Логика**:
1. **Прокрутка к вопросу**:
   - scroll_slow(driver, question)

2. **Извлечение текста вопроса**:
   - question_text = question.text
   - Вывести INFO: f"Найден текстовый вопрос: {question_text}"

3. **Поиск в кэше**:
   - existing_answer = null
   - sanitized_question = _sanitize_text(question_text)
   - Для каждого answer в seen_answers:
     - Если _sanitize_text(answer["question"]) == sanitized_question:
       - existing_answer = answer["answer"]
       - Вывести INFO: f"Найден готовый ответ: {existing_answer}"
       - Выйти из цикла

4. **Получение ответа**:
   - Если existing_answer:
     - answer = existing_answer
     - Вывести INFO: "Используем готовый ответ"
   - Иначе:
     - **Генерация нового ответа**:
       - answer = gpt_answerer.answer_question_textual_wide_range(question_text)
       
       - **Проверка на неопределенный тип**:
         - Если answer.startswith("Вопрос не принадлежит ни к одной из известных тем"):
           - output = f"Не смогли определить тип вопроса: {question_text}"
           - Вывести WARNING в лог
           - Вернуть (false, output)
       
       - **Проверка на отсутствие информации**:
         - Если "no info" в answer.lower() ИЛИ
              "нет информации" в answer.lower() ИЛИ
              "не указан" в answer.lower():
           - output = f"Не смогли ответить на вопрос: {question_text}"
           - Вывести WARNING в лог
           - Вернуть (false, output)
       
       - **Сохранение в кэш**:
         - Вывести INFO: f"Сгенерирован ответ: {answer}"
         - seen_answers.append({"question": question_text, "answer": answer})
         - _save_data_to_yaml(seen_answers, "answers.yaml")
         - Вывести INFO: "Ответ сохранен в YAML"

5. **Деанонимизация и ввод**:
   - Пауза
   - answer = resume_component.deanonymize_personal_information(answer)
   - enter_text(text_field, answer)
   - Вывести INFO: "Ответ введен"

6. Вернуть (true, "")

---

## Вспомогательные методы для Selenium

### scroll_slow

**Сигнатура**:
```
scroll_slow(driver: WebDriver, element: WebElement) -> void
```

**Назначение**: Плавная прокрутка к элементу

**Логика**:
1. Получить координаты element
2. Рассчитать целевую позицию скролла:
   - target = element.location.y - viewport_height/2
3. Выполнить плавный скролл (JavaScript):
   - window.scrollTo({top: target, behavior: 'smooth'})
4. Пауза для завершения анимации

---

### enter_text

**Сигнатура**:
```
enter_text(element: WebElement, text: String) -> void
```

**Назначение**: Безопасный ввод текста с очисткой поля

**Логика**:
1. Получить текущее значение:
   - current_text = element.get_attribute("value")
2. Очистить поле (отправка BACKSPACE):
   - Для каждого символа в current_text:
     - element.send_keys(Keys.BACKSPACE)
3. Ввести новый текст:
   - element.send_keys(text)
4. Пауза

---

## Интеграция с LLM

### Методы GPTAnswerer для вопросов

#### select_one_answer_from_options

**Сигнатура**:
```
select_one_answer_from_options(question: String, options: List[String]) -> String
```

**Назначение**: Выбрать один вариант из списка

**Входные параметры**:
- `question` - текст вопроса
- `options` - список доступных вариантов

**Возвращаемое значение**:
- String - выбранный вариант (один из options)

**Логика работы LLM**:
1. Сформировать промпт:
   ```
   Вопрос: {question}
   Варианты:
   1. {option1}
   2. {option2}
   ...
   N. No info
   
   Выбери ОДИН наиболее подходящий вариант на основе резюме.
   Если нет подходящего - выбери "No info".
   Верни ТОЛЬКО текст выбранного варианта.
   ```
2. Отправить запрос в LLM
3. Вернуть ответ

---

#### select_many_answers_from_options

**Сигнатура**:
```
select_many_answers_from_options(question: String, options: List[String]) -> List[String]
```

**Назначение**: Выбрать несколько вариантов из списка

**Входные параметры**:
- `question` - текст вопроса
- `options` - список доступных вариантов

**Возвращаемое значение**:
- List[String] - список выбранных вариантов

**Логика работы LLM**:
1. Сформировать промпт:
   ```
   Вопрос: {question}
   Варианты:
   1. {option1}
   2. {option2}
   ...
   N. No info
   
   Выбери ВСЕ подходящие варианты на основе резюме.
   Если нет подходящих - верни ["No info"].
   Верни список текстов выбранных вариантов в JSON формате.
   ```
2. Отправить запрос в LLM
3. Распарсить JSON ответ
4. Вернуть список

---

#### answer_question_textual_wide_range

**Сигнатура**:
```
answer_question_textual_wide_range(question: String) -> String
```

**Назначение**: Ответить на текстовый вопрос

**Входные параметры**:
- `question` - текст вопроса

**Возвращаемое значение**:
- String - текстовый ответ

**Логика работы LLM**:
1. Определить тип вопроса (категория):
   - work_experience
   - education
   - salary_expectations
   - availability
   - certifications
   - languages
   - skills
   - projects
   - achievements
   - general_knowledge
   - other

2. Сформировать промпт в зависимости от типа:
   ```
   Вопрос: {question}
   Резюме: {resume_text}
   
   Ответь на вопрос на основе резюме.
   Если информации нет - верни "No info".
   Ответ должен быть кратким и конкретным.
   ```

3. Отправить запрос в LLM

4. Обработать ответ:
   - Если ответ содержит "No info" → вернуть как есть
   - Иначе → вернуть ответ

5. Вернуть результат

---

## Обработка ошибок

### Возможные ошибки

**Selenium ошибки**:
- `NoSuchElementException` - элемент не найден
- `ElementNotInteractableException` - элемент недоступен для взаимодействия
- `StaleElementReferenceException` - элемент устарел

**Стратегия обработки**:
1. При NoSuchElementException:
   - Вывести WARNING в лог
   - Вернуть (false, "Элемент не найден")

2. При ElementNotInteractableException:
   - Пауза 1-2 сек
   - Повторить попытку
   - Если не помогло: вернуть (false, "Элемент недоступен")

3. При StaleElementReferenceException:
   - Повторно найти элемент
   - Повторить операцию
   - Если не помогло: вернуть (false, "Элемент устарел")

---

## Кэширование ответов

### Формат кэша (answers.yaml)

```yaml
- question: "Опишите ваш опыт работы с Python"
  answer: "У меня 5 лет опыта..."

- question: "Какая у вас зарплатная ожидания?"
  answer: "От 200000 руб"
```

### Логика работы с кэшем

**Поиск в кэше**:
1. Санитизировать вопрос:
   - Привести к нижнему регистру
   - Убрать спецсимволы
   - Удалить лишние пробелы
2. Сравнить с вопросами в кэше
3. Если найдено точное совпадение:
   - Использовать сохраненный ответ
4. Иначе:
   - Запросить LLM
   - Сохранить в кэш

**Сохранение в кэш**:
1. Добавить в список seen_answers
2. Сохранить весь список в answers.yaml
3. Вывести INFO в лог

---

## Производительность

### Оптимизации

1. **Кэширование ответов**:
   - Избегает повторных запросов к LLM
   - Экономит время и деньги

2. **Пакетная обработка**:
   - Все вопросы обрабатываются за один визит на страницу

3. **Плавная прокрутка**:
   - Уменьшает вероятность ошибок взаимодействия

### Узкие места

1. **LLM запросы** - самые медленные (2-5 сек)
2. **Selenium операции** - средние (0.5-1 сек)
3. **Прокрутка и анимации** - быстрые (0.1-0.3 сек)

---

**Версия документа**: 1.0  
**Дата**: 22 октября 2025  
**Назначение**: Спецификация обработки вопросов для реализации на Go

