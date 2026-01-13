# Шаг 2: Получение и обработка резюме пользователя

## Оглавление
1. [Обзор задачи](#обзор-задачи)
2. [Архитектура решения](#архитектура-решения)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [UX/UI Design](#uxui-design)
6. [API Contracts](#api-contracts)
7. [Data Models](#data-models)
8. [Последовательность реализации](#последовательность-реализации)

---

## Обзор задачи

### Цель
Реализовать полный процесс получения, обработки и анонимизации резюме пользователя из hh.ru API после OAuth авторизации.

### Контекст
После успешной OAuth авторизации через hh.ru (Шаг 1), система должна:
1. Получить список всех резюме пользователя
2. Выбрать релевантное резюме (автоматически или через UI)
3. Извлечь и структурировать данные резюме
4. Анонимизировать личную информацию для передачи в LLM
5. Сохранить резюме в БД
6. Поднять резюме в поиске (если возможно)

### Существующая реализация (Python)
Код находится в `src/job_manager/resume_scraper.py`:
- Класс `ResumeScraper` выполняет все операции
- 489 строк кода
- Интеграция с hh.ru API
- Анонимизация персональных данных
- Парсинг контактов через LLM

---

## Архитектура решения

### High-Level Flow

```
┌──────────────┐     OAuth     ┌──────────────┐
│   Frontend   ├──────────────>│  Core API    │
│   (Vue.js)   │               │   (Go)       │
└──────┬───────┘               └──────┬───────┘
       │                              │
       │  1. GET /resumes/list        │
       │<─────────────────────────────┤
       │                              │
       │  2. POST /resumes/select     │ 3. hh.ru API
       ├─────────────────────────────>│────────────┐
       │                              │            │
       │                              │<───────────┘
       │                              │
       │  4. Resume processed         │ 5. Save to DB
       │<─────────────────────────────┤────────────┐
       │                              │            │
       │  Dashboard updated           │<───────────┘
       │<─────────────────────────────┤
       │                              │
```

### Компоненты

**Backend (Go):**
- `core/handlers/resume.go` - HTTP handlers
- `core/services/resume_service.go` - Business logic
- `core/clients/hh_client.go` - hh.ru API client
- `core/models/resume.go` - Data models
- `core/repository/resume_repo.go` - Database access

**Frontend (Vue.js):**
- `src/views/ResumeSetup.vue` - Resume selection page
- `src/components/ResumeCard.vue` - Resume preview card
- `src/components/ResumeDetails.vue` - Detailed resume view
- `src/store/resume.js` - Vuex state management
- `src/api/resume.js` - API client

---

## Backend Implementation

### Подшаг 1: API Client для hh.ru

#### Файл: `core/clients/hh_client.go`

```go
package clients

import (
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type HHClient struct {
    baseURL     string
    httpClient  *http.Client
}

type HHResume struct {
    ID                string    `json:"id"`
    Title             string    `json:"title"`
    FirstName         string    `json:"first_name"`
    LastName          string    `json:"last_name"`
    MiddleName        string    `json:"middle_name"`
    Age               *int      `json:"age"`
    Gender            Gender    `json:"gender"`
    Area              Area      `json:"area"`
    Metro             *Metro    `json:"metro"`
    BirthDate         *string   `json:"birth_date"`
    Citizenship       []Country `json:"citizenship"`
    WorkTicket        []Country `json:"work_ticket"`
    HasVehicle        bool      `json:"has_vehicle"`
    DriverLicenseTypes []DLType `json:"driver_license_types"`
    Relocation        Relocation `json:"relocation"`
    Languages         []Language `json:"language"`
    Experience        []Exp      `json:"experience"`
    Education         Education  `json:"education"`
    TotalExperience   *TotalExp  `json:"total_experience"`
    SkillSet          []string   `json:"skill_set"`
    Skills            string     `json:"skills"`
    Salary            *Salary    `json:"salary"`
    Site              []Site     `json:"site"`
    Contact           []Contact  `json:"contact"`
    Certificate       []Cert     `json:"certificate"`
    Recommendation    []Rec      `json:"recommendation"`
    ProfessionalRoles []Role     `json:"professional_roles"`
    Employments       []Empl     `json:"employments"`
    Schedules         []Sched    `json:"schedules"`
    TravelTime        TravelTime `json:"travel_time"`
    BusinessTripReadiness BTR    `json:"business_trip_readiness"`
    NextPublishAt     time.Time  `json:"next_publish_at"`
    UpdatedAt         time.Time  `json:"updated_at"`
    CreatedAt         time.Time  `json:"created_at"`
}

// NewHHClient создает новый клиент для hh.ru API
func NewHHClient() *HHClient {
    return &HHClient{
        baseURL: "https://api.hh.ru",
        httpClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

// GetUserResumes получает список резюме пользователя
func (c *HHClient) GetUserResumes(accessToken string) ([]HHResume, error) {
    req, err := http.NewRequest("GET", c.baseURL+"/resumes/mine", nil)
    if err != nil {
        return nil, fmt.Errorf("create request: %w", err)
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    req.Header.Set("User-Agent", "XX_Auto_Jobs_Applier/1.0")
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("execute request: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("unexpected status: %d", resp.StatusCode)
    }
    
    var response struct {
        Items []HHResume `json:"items"`
    }
    
    if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
        return nil, fmt.Errorf("decode response: %w", err)
    }
    
    return response.Items, nil
}

// GetResumeDetails получает детальную информацию о резюме
func (c *HHClient) GetResumeDetails(resumeID, accessToken string) (*HHResume, error) {
    url := fmt.Sprintf("%s/resumes/%s", c.baseURL, resumeID)
    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        return nil, fmt.Errorf("create request: %w", err)
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    req.Header.Set("User-Agent", "XX_Auto_Jobs_Applier/1.0")
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("execute request: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("unexpected status: %d", resp.StatusCode)
    }
    
    var resume HHResume
    if err := json.NewDecoder(resp.Body).Decode(&resume); err != nil {
        return nil, fmt.Errorf("decode response: %w", err)
    }
    
    return &resume, nil
}

// PublishResume поднимает резюме в поиске
func (c *HHClient) PublishResume(resumeID, accessToken string) error {
    url := fmt.Sprintf("%s/resumes/%s/publish", c.baseURL, resumeID)
    req, err := http.NewRequest("POST", url, nil)
    if err != nil {
        return fmt.Errorf("create request: %w", err)
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    req.Header.Set("User-Agent", "XX_Auto_Jobs_Applier/1.0")
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return fmt.Errorf("execute request: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusNoContent {
        return fmt.Errorf("unexpected status: %d", resp.StatusCode)
    }
    
    return nil
}

// GetUserID получает ID пользователя
func (c *HHClient) GetUserID(accessToken string) (string, error) {
    req, err := http.NewRequest("GET", c.baseURL+"/me", nil)
    if err != nil {
        return "", fmt.Errorf("create request: %w", err)
    }
    
    req.Header.Set("Authorization", "Bearer "+accessToken)
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return "", fmt.Errorf("execute request: %w", err)
    }
    defer resp.Body.Close()
    
    var result struct {
        ID string `json:"id"`
    }
    
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return "", fmt.Errorf("decode response: %w", err)
    }
    
    return result.ID, nil
}
```

### Подшаг 2: Business Logic Service

#### Файл: `core/services/resume_service.go`

```go
package services

import (
    "context"
    "fmt"
    "strings"
    "time"
    
    "your-app/core/clients"
    "your-app/core/models"
    "your-app/core/repository"
)

type ResumeService struct {
    hhClient   *clients.HHClient
    resumeRepo *repository.ResumeRepository
    llmService *LLMService
}

func NewResumeService(
    hhClient *clients.HHClient,
    resumeRepo *repository.ResumeRepository,
    llmService *LLMService,
) *ResumeService {
    return &ResumeService{
        hhClient:   hhClient,
        resumeRepo: resumeRepo,
        llmService: llmService,
    }
}

// ListUserResumes получает список резюме из hh.ru
func (s *ResumeService) ListUserResumes(ctx context.Context, userID int64, accessToken string) ([]models.ResumeListItem, error) {
    // 1. Получить резюме из hh.ru
    hhResumes, err := s.hhClient.GetUserResumes(accessToken)
    if err != nil {
        return nil, fmt.Errorf("get resumes from hh: %w", err)
    }
    
    // 2. Преобразовать в модель приложения
    resumes := make([]models.ResumeListItem, len(hhResumes))
    for i, hr := range hhResumes {
        resumes[i] = models.ResumeListItem{
            ID:        hr.ID,
            Title:     hr.Title,
            UpdatedAt: hr.UpdatedAt,
            CreatedAt: hr.CreatedAt,
        }
    }
    
    return resumes, nil
}

// ProcessResume обрабатывает резюме: загрузка, анонимизация, сохранение
func (s *ResumeService) ProcessResume(ctx context.Context, userID int64, resumeID, accessToken string) (*models.Resume, error) {
    // 1. Получить детальную информацию о резюме
    hhResume, err := s.hhClient.GetResumeDetails(resumeID, accessToken)
    if err != nil {
        return nil, fmt.Errorf("get resume details: %w", err)
    }
    
    // 2. Поднять резюме в поиске (если возможно)
    if time.Now().After(hhResume.NextPublishAt) {
        if err := s.hhClient.PublishResume(resumeID, accessToken); err != nil {
            // Не критичная ошибка, логируем и продолжаем
            fmt.Printf("failed to publish resume: %v\n", err)
        }
    }
    
    // 3. Преобразовать в модель приложения
    resume := s.convertHHResumeToModel(userID, hhResume)
    
    // 4. Парсинг дополнительных контактов через LLM (если есть "О себе")
    if resume.AboutMe != "" {
        contacts, err := s.llmService.ParseContacts(ctx, resume.AboutMe)
        if err == nil {
            s.mergeContacts(resume, contacts)
        }
    }
    
    // 5. Анонимизация для LLM
    resume.AnonymizedData = s.anonymizeResume(resume)
    
    // 6. Сохранить в БД
    if err := s.resumeRepo.Save(ctx, resume); err != nil {
        return nil, fmt.Errorf("save resume: %w", err)
    }
    
    return resume, nil
}

// convertHHResumeToModel преобразует hh.ru резюме в модель приложения
func (s *ResumeService) convertHHResumeToModel(userID int64, hr *clients.HHResume) *models.Resume {
    resume := &models.Resume{
        UserID:   userID,
        ResumeID: hr.ID,
        Title:    hr.Title,
        
        // Персональная информация
        PersonalInfo: models.PersonalInfo{
            FirstName:  hr.FirstName,
            LastName:   hr.LastName,
            MiddleName: hr.MiddleName,
            Age:        hr.Age,
            Gender:     hr.Gender.Name,
            CurrentCity: hr.Area.Name,
        },
        
        // Контакты
        Contacts: s.extractContacts(hr),
        
        // Языки
        Languages: s.extractLanguages(hr),
        
        // Образование
        Education: s.extractEducation(hr),
        
        // Опыт работы
        Experience: s.extractExperience(hr),
        
        // Навыки
        Skills: hr.SkillSet,
        AboutMe: hr.Skills,
        
        // Предпочтения по работе
        WorkPreferences: s.extractWorkPreferences(hr),
        
        // Зарплатные ожидания
        SalaryExpectations: s.extractSalary(hr),
        
        UpdatedAt: time.Now(),
    }
    
    // Гражданство
    if len(hr.Citizenship) > 0 {
        citizenships := make([]string, len(hr.Citizenship))
        for i, c := range hr.Citizenship {
            citizenships[i] = c.Name
        }
        resume.PersonalInfo.Citizenship = citizenships
    }
    
    // Метро
    if hr.Metro != nil {
        resume.PersonalInfo.Metro = hr.Metro.Name
    }
    
    // Водительские права
    resume.PersonalInfo.HasVehicle = hr.HasVehicle
    if len(hr.DriverLicenseTypes) > 0 {
        licenses := make([]string, len(hr.DriverLicenseTypes))
        for i, dl := range hr.DriverLicenseTypes {
            licenses[i] = dl.ID
        }
        resume.PersonalInfo.DriverLicenses = licenses
    }
    
    return resume
}

// anonymizeResume создает анонимизированную версию резюме для LLM
func (s *ResumeService) anonymizeResume(resume *models.Resume) map[string]interface{} {
    // Словарь замен (dummy data)
    dummyData := getDummyDataByGender(resume.PersonalInfo.Gender)
    
    anonymized := map[string]interface{}{
        "position": resume.Title,
        "personal_information": map[string]interface{}{
            "first_name":   dummyData["first_name"],
            "last_name":    dummyData["last_name"],
            "middle_name":  dummyData["middle_name"],
            "age":          resume.PersonalInfo.Age,
            "gender":       resume.PersonalInfo.Gender,
            "current_city": resume.PersonalInfo.CurrentCity,
            "metro":        resume.PersonalInfo.Metro,
            "citizenship":  resume.PersonalInfo.Citizenship,
            "has_vehicle":  resume.PersonalInfo.HasVehicle,
        },
        "work_preferences": resume.WorkPreferences,
        "languages":        resume.Languages,
        "education":        resume.Education,
        "experience":       s.anonymizeExperience(resume.Experience, dummyData),
        "skills":           resume.Skills,
        "about_me":         s.anonymizeText(resume.AboutMe, resume, dummyData),
    }
    
    if resume.SalaryExpectations != nil {
        anonymized["salary_expectations"] = resume.SalaryExpectations
    }
    
    return anonymized
}

// anonymizeText заменяет личные данные в тексте на dummy данные
func (s *ResumeService) anonymizeText(text string, resume *models.Resume, dummyData map[string]string) string {
    replacements := map[string]string{
        resume.PersonalInfo.FirstName:  dummyData["first_name"],
        resume.PersonalInfo.LastName:   dummyData["last_name"],
        resume.PersonalInfo.MiddleName: dummyData["middle_name"],
    }
    
    // Анонимизация контактов
    if resume.Contacts.Phone != "" {
        replacements[resume.Contacts.Phone] = dummyData["phone"]
    }
    if resume.Contacts.Email != "" {
        replacements[resume.Contacts.Email] = dummyData["email"]
    }
    
    result := text
    for original, dummy := range replacements {
        if original != "" {
            result = strings.ReplaceAll(result, original, dummy)
        }
    }
    
    return result
}

// getDummyDataByGender возвращает dummy данные в зависимости от пола
func getDummyDataByGender(gender string) map[string]string {
    if strings.Contains(strings.ToLower(gender), "женский") {
        return map[string]string{
            "first_name":  "Анна",
            "last_name":   "Иванова",
            "middle_name": "Сергеевна",
            "phone":       "+7 (999) 111-22-33",
            "email":       "anna.ivanova@example.com",
        }
    }
    
    return map[string]string{
        "first_name":  "Иван",
        "last_name":   "Иванов",
        "middle_name": "Сергеевич",
        "phone":       "+7 (999) 111-22-33",
        "email":       "ivan.ivanov@example.com",
    }
}

// Helper methods для извлечения данных
func (s *ResumeService) extractContacts(hr *clients.HHResume) models.Contacts {
    contacts := models.Contacts{}
    
    for _, site := range hr.Site {
        url := strings.TrimSpace(site.URL)
        if strings.Contains(url, "t.me") {
            contacts.Telegram = url
        } else if strings.Contains(url, "wa.me") {
            contacts.WhatsApp = url
        } else if site.Type.ID == "linkedin" {
            contacts.LinkedIn = url
        } else if site.Type.ID == "skype" {
            contacts.Skype = url
        }
    }
    
    for _, contact := range hr.Contact {
        if contact.Type.ID == "cell" {
            contacts.Phone = contact.Value.Formatted
            if contact.Preferred {
                contacts.PreferredContact = "phone"
            }
        } else if contact.Type.ID == "email" {
            contacts.Email = contact.Value
            if contact.Preferred {
                contacts.PreferredContact = "email"
            }
        }
    }
    
    return contacts
}

func (s *ResumeService) extractLanguages(hr *clients.HHResume) map[string]string {
    languages := make(map[string]string)
    for _, lang := range hr.Languages {
        languages[lang.Name] = lang.Level.Name
    }
    return languages
}

func (s *ResumeService) extractEducation(hr *clients.HHResume) models.Education {
    edu := models.Education{
        Level: hr.Education.Level.Name,
    }
    
    // Основное образование
    if len(hr.Education.Primary) > 0 {
        primary := make([]models.EducationItem, len(hr.Education.Primary))
        for i, p := range hr.Education.Primary {
            primary[i] = models.EducationItem{
                Name:       p.Name,
                Result:     p.Result,
                Year:       p.Year,
                NameID:     p.NameID,
                ResultID:   p.ResultID,
            }
        }
        edu.Primary = primary
    }
    
    // Дополнительное образование
    if len(hr.Education.Additional) > 0 {
        additional := make([]models.EducationItem, len(hr.Education.Additional))
        for i, a := range hr.Education.Additional {
            additional[i] = models.EducationItem{
                Name:         a.Name,
                Organization: a.Organization,
                Year:         a.Year,
            }
        }
        edu.Additional = additional
    }
    
    return edu
}

func (s *ResumeService) extractExperience(hr *clients.HHResume) []models.ExperienceItem {
    if len(hr.Experience) == 0 {
        return nil
    }
    
    experience := make([]models.ExperienceItem, len(hr.Experience))
    for i, exp := range hr.Experience {
        experience[i] = models.ExperienceItem{
            Company:      exp.Employer,
            Position:     exp.Position,
            StartDate:    exp.Start,
            EndDate:      exp.End,
            Description:  exp.Description,
            Area:         exp.Area,
        }
        
        if len(exp.Industries) > 0 {
            industries := make([]string, len(exp.Industries))
            for j, ind := range exp.Industries {
                industries[j] = ind.Name
            }
            experience[i].Industries = industries
        }
    }
    
    return experience
}

func (s *ResumeService) extractWorkPreferences(hr *clients.HHResume) models.WorkPreferences {
    wp := models.WorkPreferences{
        Position: hr.Title,
        CanRelocate: hr.Relocation.Type.Name,
        NoticePeriod: "2 недели", // Default value
    }
    
    if len(hr.ProfessionalRoles) > 0 {
        roles := make([]string, len(hr.ProfessionalRoles))
        for i, role := range hr.ProfessionalRoles {
            roles[i] = role.Name
        }
        wp.ProfessionalRoles = roles
    }
    
    if len(hr.Employments) > 0 {
        employments := make([]string, len(hr.Employments))
        for i, emp := range hr.Employments {
            employments[i] = emp.Name
        }
        wp.Employments = employments
    }
    
    if len(hr.Schedules) > 0 {
        schedules := make([]string, len(hr.Schedules))
        for i, sched := range hr.Schedules {
            schedules[i] = sched.Name
        }
        wp.Schedules = schedules
    }
    
    wp.TravelTimeToWork = hr.TravelTime.Name
    wp.ReadyForBusinessTrips = hr.BusinessTripReadiness.Name
    
    return wp
}

func (s *ResumeService) extractSalary(hr *clients.HHResume) *models.Salary {
    if hr.Salary == nil {
        return nil
    }
    
    return &models.Salary{
        Amount:   hr.Salary.Amount,
        Currency: hr.Salary.Currency,
    }
}

func (s *ResumeService) mergeContacts(resume *models.Resume, parsedContacts map[string]string) {
    for key, value := range parsedContacts {
        keyLower := strings.ToLower(key)
        valueLower := strings.ToLower(value)
        
        if valueLower == "no info" {
            continue
        }
        
        switch keyLower {
        case "github":
            if resume.Contacts.GitHub == "" {
                resume.Contacts.GitHub = value
            }
        case "telegram":
            if resume.Contacts.Telegram == "" {
                resume.Contacts.Telegram = value
            }
        // ... другие поля
        }
    }
}

func (s *ResumeService) anonymizeExperience(experience []models.ExperienceItem, dummyData map[string]string) []models.ExperienceItem {
    // В experience обычно не требуется анонимизация, но можно добавить при необходимости
    return experience
}
```

### Подшаг 3: HTTP Handlers

#### Файл: `core/handlers/resume.go`

```go
package handlers

import (
    "encoding/json"
    "net/http"
    
    "your-app/core/services"
    "your-app/core/middleware"
)

type ResumeHandler struct {
    resumeService *services.ResumeService
}

func NewResumeHandler(resumeService *services.ResumeService) *ResumeHandler {
    return &ResumeHandler{
        resumeService: resumeService,
    }
}

// GET /api/v1/resumes/list
func (h *ResumeHandler) ListResumes(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    userID := middleware.GetUserID(ctx)
    accessToken := middleware.GetHHAccessToken(ctx)
    
    if accessToken == "" {
        http.Error(w, `{"error":"hh_oauth_required"}`, http.StatusUnauthorized)
        return
    }
    
    resumes, err := h.resumeService.ListUserResumes(ctx, userID, accessToken)
    if err != nil {
        http.Error(w, `{"error":"failed to fetch resumes"}`, http.StatusInternalServerError)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "resumes": resumes,
        "total":   len(resumes),
    })
}

// POST /api/v1/resumes/process
func (h *ResumeHandler) ProcessResume(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    userID := middleware.GetUserID(ctx)
    accessToken := middleware.GetHHAccessToken(ctx)
    
    var req struct {
        ResumeID string `json:"resume_id"`
    }
    
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, `{"error":"invalid request"}`, http.StatusBadRequest)
        return
    }
    
    resume, err := h.resumeService.ProcessResume(ctx, userID, req.ResumeID, accessToken)
    if err != nil {
        http.Error(w, `{"error":"failed to process resume"}`, http.StatusInternalServerError)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "resume": resume,
        "status": "success",
    })
}

// GET /api/v1/resumes/current
func (h *ResumeHandler) GetCurrentResume(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    userID := middleware.GetUserID(ctx)
    
    resume, err := h.resumeService.GetCurrentResume(ctx, userID)
    if err != nil {
        http.Error(w, `{"error":"resume not found"}`, http.StatusNotFound)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resume)
}
```

---

## Frontend Implementation

### Подшаг 1: Resume Selection Page

#### Файл: `frontend/src/views/ResumeSetup.vue`

```vue
<template>
  <div class="resume-setup">
    <!-- Header -->
    <div class="setup-header">
      <h1>{{ $t('resume.setup.title') }}</h1>
      <p class="subtitle">{{ $t('resume.setup.subtitle') }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ $t('resume.setup.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <h3>{{ $t('resume.setup.error') }}</h3>
      <p>{{ errorMessage }}</p>
      <button @click="fetchResumes" class="btn-retry">
        {{ $t('common.retry') }}
      </button>
    </div>

    <!-- No Resumes State -->
    <div v-else-if="resumes.length === 0" class="empty-state">
      <div class="empty-icon">📄</div>
      <h3>{{ $t('resume.setup.no_resumes') }}</h3>
      <p>{{ $t('resume.setup.no_resumes_hint') }}</p>
      <a href="https://hh.ru/applicant/resumes" target="_blank" class="btn-primary">
        {{ $t('resume.setup.create_on_hh') }}
      </a>
    </div>

    <!-- Resume Selection -->
    <div v-else class="resume-list">
      <div class="selection-hint">
        <span class="icon">💡</span>
        <span>{{ $t('resume.setup.selection_hint') }}</span>
      </div>

      <div class="resumes-grid">
        <ResumeCard
          v-for="resume in resumes"
          :key="resume.id"
          :resume="resume"
          :selected="selectedResumeId === resume.id"
          @select="selectResume(resume.id)"
        />
      </div>

      <!-- Action Buttons -->
      <div class="actions">
        <button @click="goBack" class="btn-secondary">
          {{ $t('common.back') }}
        </button>
        <button 
          @click="processSelectedResume" 
          :disabled="!selectedResumeId || processing"
          class="btn-primary"
        >
          <span v-if="processing" class="spinner-small"></span>
          {{ processing ? $t('resume.setup.processing') : $t('resume.setup.continue') }}
        </button>
      </div>
    </div>

    <!-- Progress Modal -->
    <Modal v-if="showProgressModal" @close="showProgressModal = false">
      <div class="progress-modal">
        <div class="progress-icon">⚙️</div>
        <h3>{{ $t('resume.setup.processing_resume') }}</h3>
        <p>{{ processingStatus }}</p>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${processingProgress}%` }"></div>
        </div>
        <p class="progress-text">{{ processingProgress }}%</p>
      </div>
    </Modal>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import ResumeCard from '@/components/ResumeCard.vue'
import Modal from '@/components/Modal.vue'
import { resumeApi } from '@/api/resume'

export default {
  name: 'ResumeSetup',
  components: {
    ResumeCard,
    Modal,
  },
  setup() {
    const router = useRouter()
    const store = useStore()
    
    const loading = ref(true)
    const error = ref(false)
    const errorMessage = ref('')
    const resumes = ref([])
    const selectedResumeId = ref(null)
    const processing = ref(false)
    const showProgressModal = ref(false)
    const processingStatus = ref('')
    const processingProgress = ref(0)

    // Загрузка списка резюме
    const fetchResumes = async () => {
      loading.value = true
      error.value = false
      
      try {
        const response = await resumeApi.listResumes()
        resumes.value = response.data.resumes
        
        // Автоматически выбрать первое резюме, если оно одно
        if (resumes.value.length === 1) {
          selectedResumeId.value = resumes.value[0].id
        }
      } catch (err) {
        error.value = true
        errorMessage.value = err.response?.data?.error || 'Failed to load resumes'
      } finally {
        loading.value = false
      }
    }

    const selectResume = (resumeId) => {
      selectedResumeId.value = resumeId
    }

    const processSelectedResume = async () => {
      if (!selectedResumeId.value) return
      
      processing.value = true
      showProgressModal.value = true
      
      // Симуляция прогресса
      const progressSteps = [
        { progress: 20, status: 'resume.setup.step.fetching' },
        { progress: 40, status: 'resume.setup.step.parsing' },
        { progress: 60, status: 'resume.setup.step.anonymizing' },
        { progress: 80, status: 'resume.setup.step.saving' },
        { progress: 100, status: 'resume.setup.step.complete' },
      ]
      
      try {
        for (let i = 0; i < progressSteps.length; i++) {
          const step = progressSteps[i]
          processingProgress.value = step.progress
          processingStatus.value = step.status
          
          if (i === 2) {
            // Реальный API запрос на этапе 60%
            await resumeApi.processResume(selectedResumeId.value)
          } else {
            // Симуляция задержки
            await new Promise(resolve => setTimeout(resolve, 500))
          }
        }
        
        // Сохранить в Vuex
        await store.dispatch('resume/fetchCurrentResume')
        
        // Перейти на Dashboard
        setTimeout(() => {
          router.push('/dashboard')
        }, 1000)
        
      } catch (err) {
        error.value = true
        errorMessage.value = err.response?.data?.error || 'Failed to process resume'
        showProgressModal.value = false
      } finally {
        processing.value = false
      }
    }

    const goBack = () => {
      router.back()
    }

    onMounted(() => {
      fetchResumes()
    })

    return {
      loading,
      error,
      errorMessage,
      resumes,
      selectedResumeId,
      processing,
      showProgressModal,
      processingStatus,
      processingProgress,
      fetchResumes,
      selectResume,
      processSelectedResume,
      goBack,
    }
  },
}
</script>

<style scoped>
.resume-setup {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.setup-header {
  text-align: center;
  margin-bottom: 48px;
}

.setup-header h1 {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.subtitle {
  font-size: 16px;
  color: #666;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Error State */
.error-state {
  text-align: center;
  padding: 80px 20px;
}

.error-icon {
  font-size: 64px;
  margin-bottom: 24px;
}

.error-state h3 {
  font-size: 24px;
  color: #dc2626;
  margin-bottom: 12px;
}

.error-state p {
  color: #666;
  margin-bottom: 24px;
}

.btn-retry {
  padding: 12px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-retry:hover {
  background: #2563eb;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 24px;
}

.empty-state h3 {
  font-size: 24px;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.empty-state p {
  color: #666;
  margin-bottom: 24px;
}

/* Resume List */
.selection-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: #eff6ff;
  border-radius: 8px;
  margin-bottom: 32px;
  color: #1e40af;
}

.selection-hint .icon {
  font-size: 20px;
}

.resumes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  margin-bottom: 48px;
}

/* Actions */
.actions {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.btn-primary,
.btn-secondary {
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  flex: 1;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #64748b;
  border: 2px solid #e2e8f0;
}

.btn-secondary:hover {
  border-color: #cbd5e1;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Progress Modal */
.progress-modal {
  text-align: center;
  padding: 40px;
}

.progress-icon {
  font-size: 48px;
  margin-bottom: 24px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.progress-modal h3 {
  font-size: 20px;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.progress-modal p {
  color: #666;
  margin-bottom: 24px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 14px;
  font-weight: 600;
  color: #3b82f6;
}
</style>
```

### Подшаг 2: Resume Card Component

#### Файл: `frontend/src/components/ResumeCard.vue`

```vue
<template>
  <div 
    class="resume-card" 
    :class="{ selected: selected }"
    @click="$emit('select')"
  >
    <div class="card-header">
      <div class="resume-title">{{ resume.title }}</div>
      <div v-if="selected" class="selected-badge">
        <span class="check-icon">✓</span>
      </div>
    </div>
    
    <div class="card-body">
      <div class="info-item">
        <span class="label">{{ $t('resume.updated') }}:</span>
        <span class="value">{{ formatDate(resume.updated_at) }}</span>
      </div>
      <div class="info-item">
        <span class="label">{{ $t('resume.created') }}:</span>
        <span class="value">{{ formatDate(resume.created_at) }}</span>
      </div>
    </div>
    
    <div class="card-footer">
      <a 
        :href="`https://hh.ru/resume/${resume.id}`" 
        target="_blank" 
        class="view-link"
        @click.stop
      >
        {{ $t('resume.view_on_hh') }} →
      </a>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResumeCard',
  props: {
    resume: {
      type: Object,
      required: true,
    },
    selected: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['select'],
  methods: {
    formatDate(dateString) {
      const date = new Date(dateString)
      return new Intl.DateTimeFormat('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      }).format(date)
    },
  },
}
</script>

<style scoped>
.resume-card {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s;
}

.resume-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.resume-card.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 20px;
}

.resume-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.4;
}

.selected-badge {
  width: 28px;
  height: 28px;
  background: #3b82f6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.check-icon {
  color: white;
  font-size: 16px;
  font-weight: bold;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  gap: 8px;
  font-size: 14px;
}

.label {
  color: #64748b;
  font-weight: 500;
}

.value {
  color: #1a1a1a;
}

.card-footer {
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.view-link {
  color: #3b82f6;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s;
}

.view-link:hover {
  color: #2563eb;
}
</style>
```

### Подшаг 3: API Client

#### Файл: `frontend/src/api/resume.js`

```javascript
import axios from 'axios'

const API_BASE = process.env.VUE_APP_API_BASE || '/api/v1'

export const resumeApi = {
  /**
   * Получить список резюме пользователя из hh.ru
   */
  async listResumes() {
    return axios.get(`${API_BASE}/resumes/list`)
  },

  /**
   * Обработать выбранное резюме
   */
  async processResume(resumeId) {
    return axios.post(`${API_BASE}/resumes/process`, {
      resume_id: resumeId,
    })
  },

  /**
   * Получить текущее резюме пользователя
   */
  async getCurrentResume() {
    return axios.get(`${API_BASE}/resumes/current`)
  },

  /**
   * Обновить резюме
   */
  async updateResume(resumeId, data) {
    return axios.put(`${API_BASE}/resumes/${resumeId}`, data)
  },
}
```

### Подшаг 4: Vuex Store

#### Файл: `frontend/src/store/modules/resume.js`

```javascript
import { resumeApi } from '@/api/resume'

const state = {
  currentResume: null,
  loading: false,
  error: null,
}

const getters = {
  currentResume: (state) => state.currentResume,
  hasResume: (state) => !!state.currentResume,
  isLoading: (state) => state.loading,
}

const actions = {
  async fetchCurrentResume({ commit }) {
    commit('SET_LOADING', true)
    commit('SET_ERROR', null)
    
    try {
      const response = await resumeApi.getCurrentResume()
      commit('SET_CURRENT_RESUME', response.data)
      return response.data
    } catch (error) {
      commit('SET_ERROR', error.response?.data?.error || 'Failed to fetch resume')
      throw error
    } finally {
      commit('SET_LOADING', false)
    }
  },

  clearResume({ commit }) {
    commit('SET_CURRENT_RESUME', null)
  },
}

const mutations = {
  SET_CURRENT_RESUME(state, resume) {
    state.currentResume = resume
  },

  SET_LOADING(state, loading) {
    state.loading = loading
  },

  SET_ERROR(state, error) {
    state.error = error
  },
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
```

---

## UX/UI Design

### Принципы минимизации клиентского пути

#### 1. **Single-Click Selection (если резюме одно)**
```
hh.ru OAuth → Automatic Resume Processing → Dashboard
     ↓              ↓                          ↓
  Шаг 1          Шаг 2                      Шаг 3
  
Время: 10 секунд (без UI взаимодействия)
```

#### 2. **Multi-Resume Flow (если резюме несколько)**
```
hh.ru OAuth → Resume Selection → Processing → Dashboard
     ↓              ↓                ↓            ↓
  Шаг 1          Шаг 2a           Шаг 2b       Шаг 3

Время: 30 секунд (1 клик пользователя)
```

### Ключевые UX решения

1. **Progressive Disclosure**
   - Показываем только необходимую информацию
   - Детали доступны по клику

2. **Optimistic UI**
   - Сразу показываем прогресс
   - Не блокируем UI во время загрузки

3. **Visual Feedback**
   - Анимированные индикаторы прогресса
   - Четкие состояния (loading, success, error)
   - Микроанимации при выборе

4. **Error Recovery**
   - Понятные сообщения об ошибках
   - Кнопка "Повторить" на каждом экране ошибки
   - Автоматический retry (3 попытки)

5. **Smart Defaults**
   - Автоматический выбор единственного резюме
   - Предзаполненные поля на следующих шагах

### UI States Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Resume Setup Page                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  STATE 1: Loading                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  [Spinner]                                        │    │
│  │  Загружаем ваши резюме из hh.ru...               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  STATE 2: Empty (No Resumes)                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │  📄                                               │    │
│  │  Резюме не найдены                                │    │
│  │  Создайте резюме на hh.ru                         │    │
│  │  [Создать резюме на hh.ru]                        │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  STATE 3: Resume Selection                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │  💡 Выберите резюме для автоматизации откликов   │    │
│  ├─────────────────────────────────────────────────┤    │
│  │                                                   │    │
│  │  ┌──────────────┐  ┌──────────────┐            │    │
│  │  │ ✓ Backend     │  │  Frontend     │            │    │
│  │  │  Developer    │  │  Developer    │            │    │
│  │  │  Обновлено:   │  │  Обновлено:   │            │    │
│  │  │  15 окт 2025  │  │  10 сент 2025 │            │    │
│  │  └──────────────┘  └──────────────┘            │    │
│  │                                                   │    │
│  │  [Назад]                    [Продолжить →]       │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  STATE 4: Processing                                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ⚙️                                               │    │
│  │  Обрабатываем ваше резюме                         │    │
│  │  Анонимизация персональных данных...              │    │
│  │  ░░░░░░░░░░░░░░████████████ 60%                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  STATE 5: Error                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ⚠️                                               │    │
│  │  Не удалось загрузить резюме                      │    │
│  │  Проверьте подключение к интернету               │    │
│  │  [Повторить попытку]                              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Responsive Design

**Desktop (>1024px):**
- Grid с 3 колонками для карточек резюме
- Широкие margins (40px)

**Tablet (768-1023px):**
- Grid с 2 колонками
- Средние margins (24px)

**Mobile (<768px):**
- Одна колонка
- Узкие margins (16px)
- Sticky footer с кнопками

---

## API Contracts

### GET /api/v1/resumes/list

**Request Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response 200:**
```json
{
  "resumes": [
    {
      "id": "resume_abc123",
      "title": "Backend Developer",
      "updated_at": "2025-10-15T14:30:00Z",
      "created_at": "2024-01-10T09:00:00Z"
    },
    {
      "id": "resume_def456",
      "title": "Frontend Developer",
      "updated_at": "2025-09-10T11:00:00Z",
      "created_at": "2023-05-20T10:00:00Z"
    }
  ],
  "total": 2
}
```

**Response 401:**
```json
{
  "error": "hh_oauth_required",
  "message": "Требуется авторизация через hh.ru"
}
```

---

### POST /api/v1/resumes/process

**Request Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "resume_id": "resume_abc123"
}
```

**Response 200:**
```json
{
  "resume": {
    "id": 1,
    "user_id": 123,
    "resume_id": "resume_abc123",
    "title": "Backend Developer",
    "personal_info": {
      "first_name": "Иван",
      "last_name": "Иванов",
      "middle_name": "Сергеевич",
      "age": 28,
      "gender": "Мужской",
      "current_city": "Москва",
      "metro": "Тверская",
      "citizenship": ["Россия"],
      "has_vehicle": false
    },
    "contacts": {
      "phone": "+7 (999) 111-22-33",
      "email": "ivan.ivanov@example.com",
      "telegram": "https://t.me/ivan_dev",
      "preferred_contact": "phone"
    },
    "languages": {
      "Русский": "Родной",
      "Английский": "B2 — Средне-продвинутый"
    },
    "education": {
      "level": "Высшее",
      "primary": [
        {
          "name": "МГУ им. Ломоносова",
          "result": "Прикладная математика",
          "year": 2019
        }
      ]
    },
    "experience": [
      {
        "company": "Яндекс",
        "position": "Backend Developer",
        "start_date": "2019-09-01",
        "end_date": null,
        "description": "Разработка микросервисов на Go...",
        "area": "Москва",
        "industries": ["Интернет-компания"]
      }
    ],
    "skills": ["Go", "Python", "PostgreSQL", "Docker", "Kubernetes"],
    "about_me": "Опытный backend разработчик с 5+ годами опыта...",
    "work_preferences": {
      "position": "Backend Developer",
      "can_relocate": "Не готов к переезду",
      "professional_roles": ["Программист, разработчик"],
      "employments": ["Полная занятость"],
      "schedules": ["Удаленная работа", "Гибкий график"],
      "travel_time_to_work": "Не имеет значения",
      "ready_for_business_trips": "Готов к командировкам"
    },
    "salary_expectations": {
      "amount": 250000,
      "currency": "RUR"
    },
    "updated_at": "2025-10-22T15:30:00Z"
  },
  "status": "success"
}
```

**Response 400:**
```json
{
  "error": "invalid_request",
  "message": "resume_id is required"
}
```

**Response 500:**
```json
{
  "error": "processing_failed",
  "message": "Failed to process resume from hh.ru"
}
```

---

### GET /api/v1/resumes/current

**Request Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response 200:**
```json
{
  "id": 1,
  "user_id": 123,
  "resume_id": "resume_abc123",
  "title": "Backend Developer",
  "personal_info": { ... },
  "contacts": { ... },
  "languages": { ... },
  "education": { ... },
  "experience": [ ... ],
  "skills": [ ... ],
  "about_me": "...",
  "work_preferences": { ... },
  "salary_expectations": { ... },
  "updated_at": "2025-10-22T15:30:00Z"
}
```

**Response 404:**
```json
{
  "error": "resume_not_found",
  "message": "Resume not found for this user"
}
```

---

## Data Models

### Database Schema (PostgreSQL)

```sql
-- Таблица: resumes
CREATE TABLE resumes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id VARCHAR(255) NOT NULL, -- ID резюме из hh.ru
    title VARCHAR(500) NOT NULL,
    
    -- Персональная информация (JSON)
    personal_info JSONB NOT NULL,
    
    -- Контакты (JSON)
    contacts JSONB NOT NULL,
    
    -- Языки (JSON)
    languages JSONB,
    
    -- Образование (JSON)
    education JSONB,
    
    -- Опыт работы (JSON)
    experience JSONB,
    
    -- Навыки (массив строк)
    skills TEXT[],
    
    -- О себе
    about_me TEXT,
    
    -- Предпочтения по работе (JSON)
    work_preferences JSONB,
    
    -- Зарплатные ожидания (JSON)
    salary_expectations JSONB,
    
    -- Анонимизированные данные для LLM (JSON)
    anonymized_data JSONB,
    
    -- Метаданные
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Индексы
    CONSTRAINT unique_user_resume UNIQUE(user_id, resume_id)
);

CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_resumes_resume_id ON resumes(resume_id);
CREATE INDEX idx_resumes_updated_at ON resumes(updated_at DESC);

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Go Models

```go
// models/resume.go
package models

import "time"

type Resume struct {
    ID                 int64                  `json:"id" db:"id"`
    UserID             int64                  `json:"user_id" db:"user_id"`
    ResumeID           string                 `json:"resume_id" db:"resume_id"`
    Title              string                 `json:"title" db:"title"`
    PersonalInfo       PersonalInfo           `json:"personal_info" db:"personal_info"`
    Contacts           Contacts               `json:"contacts" db:"contacts"`
    Languages          map[string]string      `json:"languages" db:"languages"`
    Education          Education              `json:"education" db:"education"`
    Experience         []ExperienceItem       `json:"experience" db:"experience"`
    Skills             []string               `json:"skills" db:"skills"`
    AboutMe            string                 `json:"about_me" db:"about_me"`
    WorkPreferences    WorkPreferences        `json:"work_preferences" db:"work_preferences"`
    SalaryExpectations *Salary                `json:"salary_expectations,omitempty" db:"salary_expectations"`
    AnonymizedData     map[string]interface{} `json:"anonymized_data,omitempty" db:"anonymized_data"`
    CreatedAt          time.Time              `json:"created_at" db:"created_at"`
    UpdatedAt          time.Time              `json:"updated_at" db:"updated_at"`
}

type PersonalInfo struct {
    FirstName      string   `json:"first_name"`
    LastName       string   `json:"last_name"`
    MiddleName     string   `json:"middle_name"`
    Age            *int     `json:"age,omitempty"`
    Gender         string   `json:"gender"`
    CurrentCity    string   `json:"current_city"`
    Metro          string   `json:"metro,omitempty"`
    Citizenship    []string `json:"citizenship,omitempty"`
    HasVehicle     bool     `json:"has_vehicle"`
    DriverLicenses []string `json:"driver_licenses,omitempty"`
}

type Contacts struct {
    Phone             string `json:"phone,omitempty"`
    Email             string `json:"email,omitempty"`
    Telegram          string `json:"telegram,omitempty"`
    WhatsApp          string `json:"whatsapp,omitempty"`
    LinkedIn          string `json:"linkedin,omitempty"`
    Skype             string `json:"skype,omitempty"`
    GitHub            string `json:"github,omitempty"`
    PreferredContact  string `json:"preferred_contact,omitempty"`
}

type Education struct {
    Level      string          `json:"level"`
    Primary    []EducationItem `json:"primary,omitempty"`
    Elementary []EducationItem `json:"elementary,omitempty"`
    Additional []EducationItem `json:"additional,omitempty"`
}

type EducationItem struct {
    Name         string `json:"name"`
    Organization string `json:"organization,omitempty"`
    Result       string `json:"result,omitempty"`
    Year         int    `json:"year,omitempty"`
    NameID       string `json:"name_id,omitempty"`
    ResultID     string `json:"result_id,omitempty"`
}

type ExperienceItem struct {
    Company     string   `json:"company"`
    Position    string   `json:"position"`
    StartDate   string   `json:"start_date"`
    EndDate     *string  `json:"end_date,omitempty"`
    Description string   `json:"description"`
    Area        string   `json:"area"`
    Industries  []string `json:"industries,omitempty"`
}

type WorkPreferences struct {
    Position              string   `json:"position"`
    CanRelocate           string   `json:"can_relocate"`
    NoticePeriod          string   `json:"notice_period,omitempty"`
    ProfessionalRoles     []string `json:"professional_roles,omitempty"`
    Employments           []string `json:"employments,omitempty"`
    Schedules             []string `json:"schedules,omitempty"`
    TravelTimeToWork      string   `json:"travel_time_to_work,omitempty"`
    ReadyForBusinessTrips string   `json:"ready_for_business_trips,omitempty"`
}

type Salary struct {
    Amount   int    `json:"amount"`
    Currency string `json:"currency"`
}

type ResumeListItem struct {
    ID        string    `json:"id"`
    Title     string    `json:"title"`
    UpdatedAt time.Time `json:"updated_at"`
    CreatedAt time.Time `json:"created_at"`
}
```

---

## Последовательность реализации

### Фаза 1: Backend Core (2-3 дня)

**День 1: API Client и Models**
1. ✅ Создать `core/clients/hh_client.go`
   - Методы: GetUserResumes, GetResumeDetails, PublishResume, GetUserID
   - Обработка ошибок и retry logic
   - Unit tests

2. ✅ Создать `core/models/resume.go`
   - Все data structures
   - JSON marshaling/unmarshaling
   - Validation tags

**День 2: Business Logic**
3. ✅ Создать `core/services/resume_service.go`
   - ListUserResumes
   - ProcessResume (конвертация, анонимизация)
   - Helper методы
   - Integration tests

4. ✅ Создать `core/repository/resume_repo.go`
   - CRUD операции
   - PostgreSQL queries
   - Database tests

**День 3: HTTP Handlers**
5. ✅ Создать `core/handlers/resume.go`
   - GET /api/v1/resumes/list
   - POST /api/v1/resumes/process
   - GET /api/v1/resumes/current
   - API tests

### Фаза 2: Frontend UI (2-3 дня)

**День 1: Core Components**
1. ✅ Создать `src/api/resume.js`
   - API client methods
   - Error handling

2. ✅ Создать `src/store/modules/resume.js`
   - Vuex state management
   - Actions и mutations

**День 2: Main Views**
3. ✅ Создать `src/views/ResumeSetup.vue`
   - Все 5 состояний UI
   - Обработка loading/error
   - Progress modal

4. ✅ Создать `src/components/ResumeCard.vue`
   - Карточка резюме
   - Selection state
   - Responsive design

**День 3: Integration и Polish**
5. ✅ Routing integration
   - Добавить маршрут в router
   - Middleware для OAuth check

6. ✅ i18n localization
   - Русские переводы
   - Английские переводы

7. ✅ E2E tests
   - Cypress tests для полного flow

### Фаза 3: Testing и Optimization (1-2 дня)

**День 1: Testing**
1. ✅ Unit tests (backend)
2. ✅ Integration tests
3. ✅ API tests
4. ✅ Frontend component tests
5. ✅ E2E tests

**День 2: Optimization**
1. ✅ Performance профилирование
2. ✅ Caching strategy
3. ✅ Error handling improvements
4. ✅ Logging и monitoring

---

## Метрики успеха

### Performance
- Time to process resume: < 3 seconds
- API response time: < 500ms
- Frontend rendering: < 100ms

### UX
- Клиентский путь (единственное резюме): 0 кликов
- Клиентский путь (несколько резюме): 1 клик
- Time to complete setup: < 30 seconds

### Quality
- Test coverage: > 80%
- Zero critical bugs
- All API endpoints documented

---

## Заключение

Этот документ содержит полное описание Шага 2 (Получение и обработка резюме) с детальными инструкциями для реализации как backend, так и frontend компонентов. 

Следуя этому плану, LLM сможет:
1. Реализовать полноценный API для работы с резюме
2. Создать удобный UI с минимальным клиентским путем
3. Обеспечить правильную анонимизацию данных
4. Интегрировать с существующей архитектурой

**Общее время реализации:** 5-8 дней  
**Приоритет:** High (блокирует Шаг 3 - поиск и отклик на вакансии)

