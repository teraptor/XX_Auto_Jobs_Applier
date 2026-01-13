# API методы и контракты HeadHunter (api.hh.ru)

## Оглавление
1. [Обзор](#обзор)
2. [Аутентификация и токены](#аутентификация-и-токены)
3. [Работа с пользователем](#работа-с-пользователем)
4. [Работа с резюме](#работа-с-резюме)
5. [Поиск вакансий](#поиск-вакансий)
6. [Отправка откликов](#отправка-откликов)
7. [Обработка ошибок](#обработка-ошибок)
8. [Последовательность реализации](#последовательность-реализации)

---

## Обзор

Проект использует официальное **HeadHunter API** для автоматизации поиска работы и отправки откликов.

**Base URL:** `https://api.hh.ru`

**Аутентификация:** OAuth 2.0 с использованием Bearer token

**Документация API:** https://github.com/hhru/api/tree/master/docs

---

## Аутентификация и токены

### Шаг 1: Обновление токенов

#### Эндпоинт
```
POST https://api.hh.ru/token
```

#### Когда используется
- При истечении срока действия `access_token` (error: `token_expired`)
- Перед началом работы для обеспечения актуальности токенов

#### Request Body (form-data)
```
grant_type: "refresh_token"
refresh_token: "<refresh_token>"
```

#### Response 200 (Success)
```json
{
  "access_token": "new_access_token_string",
  "refresh_token": "new_refresh_token_string",
  "token_type": "bearer",
  "expires_in": 1209600
}
```

#### Response 400 (Error)
```json
{
  "error": "invalid_grant",
  "error_description": "token not expired"
}
```

или

```json
{
  "error": "invalid_request",
  "error_description": "refresh_token is missing"
}
```

#### Логика из проекта
```python
# src/job_manager/api.py (строки 62-94)

def refress_access_token(self) -> None:
    """Обновление токена доступа к hh API"""
    logger.info("Пытаемся обновить токен доступа")
    url = "https://api.hh.ru/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": self.refresh_token,
    }
    response = requests.post(url, data=data)
    tokens = response.json()

    if "access_token" in tokens and "refresh_token" in tokens:
        logger.info("Токен доступа обновлен")
        self.secrets["access_token"] = tokens["access_token"]
        self.secrets["refresh_token"] = tokens["refresh_token"]
        self.access_token = self.secrets["access_token"]
        self.refresh_token = self.secrets["refresh_token"]
        logger.info("Записываем обновленные токены доступа в файл secrets.yaml")
        self._update_secretes()
        return

    if "error" in tokens:
        raise ValueError(f"Ошибка во время обновления токена: {tokens['error']}")

    if "errors" in tokens:
        raise ValueError(f"Ошибки во время обновления токена: {tokens['errors']}")

    if "error_description" in tokens:
        if tokens["error_description"] != "token not expired":
            raise ValueError(f"Ошибка во время обновления токена: {tokens}")
        logger.info("Обновление токена доступа не требуется")

    raise ValueError(f"Неизвестная ошибка во время обновления токена: {tokens}")
```

#### Реализация в Go
```go
// core/clients/hh_client.go

func (c *HHClient) RefreshAccessToken(refreshToken string) (*TokenResponse, error) {
    data := url.Values{}
    data.Set("grant_type", "refresh_token")
    data.Set("refresh_token", refreshToken)
    
    resp, err := http.PostForm("https://api.hh.ru/token", data)
    if err != nil {
        return nil, fmt.Errorf("post request failed: %w", err)
    }
    defer resp.Body.Close()
    
    var result TokenResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("decode response: %w", err)
    }
    
    if result.Error != "" {
        if result.ErrorDescription == "token not expired" {
            log.Println("Token refresh not required")
            return nil, nil
        }
        return nil, fmt.Errorf("token refresh error: %s - %s", result.Error, result.ErrorDescription)
    }
    
    return &result, nil
}

type TokenResponse struct {
    AccessToken      string `json:"access_token"`
    RefreshToken     string `json:"refresh_token"`
    TokenType        string `json:"token_type"`
    ExpiresIn        int    `json:"expires_in"`
    Error            string `json:"error,omitempty"`
    ErrorDescription string `json:"error_description,omitempty"`
}
```

---

## Работа с пользователем

### Шаг 2: Получение информации о текущем пользователе

#### Эндпоинт
```
GET https://api.hh.ru/me
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Когда используется
- При инициализации приложения, если `user_id` не сохранен
- Для получения основной информации о пользователе

#### Response 200
```json
{
  "id": "12345678",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": "Иванович",
  "is_admin": false,
  "is_applicant": true,
  "is_employer": false,
  "email": "user@example.com",
  "counters": {
    "unread_negotiations": 5,
    "new_resume_views": 12
  }
}
```

#### Логика из проекта
```python
# src/job_manager/api.py (строки 114-120)

def _get_user_id(self) -> str:
    """Получение ID пользователя на hh.ru"""
    url = "https://api.hh.ru/me"
    response = self.api_request(url, type_="get")
    self.secrets["user_id"] = response["id"]
    logger.info("Получили ID пользователя на сайте hh.ru, обновляем файл настроек поиска")
    self._update_secretes()
```

#### Реализация в Go
```go
func (c *HHClient) GetCurrentUser(accessToken string) (*User, error) {
    req, err := http.NewRequest("GET", "https://api.hh.ru/me", nil)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var user User
    if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
        return nil, err
    }
    
    return &user, nil
}

type User struct {
    ID         string `json:"id"`
    FirstName  string `json:"first_name"`
    LastName   string `json:"last_name"`
    MiddleName string `json:"middle_name"`
    Email      string `json:"email"`
}
```

---

## Работа с резюме

### Шаг 3.1: Получение списка резюме пользователя

#### Эндпоинт
```
GET https://api.hh.ru/resumes/mine
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Когда используется
- При выборе резюме для отправки откликов
- Для отображения списка доступных резюме пользователю

#### Response 200
```json
{
  "items": [
    {
      "id": "0123456789abcdef",
      "title": "Backend Developer",
      "url": "https://api.hh.ru/resumes/0123456789abcdef",
      "created_at": "2023-01-15T10:30:00+0300",
      "updated_at": "2023-10-20T14:45:00+0300",
      "status": {
        "id": "published",
        "name": "опубликовано"
      },
      "access": {
        "type": {
          "id": "clients",
          "name": "видно всем компаниям, зарегистрированным на HeadHunter"
        }
      },
      "next_publish_at": "2023-10-20T18:00:00+0300",
      "total_views": 245,
      "new_views": 12
    }
  ]
}
```

#### Логика из проекта
```python
# src/job_manager/resume_scraper.py (строки 57-87)

def get_id_of_selected_resume(self) -> Tuple[str, List[str]]:
    """Получить ID нужного резюме"""
    url = "https://api.hh.ru/resumes/mine"
    resumes = self.api.api_request(url)["items"]
    # найти среди резюме наиболее схожее по названию с должностью, что указана в настройках
    resume_titles = [r["title"] if r["title"] else "" for r in resumes]
    # если не задана должность - возвращаем первое резюме
    if not self.job_title:
        # если в параметрах поиска есть resume_id - используем резюме с этим id
        if self.resume_id:
            for i, resume in enumerate(resumes):
                if resume["id"] == self.resume_id:
                    self.job_title = resume_titles[i]
                    return resume["id"], resume_titles
        self.resume_id = resumes[0]["id"]
        self.job_title = resume_titles[0]
        return resumes[0]["id"], resume_titles
    distances = [
        (i, distance(self.job_title.lower(), title.lower()))
        for i, title in enumerate(resume_titles)
    ]
    best_titile_idx = min(distances, key=lambda x: x[1])[0]
    best_match_resume = resumes[best_titile_idx]
    best_match_resume_title = resume_titles[best_titile_idx]
    resume_id = best_match_resume["id"]
    logger.info(
        f"Найден наиболее подходящий вариант резюме для должности {self.job_title}: {best_match_resume_title}"
    )
    self.job_title = best_match_resume_title
    self.resume_id = resume_id
    return resume_id, resume_titles
```

#### Реализация в Go
```go
func (c *HHClient) GetUserResumes(accessToken string) (*ResumesResponse, error) {
    req, err := http.NewRequest("GET", "https://api.hh.ru/resumes/mine", nil)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result ResumesResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, err
    }
    
    return &result, nil
}

type ResumesResponse struct {
    Items []ResumeShort `json:"items"`
}

type ResumeShort struct {
    ID            string    `json:"id"`
    Title         string    `json:"title"`
    URL           string    `json:"url"`
    CreatedAt     time.Time `json:"created_at"`
    UpdatedAt     time.Time `json:"updated_at"`
    NextPublishAt time.Time `json:"next_publish_at"`
    TotalViews    int       `json:"total_views"`
    NewViews      int       `json:"new_views"`
}
```

---

### Шаг 3.2: Получение детальной информации о резюме

#### Эндпоинт
```
GET https://api.hh.ru/resumes/{resume_id}
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Когда используется
- Для получения полной информации о резюме
- Перед отправкой откликов для сбора данных о кандидате

#### Response 200 (сокращенно, основные поля)
```json
{
  "id": "0123456789abcdef",
  "title": "Backend Developer",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": "Иванович",
  "age": 30,
  "birth_date": "1993-05-15",
  "gender": {
    "id": "male",
    "name": "Мужской"
  },
  "area": {
    "id": "1",
    "name": "Москва",
    "url": "https://api.hh.ru/areas/1"
  },
  "metro": {
    "id": "6.14",
    "name": "Сокол",
    "lat": 55.805452,
    "lng": 37.515214
  },
  "citizenship": [
    {
      "id": "113",
      "name": "Россия"
    }
  ],
  "work_ticket": [
    {
      "id": "113",
      "name": "Разрешение на работу в России"
    }
  ],
  "relocation": {
    "type": {
      "id": "living_or_relocation",
      "name": "живу или готов переехать"
    },
    "area": []
  },
  "business_trip_readiness": {
    "id": "ready",
    "name": "Готов к командировкам"
  },
  "contact": [
    {
      "type": {
        "id": "cell",
        "name": "Мобильный телефон"
      },
      "preferred": true,
      "value": {
        "country": "7",
        "city": "926",
        "number": "1234567",
        "formatted": "+7 (926) 123-45-67"
      }
    },
    {
      "type": {
        "id": "email",
        "name": "Эл. почта"
      },
      "preferred": false,
      "value": "ivanov@example.com"
    }
  ],
  "site": [
    {
      "type": {
        "id": "other",
        "name": "Другое"
      },
      "url": "https://github.com/ivanov"
    },
    {
      "type": {
        "id": "linkedin",
        "name": "LinkedIn"
      },
      "url": "https://linkedin.com/in/ivanov"
    }
  ],
  "salary": {
    "amount": 200000,
    "currency": "RUR"
  },
  "professional_roles": [
    {
      "id": "96",
      "name": "Программист, разработчик"
    }
  ],
  "employments": [
    {
      "id": "full",
      "name": "Полная занятость"
    }
  ],
  "schedules": [
    {
      "id": "fullDay",
      "name": "Полный день"
    },
    {
      "id": "remote",
      "name": "Удаленная работа"
    }
  ],
  "travel_time": {
    "id": "any",
    "name": "Не имеет значения"
  },
  "has_vehicle": false,
  "driver_license_types": [],
  "skills": "Опытный backend разработчик со знанием Go, Python, PostgreSQL...",
  "skill_set": [
    "Go",
    "Python",
    "PostgreSQL",
    "Redis",
    "Docker",
    "Kubernetes"
  ],
  "language": [
    {
      "id": "rus",
      "name": "Русский",
      "level": {
        "id": "native",
        "name": "Родной"
      }
    },
    {
      "id": "eng",
      "name": "Английский",
      "level": {
        "id": "b2",
        "name": "B2 — Средне-продвинутый"
      }
    }
  ],
  "experience": [
    {
      "company": "Tech Company LLC",
      "company_id": null,
      "area": {
        "id": "1",
        "name": "Москва"
      },
      "company_url": "https://techcompany.ru",
      "employer": {
        "id": "12345",
        "name": "Tech Company LLC"
      },
      "position": "Senior Backend Developer",
      "start": "2020-03",
      "end": null,
      "description": "Разработка микросервисной архитектуры...",
      "industries": [
        {
          "id": "7",
          "name": "Информационные технологии"
        }
      ]
    }
  ],
  "total_experience": {
    "months": 84
  },
  "education": {
    "level": {
      "id": "higher",
      "name": "Высшее"
    },
    "primary": [
      {
        "name": "МГУ им. М.В. Ломоносова",
        "name_id": "123",
        "organization": "Факультет ВМК",
        "result": "Программная инженерия",
        "result_id": null,
        "year": 2015
      }
    ],
    "additional": [],
    "attestation": [],
    "elementary": []
  },
  "certificate": [
    {
      "title": "AWS Certified Solutions Architect",
      "achieved_at": "2022-06",
      "type": "custom",
      "owner": null,
      "url": "https://..."
    }
  ],
  "recommendation": [],
  "next_publish_at": "2023-10-20T18:00:00+0300",
  "created_at": "2023-01-15T10:30:00+0300",
  "updated_at": "2023-10-20T14:45:00+0300"
}
```

#### Логика из проекта
```python
# src/job_manager/resume_scraper.py (строки 89-93)

def get_selected_resume_info(self, resume_id: str) -> Dict[str, Any]:
    """Получить информацию о нужном резюме"""
    url = f"https://api.hh.ru/resumes/{resume_id}"
    resume_info = self.api.api_request(url)
    return resume_info
```

#### Реализация в Go
```go
func (c *HHClient) GetResume(resumeID, accessToken string) (*Resume, error) {
    url := fmt.Sprintf("https://api.hh.ru/resumes/%s", resumeID)
    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var resume Resume
    if err := json.NewDecoder(resp.Body).Decode(&resume); err != nil {
        return nil, err
    }
    
    return &resume, nil
}

// Полная структура Resume - см. Response выше
```

---

### Шаг 3.3: Поднятие резюме в поиске

#### Эндпоинт
```
POST https://api.hh.ru/resumes/{resume_id}/publish
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Когда используется
- Перед началом рассылки откликов
- Только если прошло >= 4 часов с последнего поднятия (проверяется по полю `next_publish_at`)

#### Response 204 (Success - No Content)
Пустой ответ, успешное поднятие

#### Response 429 (Too Many Requests)
```json
{
  "errors": [
    {
      "type": "too_many_requests",
      "value": "resume_publication"
    }
  ]
}
```

#### Логика из проекта
```python
# src/job_manager/resume_scraper.py (строки 95-107)

def raise_resume(self, resume_id: str, resume_info: Dict[str, Any]) -> None:
    """Поднять резюме в поиске"""
    # для начала проверяем, что резюме можно поднять
    # (прошло как минимум 4 часа с последнего подъема резюме)
    logger.info("Проверяем возможность подъема резюме")
    next_publish_at = resume_info["next_publish_at"]
    next_publish_at = datetime.fromisoformat(next_publish_at).replace(tzinfo=None)
    dt_now = datetime.now()
    # если поднять можно - поднимаем
    if dt_now >= next_publish_at:
        url = f"https://api.hh.ru/resumes/{resume_id}/publish"
        self.api.api_request(url, type_="post")
        logger.info("Резюме успешно поднято")
```

#### Реализация в Go
```go
func (c *HHClient) PublishResume(resumeID, accessToken string, nextPublishAt time.Time) error {
    // Проверка, можно ли поднять резюме
    if time.Now().Before(nextPublishAt) {
        return fmt.Errorf("resume can be published only after %v", nextPublishAt)
    }
    
    url := fmt.Sprintf("https://api.hh.ru/resumes/%s/publish", resumeID)
    req, err := http.NewRequest("POST", url, nil)
    if err != nil {
        return err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode == 204 {
        log.Println("Resume published successfully")
        return nil
    }
    
    if resp.StatusCode == 429 {
        return fmt.Errorf("too many requests: cannot publish resume yet")
    }
    
    return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
}
```

---

## Поиск вакансий

### Шаг 4.1: Поиск вакансий, похожих на резюме

#### Эндпоинт
```
GET https://api.hh.ru/resumes/{resume_id}/similar_vacancies
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Query Parameters
```
page: int (default=0, номер страницы)
per_page: int (default=20, max=100, количество на странице)
+ все параметры из search_config (experience, employment, schedule, area, salary и т.д.)
```

#### Когда используется
- **Первая фаза** поиска вакансий
- HH.ru API автоматически подбирает вакансии, похожие на данное резюме

#### Response 200
```json
{
  "found": 150,
  "pages": 15,
  "per_page": 10,
  "page": 0,
  "items": [
    {
      "id": "12345678",
      "premium": false,
      "name": "Backend Developer (Go)",
      "department": null,
      "has_test": false,
      "response_letter_required": true,
      "area": {
        "id": "1",
        "name": "Москва",
        "url": "https://api.hh.ru/areas/1"
      },
      "salary": {
        "from": 200000,
        "to": 350000,
        "currency": "RUR",
        "gross": false
      },
      "type": {
        "id": "open",
        "name": "Открытая"
      },
      "address": {
        "city": "Москва",
        "street": "Красная площадь",
        "building": "1",
        "description": null,
        "lat": 55.753215,
        "lng": 37.622504,
        "raw": "Москва, Красная площадь, 1",
        "metro": {
          "station_name": "Охотный Ряд",
          "line_name": "Сокольническая",
          "station_id": "1.1",
          "line_id": "1",
          "lat": 55.75722,
          "lng": 37.61556
        },
        "metro_stations": []
      },
      "employer": {
        "id": "1234",
        "name": "Tech Company LLC",
        "url": "https://api.hh.ru/employers/1234",
        "alternate_url": "https://hh.ru/employer/1234",
        "logo_urls": {
          "90": "https://...",
          "240": "https://..."
        },
        "vacancies_url": "https://api.hh.ru/vacancies?employer_id=1234",
        "accredited_it_employer": true,
        "trusted": true
      },
      "snippet": {
        "requirement": "Опыт разработки на <highlighttext>Go</highlighttext> от 3 лет. Знание PostgreSQL, Redis...",
        "responsibility": "Разработка и поддержка микросервисов. Оптимизация производительности..."
      },
      "contacts": null,
      "schedule": {
        "id": "remote",
        "name": "Удаленная работа"
      },
      "working_days": [],
      "working_time_intervals": [],
      "working_time_modes": [],
      "accept_temporary": false,
      "professional_roles": [
        {
          "id": "96",
          "name": "Программист, разработчик"
        }
      ],
      "accept_incomplete_resumes": false,
      "experience": {
        "id": "between3And6",
        "name": "От 3 до 6 лет"
      },
      "employment": {
        "id": "full",
        "name": "Полная занятость"
      },
      "adv_response_url": null,
      "is_adv_vacancy": false,
      "alternate_url": "https://hh.ru/vacancy/12345678"
    }
  ]
}
```

#### Логика из проекта
```python
# src/job_manager/job_applier.py (строки 119-153)

def search_vacancies(self, page_num: int = 0) -> List[Any]:
    """Начать поиск"""
    search_params = {"page": page_num, "per_page": 10}
    vacancies = []
    for key, value in self.search_component.search_params.items():
        if value:
            search_params[key] = value
    # сначала ищем вакансии, похожие на данное резюме,
    if self.resume_vac_page_num == -1:
        resume_vacancies = self.api.api_request(
            f"https://api.hh.ru/resumes/{self.resume_id}/similar_vacancies",
            params=search_params,
        )
        # если не нашли - записываем общее количество страниц с вакансиями, похожими на резюме
        if len(resume_vacancies["items"]) == 0:
            self.resume_vac_page_num = page_num
        else:
            vacancies = resume_vacancies["items"]
    # обращаемся сюда только в случае, если только начали поиск или
    # уже обработали все вакансии, похожие на резюме
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
    # выводим общее количество всех найденных вакансий, если только начали поиск
    if page_num == 0 and self.resume_vac_page_num == -1:
        total_found = resume_vacancies["found"] + main_vacancies["found"]
        logger.info(f"Найдено {total_found} вакансий")
    return vacancies
```

#### Реализация в Go
```go
func (c *HHClient) GetSimilarVacancies(resumeID, accessToken string, params map[string]interface{}) (*VacanciesResponse, error) {
    url := fmt.Sprintf("https://api.hh.ru/resumes/%s/similar_vacancies", resumeID)
    
    // Build query parameters
    queryParams := url.Values{}
    for key, value := range params {
        queryParams.Set(key, fmt.Sprintf("%v", value))
    }
    
    fullURL := fmt.Sprintf("%s?%s", url, queryParams.Encode())
    
    req, err := http.NewRequest("GET", fullURL, nil)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result VacanciesResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, err
    }
    
    return &result, nil
}

type VacanciesResponse struct {
    Found   int              `json:"found"`
    Pages   int              `json:"pages"`
    PerPage int              `json:"per_page"`
    Page    int              `json:"page"`
    Items   []VacancyShort   `json:"items"`
}

type VacancyShort struct {
    ID            string   `json:"id"`
    Name          string   `json:"name"`
    HasTest       bool     `json:"has_test"`
    Area          Area     `json:"area"`
    Salary        *Salary  `json:"salary,omitempty"`
    Employer      Employer `json:"employer"`
    Snippet       Snippet  `json:"snippet"`
    AlternateURL  string   `json:"alternate_url"`
    // ... другие поля
}

type Area struct {
    ID   string `json:"id"`
    Name string `json:"name"`
    URL  string `json:"url"`
}

type Salary struct {
    From     int    `json:"from"`
    To       int    `json:"to"`
    Currency string `json:"currency"`
    Gross    bool   `json:"gross"`
}

type Employer struct {
    ID                   string `json:"id"`
    Name                 string `json:"name"`
    URL                  string `json:"url"`
    AlternateURL         string `json:"alternate_url"`
    AccreditedITEmployer bool   `json:"accredited_it_employer"`
    Trusted              bool   `json:"trusted"`
}

type Snippet struct {
    Requirement    string `json:"requirement"`
    Responsibility string `json:"responsibility"`
}
```

---

### Шаг 4.2: Общий поиск вакансий

#### Эндпоинт
```
GET https://api.hh.ru/vacancies
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Query Parameters (основные)
```
text: string - текст поиска (название должности, ключевые слова)
page: int (default=0)
per_page: int (default=20, max=100)
area: int/array - регион поиска (1 = Москва, 2 = Санкт-Петербург)
salary: int - минимальная зарплата
only_with_salary: bool - показывать только вакансии с указанной зарплатой
currency: string (RUR, USD, EUR)
experience: string (noExperience, between1And3, between3And6, moreThan6)
employment: string/array (full, part, project, volunteer, probation)
schedule: string/array (fullDay, shift, flexible, remote, flyInFlyOut)
search_field: string/array (name, company_name, description)
professional_role: int/array - профессиональная роль
industry: int/array - индустрия
label: string/array - метки вакансий (not_from_agency, accept_handicapped, etc.)
order_by: string (relevance, publication_time, salary_desc, salary_asc)
period: int - период размещения в днях (1, 3, 7, 30)
```

#### Когда используется
- **Вторая фаза** поиска вакансий (после similar_vacancies)
- Когда похожие на резюме вакансии закончились

#### Response 200
Аналогичен ответу `/resumes/{id}/similar_vacancies` (см. выше)

#### Логика из проекта
См. `search_vacancies()` выше - использует тот же метод после похожих вакансий

#### Реализация в Go
```go
func (c *HHClient) SearchVacancies(accessToken string, params map[string]interface{}) (*VacanciesResponse, error) {
    url := "https://api.hh.ru/vacancies"
    
    // Build query parameters
    queryParams := url.Values{}
    for key, value := range params {
        switch v := value.(type) {
        case []string:
            for _, item := range v {
                queryParams.Add(key, item)
            }
        default:
            queryParams.Set(key, fmt.Sprintf("%v", v))
        }
    }
    
    fullURL := fmt.Sprintf("%s?%s", url, queryParams.Encode())
    
    req, err := http.NewRequest("GET", fullURL, nil)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result VacanciesResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, err
    }
    
    return &result, nil
}
```

---

### Шаг 4.3: Получение детальной информации о вакансии

#### Эндпоинт
```
GET https://api.hh.ru/vacancies/{vacancy_id}
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Когда используется
- Для получения полного описания вакансии (включая HTML description)
- Перед отправкой отклика для анализа вакансии через LLM

#### Response 200 (основные поля)
```json
{
  "id": "12345678",
  "name": "Backend Developer (Go)",
  "description": "<p>Мы ищем опытного Backend Developer...</p><ul><li>Go</li><li>PostgreSQL</li></ul>",
  "key_skills": [
    {
      "name": "Go"
    },
    {
      "name": "PostgreSQL"
    },
    {
      "name": "Redis"
    },
    {
      "name": "Docker"
    }
  ],
  "area": {
    "id": "1",
    "name": "Москва"
  },
  "salary": {
    "from": 200000,
    "to": 350000,
    "currency": "RUR",
    "gross": false
  },
  "employer": {
    "id": "1234",
    "name": "Tech Company LLC",
    "accredited_it_employer": true
  },
  "has_test": false,
  "response_letter_required": true,
  "accept_handicapped": false,
  "accept_kids": false,
  "driver_license_types": [],
  "experience": {
    "id": "between3And6",
    "name": "От 3 до 6 лет"
  },
  "employment": {
    "id": "full",
    "name": "Полная занятость"
  },
  "schedule": {
    "id": "remote",
    "name": "Удаленная работа"
  },
  "professional_roles": [
    {
      "id": "96",
      "name": "Программист, разработчик"
    }
  ],
  "contacts": null,
  "work_format": [
    {
      "id": "remote",
      "name": "Удаленная работа"
    }
  ],
  "work_schedule_by_days": [],
  "alternate_url": "https://hh.ru/vacancy/12345678",
  "apply_alternate_url": "https://hh.ru/applicant/vacancy_response?vacancyId=12345678",
  "published_at": "2023-10-20T10:00:00+0300",
  "created_at": "2023-10-20T10:00:00+0300",
  "archived": false
}
```

#### Логика из проекта
```python
# src/job_manager/job_applier.py (строки 155-211)

def scrape_vacancy(self, vacancy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Собрать всю информацию о работодателе
    для дальнейшей передачи в LLM
    """
    job = {}
    job["job_title"] = vacancy["name"]
    job["vacancy_id"] = vacancy["id"]
    job["company_id"] = vacancy["employer"].get("id")
    if vacancy.get("salary"):
        job["salary"] = vacancy["salary"]
    if vacancy.get("address"):
        job["address"] = vacancy["address"]
    job["area"] = vacancy["area"]["name"]
    if vacancy.get("contacts"):
        job["contacts"] = vacancy["contacts"]
    if vacancy.get("department"):
        job["company_department"] = vacancy["department"]["name"]
    job["company_name"] = vacancy["employer"]["name"]
    if vacancy["employer"].get("accredited_it_employer"):
        job["accredited_it_employer"] = vacancy["employer"]["accredited_it_employer"]
    job["has_test_task"] = vacancy["has_test"]
    if vacancy["snippet"]["requirement"]:
        job["requirement"] = vacancy["snippet"]["requirement"]
    if vacancy["snippet"]["responsibility"]:
        job["responsibility"] = vacancy["snippet"]["responsibility"]
    if vacancy.get("work_format"):
        job["work_format"] = [format["name"] for format in vacancy["work_format"]]
    if vacancy.get("work_schedule_by_days"):
        job["work_schedule_by_days"] = [
            schedule["name"] for schedule in vacancy["work_schedule_by_days"]
        ]
    if vacancy.get("employment_form"):
        job["employment_form"] = vacancy["employment_form"]["name"]
    if vacancy.get("experience"):
        job["required_experience"] = vacancy["experience"]["name"]
    job["professional_roles"] = [role["name"] for role in vacancy["professional_roles"]]
    if vacancy.get("night_shifts"):
        job["night_shifts"] = vacancy["night_shifts"]
    if vacancy.get("internship"):
        job["is_internship"] = vacancy["internship"]
    if vacancy.get("accept_temporary"):
        job["accept_temporary_employment"] = vacancy["accept_temporary"]
    # собрать дополнительную информацию о работодателе (описание)
    vacancy_description = self.api.api_request(
        f"https://api.hh.ru/vacancies/{vacancy['id']}",
    )
    job_description = vacancy_description["description"]
    job["job_description"] = re.sub(r"<[^>]+>", "", job_description)
    job["accept_handicapped_employers"] = vacancy_description["accept_handicapped"]
    if vacancy_description.get("driver_license_types"):
        job["required_driver_licenses"] = vacancy_description["driver_license_types"]
    if vacancy_description.get("key_skills"):
        self.job_key_skills = [v["name"] for v in vacancy_description["key_skills"]]
    else:
        self.job_key_skills = []
    return job
```

#### Реализация в Go
```go
func (c *HHClient) GetVacancyDetails(vacancyID, accessToken string) (*VacancyDetail, error) {
    url := fmt.Sprintf("https://api.hh.ru/vacancies/%s", vacancyID)
    
    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var vacancy VacancyDetail
    if err := json.NewDecoder(resp.Body).Decode(&vacancy); err != nil {
        return nil, err
    }
    
    return &vacancy, nil
}

type VacancyDetail struct {
    ID                  string           `json:"id"`
    Name                string           `json:"name"`
    Description         string           `json:"description"` // HTML
    KeySkills           []KeySkill       `json:"key_skills"`
    Area                Area             `json:"area"`
    Salary              *Salary          `json:"salary,omitempty"`
    Employer            Employer         `json:"employer"`
    HasTest             bool             `json:"has_test"`
    AcceptHandicapped   bool             `json:"accept_handicapped"`
    DriverLicenseTypes  []DriverLicense  `json:"driver_license_types"`
    Experience          Experience       `json:"experience"`
    Employment          Employment       `json:"employment"`
    Schedule            Schedule         `json:"schedule"`
    ProfessionalRoles   []ProfRole       `json:"professional_roles"`
    WorkFormat          []WorkFormat     `json:"work_format"`
    AlternateURL        string           `json:"alternate_url"`
    PublishedAt         time.Time        `json:"published_at"`
}

type KeySkill struct {
    Name string `json:"name"`
}
```

---

## Отправка откликов

### Шаг 5: Отправка отклика на вакансию

#### Эндпоинт
```
POST https://api.hh.ru/negotiations
```

#### Headers
```
Authorization: Bearer <access_token>
```

#### Request Body (form-data или query params)
```
vacancy_id: string - ID вакансии
resume_id: string - ID резюме
message: string - сопроводительное письмо (опционально, но рекомендуется)
```

#### Когда используется
- После LLM оценки вакансии как "интересной"
- Генерации сопроводительного письма (или использования фиксированного)

#### Response 201 (Success - Created)
```json
{
  "id": "98765432",
  "state": {
    "id": "response",
    "name": "Отклик отправлен"
  },
  "created_at": "2023-10-20T15:30:00+0300",
  "viewed_by_opponent": false,
  "resume": {
    "id": "0123456789abcdef",
    "title": "Backend Developer",
    "url": "https://api.hh.ru/resumes/0123456789abcdef"
  },
  "vacancy": {
    "id": "12345678",
    "name": "Backend Developer (Go)",
    "url": "https://api.hh.ru/vacancies/12345678",
    "alternate_url": "https://hh.ru/vacancy/12345678"
  },
  "has_updates": false,
  "messages_url": "https://api.hh.ru/negotiations/98765432/messages"
}
```

#### Response 400 (Errors)

**1. Требуется пройти тест / ответить на вопросы:**
```json
{
  "errors": [
    {
      "type": "negotiations",
      "value": "test_required",
      "allowed_values": []
    }
  ],
  "description": "...",
  "request_id": "..."
}
```

**2. Лимит откликов исчерпан:**
```json
{
  "errors": [
    {
      "type": "negotiations",
      "value": "limit_exceeded",
      "allowed_values": []
    }
  ],
  "description": "Превышен лимит откликов"
}
```

**3. Уже откликались на эту вакансию:**
```json
{
  "errors": [
    {
      "type": "negotiations",
      "value": "already_applied",
      "allowed_values": []
    }
  ],
  "description": "Вы уже откликались на эту вакансию"
}
```

**4. Вакансия в архиве / не доступна:**
```json
{
  "errors": [
    {
      "type": "negotiations",
      "value": "application_denied",
      "allowed_values": []
    }
  ],
  "description": "Отклик на вакансию недоступен"
}
```

#### Логика из проекта
```python
# src/job_manager/job_applier.py (строки 394-482)

def apply_job(
    self, vacancy: Dict[str, Any], company_name: str, job_title: str, job: dict
) -> Tuple[str, str]:
    """Откликнуться на вакансию"""
    try:
        if self.fixed_cover_letter:
            logger.info(f"Берем готовое сопроводительное письмо")
            cover_letter_text = self.fixed_cover_letter
        elif not RESUME_MODE and not SKILL_STAT_MODE:
            cover_letter_text = self.gpt_answerer.write_cover_letter()
            # деанонимизируем информацию
            cover_letter_text = self.resume_component.deanonymize_personal_information(
                cover_letter_text
            )
            self._save_cover_letter(company_name, cover_letter_text, vacancy["alternate_url"])
        
        # ... (режимы отладки пропущены)
        
        params = {
            "message": cover_letter_text,
            "resume_id": self.resume_id,
            "vacancy_id": vacancy["id"],
        }
        response = self.api.api_request(
            type_="post",
            url="https://api.hh.ru/negotiations",
            params=params,
        )
        
        if "response_text" in response and "<!doctype html>" in response["response_text"]:
            return (
                "Skip",
                "Не смогли откликнуться. При отклике предлагают переход на сторонний сайт",
            )

        if "errors" in response:
            errors = response["errors"]
            for error in errors:
                # если уперлись в лимит по количеству откликов - выходим из цикла
                if error["value"] == "limit_exceeded":
                    logger.warning("Достигли лимита откликов")
                    return "Limit", ""
                # если нашли вопросы - отвечаем
                if error["value"] == "test_required" and self.hh_login and self.hh_password:
                    logger.info("Для отклика требуется пройти тест")
                    self.driver = self.init_driver()
                    answer_result, answer_text = self.find_and_handle_questions(
                        vacancy, cover_letter_text
                    )
                    if self.driver is not None:
                        self.driver.close()
                        self.driver = None
                    # если не на все вопросы были найдены ответы - пропускаем вакансию
                    if not answer_result:
                        return "Skip", answer_text
                    logger.info(f"Успешно откликнулись на вакансию компании {company_name}")
                    return "Success", ""
            # если ошибка заключается в другом, пропускаем вакансию
            error_message = ";".join([error["value"] for error in errors])
            logger.warning(
                f"Пропускаем вакансию компании {company_name} по причине ошибки при отклике: {error_message}"
            )
            return "Skip", error_message
        logger.info(f"Успешно откликнулись на вакансию компании {company_name}")
        pause()
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Ошибка на странице {vacancy['alternate_url']}")
        if self.driver is not None:
            self.driver.close()
            self.driver = None
        return "Error", str(e)
    return "Success", ""
```

#### Реализация в Go
```go
func (c *HHClient) ApplyToVacancy(vacancyID, resumeID, message, accessToken string) (*NegotiationResponse, error) {
    url := "https://api.hh.ru/negotiations"
    
    data := url.Values{}
    data.Set("vacancy_id", vacancyID)
    data.Set("resume_id", resumeID)
    if message != "" {
        data.Set("message", message)
    }
    
    req, err := http.NewRequest("POST", url, strings.NewReader(data.Encode()))
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    // Success
    if resp.StatusCode == 201 {
        var negotiation NegotiationResponse
        if err := json.NewDecoder(resp.Body).Decode(&negotiation); err != nil {
            return nil, err
        }
        return &negotiation, nil
    }
    
    // Errors
    var errResp ErrorResponse
    if err := json.NewDecoder(resp.Body).Decode(&errResp); err != nil {
        return nil, err
    }
    
    // Handle specific errors
    for _, e := range errResp.Errors {
        switch e.Value {
        case "limit_exceeded":
            return nil, ErrLimitExceeded
        case "test_required":
            return nil, ErrTestRequired
        case "already_applied":
            return nil, ErrAlreadyApplied
        case "application_denied":
            return nil, ErrApplicationDenied
        default:
            return nil, fmt.Errorf("application error: %s", e.Value)
        }
    }
    
    return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
}

type NegotiationResponse struct {
    ID               string    `json:"id"`
    State            State     `json:"state"`
    CreatedAt        time.Time `json:"created_at"`
    ViewedByOpponent bool      `json:"viewed_by_opponent"`
    Resume           struct {
        ID    string `json:"id"`
        Title string `json:"title"`
        URL   string `json:"url"`
    } `json:"resume"`
    Vacancy struct {
        ID           string `json:"id"`
        Name         string `json:"name"`
        URL          string `json:"url"`
        AlternateURL string `json:"alternate_url"`
    } `json:"vacancy"`
}

type ErrorResponse struct {
    Errors []struct {
        Type  string `json:"type"`
        Value string `json:"value"`
    } `json:"errors"`
    Description string `json:"description"`
}

var (
    ErrLimitExceeded     = errors.New("application limit exceeded")
    ErrTestRequired      = errors.New("test/questions required")
    ErrAlreadyApplied    = errors.New("already applied to this vacancy")
    ErrApplicationDenied = errors.New("application denied")
)
```

---

## Обработка ошибок

### Общая обработка ошибок API

#### Логика из проекта
```python
# src/job_manager/api.py (строки 23-60)

def api_request(
    self, url: str, type_: str = "get", params: Dict[str, str] = {}
) -> Dict[str, str]:
    response = self._send_request(url, type_, params)
    
    if "error" in response:
        raise ValueError(
            f"Неизвестная ошибка во время доступа к API HH: {response['error_description']}"
        )

    if "errors" in response:
        for error in response["errors"]:
            # если наткнулись на лимит - делаем паузу
            if error.get("type") == "too_many_requests":
                logger.warning("Слишком много запросов, ждем 1-2 часа")
                pause(3600, 7200)
                # далее повторяем запрос еще раз
                response = self._send_request(url, type_, params)
                break
            # если увидели сообщение о том, что истек срок токена, пытаемся обновить его
            if error.get("value") == "token_expired":
                logger.warning("Время жизни токена истекло")
                self.refress_access_token()
                # далее повторяем запрос еще раз
                response = self._send_request(url, type_, params)
                break
            elif (
                error.get("value") == "test_required"
                or error.get("value") == "limit_exceeded"
                or error.get("value") == "application_denied"
                or error.get("value") == "already_applied"
            ):
                # если требуется ответить на вопросы или лимит откликов исчерпан
                # или вакансия уже неактивна - пропускаем
                break
        else:
            raise ValueError(
                f"Неизвестная ошибка во время доступа к API HH: {response['errors']}"
            )
    return response
```

### Типы ошибок и их обработка

| Ошибка | Код | Описание | Действие |
|--------|-----|----------|----------|
| `token_expired` | 403 | Токен доступа истек | Обновить токены через `/token` |
| `too_many_requests` | 429 | Слишком много запросов | Пауза 1-2 часа, повторить запрос |
| `limit_exceeded` | 400 | Лимит откликов исчерпан | Прекратить отправку откликов |
| `test_required` | 400 | Требуются ответы на вопросы | Использовать Selenium для ответов |
| `already_applied` | 400 | Уже откликались на вакансию | Пропустить вакансию |
| `application_denied` | 400 | Отклик недоступен (архив и т.д.) | Пропустить вакансию |

#### Реализация обработки в Go
```go
func (c *HHClient) apiRequest(method, url, accessToken string, body io.Reader) ([]byte, error) {
    req, err := http.NewRequest(method, url, body)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    data, err := io.ReadAll(resp.Body)
    if err != nil {
        return nil, err
    }
    
    // Check for errors
    var errResp ErrorResponse
    if err := json.Unmarshal(data, &errResp); err == nil && len(errResp.Errors) > 0 {
        for _, e := range errResp.Errors {
            switch e.Value {
            case "token_expired":
                // Refresh token and retry
                return nil, ErrTokenExpired
            case "too_many_requests":
                // Wait and retry
                return nil, ErrTooManyRequests
            case "limit_exceeded":
                return nil, ErrLimitExceeded
            case "test_required":
                return nil, ErrTestRequired
            case "already_applied":
                return nil, ErrAlreadyApplied
            case "application_denied":
                return nil, ErrApplicationDenied
            }
        }
    }
    
    return data, nil
}
```

---

## Последовательность реализации

### Фаза 1: HH Client (Core) - 2-3 дня

#### День 1: Базовая инфраструктура
1. ✅ Создать `core/clients/hh_client.go`
   - HTTP client с timeout
   - Базовый метод `apiRequest` с обработкой ошибок
   - Retry logic для `too_many_requests`

2. ✅ Создать `core/models/hh_api.go`
   - Все структуры для работы с HH API
   - `TokenResponse`, `User`, `Resume`, `Vacancy`, `Negotiation`

3. ✅ Создать `core/services/token_service.go`
   - Хранение и обновление токенов
   - Auto-refresh при `token_expired`

#### День 2: Методы резюме и пользователя
4. ✅ Реализовать `RefreshAccessToken()`
5. ✅ Реализовать `GetCurrentUser()`
6. ✅ Реализовать `GetUserResumes()`
7. ✅ Реализовать `GetResume(resumeID)`
8. ✅ Реализовать `PublishResume(resumeID)`

#### День 3: Поиск и отклики
9. ✅ Реализовать `GetSimilarVacancies()`
10. ✅ Реализовать `SearchVacancies()`
11. ✅ Реализовать `GetVacancyDetails()`
12. ✅ Реализовать `ApplyToVacancy()`

---

### Фаза 2: Integration Tests - 1-2 дня

#### День 1: Unit Tests
1. ✅ Тесты для token refresh
2. ✅ Тесты для поиска вакансий
3. ✅ Тесты обработки ошибок
4. ✅ Mock HTTP responses

#### День 2: Integration Tests
5. ✅ Тесты с реальным HH API (sandbox если доступен)
6. ✅ Тесты rate limiting
7. ✅ Тесты error recovery

---

### Фаза 3: Обработка вопросов (Selenium) - 3-4 дня

**Примечание:** Вопросы работодателя обрабатываются через Selenium, т.к. HH API не предоставляет методы для ответов на вопросы.

#### Логика из проекта
```python
# src/job_manager/job_applier.py (строки 495-546)

def find_and_handle_questions(
    self, vacancy: Dict[str, Any], cover_letter_text: str
) -> Tuple[bool, str]:
    """Если на странице есть вопросы - использовать LLM для ответа на них"""
    authenticator = Authenticator(self.driver)
    authenticator.set_parameters(self.hh_login, self.hh_password)
    # заходим на сайт
    result = authenticator.start()
    if not result:
        logger.warning("Не смогли зайти на сайт")
        if self.driver is not None:
            self.driver.close()
            self.driver = None
        return False, "Не смогли зайти на сайт"
    
    self.driver.get(f"https://hh.ru/applicant/vacancy_response?vacancyId={vacancy['id']}")
    pause(2, 3)
    
    # обрабатываем сообщения, которые мешают отклику на вакансию
    self._handle_interfering_messages()
    
    # отвечаем на вопросы
    question_element = ("xpath", "//*[@data-qa='task-body']")
    questions = self.driver.find_elements(*question_element)
    if questions:
        logger.info("Нашли вопрос(ы).")
        for question in questions:
            answer, answer_text = self.handle_question(question)
            if not answer:
                logger.warning("Прерываем отклик на вакансию.")
                return False, answer_text
    else:
        logger.warning("Вопросы не найдены.")
        return False, "Вопросы не найдены."
    
    # обрабатываем сообщения, которые мешают отклику на вакансию
    self._handle_interfering_messages()
    
    # выбираем нужное резюме
    answer, answer_text = self._select_correct_resume()
    if not answer:
        return False, answer_text
    
    # вводим текст сопроводительного письма
    answer, answer_text = self._enter_cover_letter(cover_letter_text)
    if not answer:
        return False, answer_text
    
    # жмем кнопку 'Откликнуться'
    apply_element = self.driver.find_elements("xpath", "//*[text()='Откликнуться']")
    if not apply_element:
        logger.error("Не нашли кнопку отклика")
        return False, "Не нашли кнопку отклика"
    
    scroll_slow(self.driver, apply_element[0])
    apply_element[0].click()
    pause(3, 5)
    return True, ""
```

#### Реализация (опционально)
- Go не имеет встроенной поддержки Selenium
- Рекомендуется вынести в отдельный Python микросервис
- Или использовать библиотеку `tebeka/selenium` для Go

---

## Итоговые рекомендации

### Приоритеты реализации
1. **High Priority:**
   - Token management (auto-refresh)
   - Search vacancies (both methods)
   - Apply to vacancy
   - Error handling

2. **Medium Priority:**
   - Get resume details
   - Publish resume
   - Get vacancy details

3. **Low Priority:**
   - Questions handling (Selenium)
   - Advanced statistics

### Rate Limiting
- **Максимум запросов:** Не документировано, но на практике ~50-100 в минуту
- **При превышении:** HTTP 429 → пауза 1-2 часа
- **Рекомендация:** Добавить задержку 1-2 секунды между запросами

### Кеширование
- Кешировать детали вакансий (не меняются часто)
- НЕ кешировать результаты поиска (обновляются постоянно)
- Кешировать информацию о резюме на 1 час

---

**Автор:** HH API Integration Documentation  
**Версия:** 1.0  
**Дата:** 27 октября 2025  
**Источники:** Реальный код проекта (Python)

