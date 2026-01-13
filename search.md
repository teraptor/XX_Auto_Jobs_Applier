# Шаг 3: Настройка параметров поиска и начало рассылки откликов

## Оглавление
1. [Обзор задачи](#обзор-задачи)
2. [Архитектура решения](#архитектура-решения)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [UX/UI Design](#uxui-design)
6. [API Contracts](#api-contracts)
7. [Data Models](#data-models)
8. [Progress Tracking](#progress-tracking)
9. [Interview Management](#interview-management)
10. [Последовательность реализации](#последовательность-реализации)

---

## Обзор задачи

### Цель
Реализовать полный процесс настройки параметров поиска, запуска задачи рассылки откликов и мониторинга прогресса в реальном времени.

### Контекст
После обработки резюме (Шаг 2), пользователь должен:
1. Настроить параметры поиска вакансий (фильтры, ключевые слова, география и т.д.)
2. Запустить задачу автоматической рассылки откликов
3. Наблюдать прогресс в реальном времени
4. Получать уведомления о результатах

### Существующая реализация (Python)

**Основные файлы:**
- `src/job_manager/job_applier.py` - логика поиска и откликов
- `src/job_manager/search_customizer.py` - настройка параметров поиска
- `data_folder_example/search_config/search_config.yaml` - пример конфигурации
- `src/pydantic_models/config.py` - модели данных

**Логика процесса:**
1. Поиск вакансий:
   - Сначала похожие на резюме (`/resumes/{id}/similar_vacancies`)
   - Затем общий поиск (`/vacancies`)
   
2. Обработка каждой вакансии:
   - Scraping деталей вакансии
   - Проверка черного списка
   - Проверка дубликатов (уже откликались)
   - LLM оценка соответствия (score 0-100)
   - Генерация сопроводительного письма
   - Отправка отклика через API
   - Обработка вопросов (через Selenium при необходимости)

3. Tracking:
   - Успешные отклики → `success.yaml`
   - Пропущенные вакансии → `skipped.yaml`
   - Ошибки → `failed.yaml`

---

## Архитектура решения

### High-Level Flow

```
┌──────────────┐                      ┌──────────────┐
│   Frontend   │                      │  Core API    │
│   (Vue.js)   │                      │   (Go)       │
└──────┬───────┘                      └──────┬───────┘
       │                                     │
       │ 1. GET /search-config              │
       │<────────────────────────────────────┤
       │                                     │
       │ 2. PUT /search-config              │
       ├────────────────────────────────────>│
       │    (save parameters)                │
       │                                     │
       │ 3. POST /jobs/start                │
       ├────────────────────────────────────>│ 4. Create Job
       │                                     ├──────────────┐
       │                                     │              │
       │                                     │<─────────────┘
       │                                     │
       │                                     │ 5. Push to Redis Queue
       │                                     ├──────────────────┐
       │                                     │                  │
       │                                     │                  ▼
       │                                  ┌──┴───────────┐  ┌──────────┐
       │                                  │   Worker     │  │  Redis   │
       │                                  │   Pool       │  │  Queue   │
       │                                  └──┬───────────┘  └──────────┘
       │                                     │
       │                                     │ 6. Process vacancies
       │                                     │    - Search hh.ru
       │                                     │    - LLM scoring
       │                                     │    - Generate letter
       │                                     │    - Apply
       │                                     │
       │ 7. GET /jobs/{id}/status (polling) │
       │<────────────────────────────────────┤
       │                                     │
       │ 8. PUT /applications/{id}/interview │
       │────────────────────────────────────>│
       │    (save interview date)            │
       │                                     │
```

### Компоненты

**Backend (Go):**
- `core/handlers/search_config.go` - Управление конфигурацией поиска
- `core/handlers/job.go` - Управление задачами поиска
- `core/handlers/application.go` - Управление откликами и собеседованиями
- `core/services/job_service.go` - Бизнес-логика задач
- `core/services/search_service.go` - Логика поиска вакансий
- `core/services/application_service.go` - Логика работы с откликами
- `core/workers/job_worker.go` - Worker для обработки задач
- `core/models/search_config.go` - Модели конфигурации
- `core/models/job.go` - Модели задач и откликов

**Frontend (Vue.js):**
- `src/views/SearchConfig.vue` - Страница настройки поиска
- `src/views/JobProgress.vue` - Страница мониторинга прогресса
- `src/views/Dashboard.vue` - Главная страница с кнопкой запуска
- `src/views/Applications.vue` - Список откликов с датами собеседований
- `src/components/SearchForm.vue` - Форма параметров поиска
- `src/components/JobStats.vue` - Компонент статистики задачи
- `src/store/modules/search.js` - Vuex state для конфигурации
- `src/store/modules/job.js` - Vuex state для задач
- `src/api/search.js` - API client для поиска
- `src/api/job.js` - API client для задач
- `src/api/application.js` - API client для откликов

---

## Backend Implementation

### Подшаг 1: Search Config Models и Repository

#### Файл: `core/models/search_config.go`

```go
package models

import "time"

type SearchConfig struct {
    ID                   int64           `json:"id" db:"id"`
    UserID               int64           `json:"user_id" db:"user_id"`
    JobTitle             string          `json:"job_title" db:"job_title"`
    Keywords             string          `json:"keywords,omitempty" db:"keywords"`
    WordsToExclude       string          `json:"words_to_exclude,omitempty" db:"words_to_exclude"`
    SearchField          SearchField     `json:"search_field" db:"search_field"`
    ProfessionalRole     string          `json:"professional_role,omitempty" db:"professional_role"`
    Industry             string          `json:"industry,omitempty" db:"industry"`
    Area                 string          `json:"area,omitempty" db:"area"`
    Metro                string          `json:"metro,omitempty" db:"metro"`
    Salary               *int            `json:"salary,omitempty" db:"salary"`
    OnlyWithSalary       bool            `json:"only_with_salary" db:"only_with_salary"`
    Currency             Currency        `json:"currency" db:"currency"`
    Experience           Experience      `json:"experience" db:"experience"`
    Employment           Employment      `json:"employment" db:"employment"`
    Schedule             Schedule        `json:"schedule" db:"schedule"`
    PartTime             PartTime        `json:"part_time" db:"part_time"`
    VacancyLabel         VacancyLabel    `json:"vacancy_label" db:"vacancy_label"`
    OrderBy              OrderBy         `json:"order_by" db:"order_by"`
    Period               Period          `json:"period" db:"period"`
    JobBlacklist         []string        `json:"job_blacklist" db:"job_blacklist"`
    FixedCoverLetter     *string         `json:"fixed_cover_letter,omitempty" db:"fixed_cover_letter"`
    ApplyOnceAtCompany   bool            `json:"apply_once_at_company" db:"apply_once_at_company"`
    SkipCompaniesWithTest bool           `json:"skip_companies_with_test" db:"skip_companies_with_test"`
    MaxAppliesNum        int             `json:"max_applies_num" db:"max_applies_num"`
    MaxTotalAppliesNum   *int            `json:"max_total_applies_num,omitempty" db:"max_total_applies_num"`
    CreatedAt            time.Time       `json:"created_at" db:"created_at"`
    UpdatedAt            time.Time       `json:"updated_at" db:"updated_at"`
}

type SearchField struct {
    Name        bool `json:"name"`
    CompanyName bool `json:"company_name"`
    Description bool `json:"description"`
}

type Currency struct {
    RUR bool `json:"rur"`
    EUR bool `json:"eur"`
    USD bool `json:"usd"`
}

type Experience struct {
    DoesntMatter bool `json:"doesnt_matter"`
    NoExperience bool `json:"no_experience"`
    Between1And3 bool `json:"between_1_and_3"`
    Between3And6 bool `json:"between_3_and_6"`
    MoreThan6    bool `json:"more_than_6"`
}

type Employment struct {
    Full      bool `json:"full"`
    Part      bool `json:"part"`
    Project   bool `json:"project"`
    Volunteer bool `json:"volunteer"`
    Probation bool `json:"probation"`
}

type Schedule struct {
    FullDay    bool `json:"full_day"`
    Shift      bool `json:"shift"`
    Flexible   bool `json:"flexible"`
    Remote     bool `json:"remote"`
    FlyInFlyOut bool `json:"fly_in_fly_out"`
}

type PartTime struct {
    Project                     bool `json:"project"`
    Part                        bool `json:"part"`
    FromFourToSixHoursInADay    bool `json:"from_four_to_six_hours_in_a_day"`
    OnlySaturdayAndSunday       bool `json:"only_saturday_and_sunday"`
    StartAfterSixteen           bool `json:"start_after_sixteen"`
}

type VacancyLabel struct {
    WithAddress      bool `json:"with_address"`
    AcceptHandicapped bool `json:"accept_handicapped"`
    NotFromAgency    bool `json:"not_from_agency"`
    AcceptKids       bool `json:"accept_kids"`
    AccreditedIT     bool `json:"accredited_it"`
    LowPerformance   bool `json:"low_performance"`
}

type OrderBy struct {
    Relevance        bool `json:"relevance"`
    PublicationTime  bool `json:"publication_time"`
    SalaryDesc       bool `json:"salary_desc"`
    SalaryAsc        bool `json:"salary_asc"`
}

type Period struct {
    AllTime   bool `json:"all_time"`
    Month     bool `json:"month"`
    Week      bool `json:"week"`
    ThreeDays bool `json:"three_days"`
    OneDay    bool `json:"one_day"`
}
```

#### Файл: `core/models/job.go`

```go
package models

import "time"

// Job - задача поиска и рассылки откликов
type Job struct {
    ID                 int64      `json:"id" db:"id"`
    UserID             int64      `json:"user_id" db:"user_id"`
    SearchConfigID     int64      `json:"search_config_id" db:"search_config_id"`
    Status             JobStatus  `json:"status" db:"status"`
    TotalVacancies     int        `json:"total_vacancies" db:"total_vacancies"`
    ProcessedVacancies int        `json:"processed_vacancies" db:"processed_vacancies"`
    SuccessApplies     int        `json:"success_applies" db:"success_applies"`
    SkippedVacancies   int        `json:"skipped_vacancies" db:"skipped_vacancies"`
    FailedApplies      int        `json:"failed_applies" db:"failed_applies"`
    CurrentPage        int        `json:"current_page" db:"current_page"`
    ErrorCount         int        `json:"error_count" db:"error_count"`
    StartedAt          *time.Time `json:"started_at,omitempty" db:"started_at"`
    CompletedAt        *time.Time `json:"completed_at,omitempty" db:"completed_at"`
    ErrorMessage       *string    `json:"error_message,omitempty" db:"error_message"`
    CreatedAt          time.Time  `json:"created_at" db:"created_at"`
    UpdatedAt          time.Time  `json:"updated_at" db:"updated_at"`
}

type JobStatus string

const (
    JobStatusPending    JobStatus = "pending"
    JobStatusRunning    JobStatus = "running"
    JobStatusPaused     JobStatus = "paused"
    JobStatusCompleted  JobStatus = "completed"
    JobStatusFailed     JobStatus = "failed"
    JobStatusCancelled  JobStatus = "cancelled"
)

// Application - отклик на вакансию
type Application struct {
    ID               int64           `json:"id" db:"id"`
    JobID            int64           `json:"job_id" db:"job_id"`
    UserID           int64           `json:"user_id" db:"user_id"`
    VacancyID        string          `json:"vacancy_id" db:"vacancy_id"`
    CompanyID        *string         `json:"company_id,omitempty" db:"company_id"`
    CompanyName      string          `json:"company_name" db:"company_name"`
    VacancyTitle     string          `json:"vacancy_title" db:"vacancy_title"`
    VacancyURL       string          `json:"vacancy_url" db:"vacancy_url"`
    VacancyData      VacancyData     `json:"vacancy_data" db:"vacancy_data"`
    Status           ApplicationStatus `json:"status" db:"status"`
    SkipReason       *string         `json:"skip_reason,omitempty" db:"skip_reason"`
    LLMScore         *int            `json:"llm_score,omitempty" db:"llm_score"`
    CoverLetter      *string         `json:"cover_letter,omitempty" db:"cover_letter"`
    QuestionsAnswers []QA            `json:"questions_answers,omitempty" db:"questions_answers"`
    InterviewDate    *time.Time      `json:"interview_date,omitempty" db:"interview_date"`
    InterviewNotes   *string         `json:"interview_notes,omitempty" db:"interview_notes"`
    AppliedAt        time.Time       `json:"applied_at" db:"applied_at"`
    CreatedAt        time.Time       `json:"created_at" db:"created_at"`
    UpdatedAt        time.Time       `json:"updated_at" db:"updated_at"`
}

type ApplicationStatus string

const (
    AppStatusSuccess ApplicationStatus = "success"
    AppStatusSkipped ApplicationStatus = "skipped"
    AppStatusFailed  ApplicationStatus = "failed"
)

type VacancyData struct {
    JobTitle                 string   `json:"job_title"`
    CompanyDepartment        *string  `json:"company_department,omitempty"`
    Salary                   *Salary  `json:"salary,omitempty"`
    Area                     string   `json:"area"`
    Address                  *string  `json:"address,omitempty"`
    HasTestTask              bool     `json:"has_test_task"`
    Requirement              *string  `json:"requirement,omitempty"`
    Responsibility           *string  `json:"responsibility,omitempty"`
    JobDescription           string   `json:"job_description"`
    WorkFormat               []string `json:"work_format,omitempty"`
    WorkScheduleByDays       []string `json:"work_schedule_by_days,omitempty"`
    EmploymentForm           *string  `json:"employment_form,omitempty"`
    RequiredExperience       *string  `json:"required_experience,omitempty"`
    ProfessionalRoles        []string `json:"professional_roles"`
    AccreditedITEmployer     bool     `json:"accredited_it_employer"`
    AcceptHandicappedEmployers bool   `json:"accept_handicapped_employers"`
    RequiredDriverLicenses   []string `json:"required_driver_licenses,omitempty"`
    KeySkills                []string `json:"key_skills,omitempty"`
}

type QA struct {
    Question string `json:"question"`
    Answer   string `json:"answer"`
}
```

### Подшаг 2: Search Config Service

#### Файл: `core/services/search_service.go`

```go
package services

import (
    "context"
    "fmt"
    "strings"
    
    "your-app/core/clients"
    "your-app/core/models"
    "your-app/core/repository"
)

type SearchService struct {
    hhClient     *clients.HHClient
    searchRepo   *repository.SearchConfigRepository
}

func NewSearchService(
    hhClient *clients.HHClient,
    searchRepo *repository.SearchConfigRepository,
) *SearchService {
    return &SearchService{
        hhClient:   hhClient,
        searchRepo: searchRepo,
    }
}

// GetSearchConfig получает конфигурацию поиска пользователя
func (s *SearchService) GetSearchConfig(ctx context.Context, userID int64) (*models.SearchConfig, error) {
    config, err := s.searchRepo.GetByUserID(ctx, userID)
    if err != nil {
        // Если конфигурации нет - создаем дефолтную
        if err == repository.ErrNotFound {
            return s.createDefaultConfig(ctx, userID)
        }
        return nil, fmt.Errorf("get search config: %w", err)
    }
    
    return config, nil
}

// UpdateSearchConfig обновляет конфигурацию поиска
func (s *SearchService) UpdateSearchConfig(ctx context.Context, userID int64, config *models.SearchConfig) error {
    config.UserID = userID
    
    // Валидация
    if err := s.validateSearchConfig(config); err != nil {
        return fmt.Errorf("validation failed: %w", err)
    }
    
    // Сохранение
    if err := s.searchRepo.Update(ctx, config); err != nil {
        return fmt.Errorf("update config: %w", err)
    }
    
    return nil
}

// BuildSearchParams преобразует SearchConfig в параметры для hh.ru API
func (s *SearchService) BuildSearchParams(config *models.SearchConfig) map[string]interface{} {
    params := make(map[string]interface{})
    
    // Текст поиска
    if config.Keywords != "" {
        params["text"] = config.Keywords
    }
    
    // Поля поиска
    searchFields := []string{}
    if config.SearchField.Name {
        searchFields = append(searchFields, "name")
    }
    if config.SearchField.CompanyName {
        searchFields = append(searchFields, "company_name")
    }
    if config.SearchField.Description {
        searchFields = append(searchFields, "description")
    }
    if len(searchFields) > 0 {
        params["search_field"] = searchFields
    }
    
    // Опыт работы
    experienceIDs := s.extractExperienceIDs(config.Experience)
    if len(experienceIDs) > 0 {
        params["experience"] = experienceIDs
    }
    
    // Тип занятости
    employmentIDs := s.extractEmploymentIDs(config.Employment)
    if len(employmentIDs) > 0 {
        params["employment"] = employmentIDs
    }
    
    // График работы
    scheduleIDs := s.extractScheduleIDs(config.Schedule)
    if len(scheduleIDs) > 0 {
        params["schedule"] = scheduleIDs
    }
    
    // Регионы
    if config.Area != "" {
        areas := strings.Split(config.Area, ",")
        areaIDs := []string{}
        for _, area := range areas {
            area = strings.TrimSpace(area)
            if area != "" {
                areaIDs = append(areaIDs, area)
            }
        }
        if len(areaIDs) > 0 {
            params["area"] = areaIDs
        }
    }
    
    // Зарплата
    if config.Salary != nil && *config.Salary > 0 {
        params["salary"] = *config.Salary
    }
    
    if config.OnlyWithSalary {
        params["only_with_salary"] = true
    }
    
    // Валюта
    if config.Currency.RUR {
        params["currency"] = "RUR"
    } else if config.Currency.EUR {
        params["currency"] = "EUR"
    } else if config.Currency.USD {
        params["currency"] = "USD"
    }
    
    // Период публикации
    period := s.extractPeriod(config.Period)
    if period > 0 {
        params["period"] = period
    }
    
    // Сортировка
    orderBy := s.extractOrderBy(config.OrderBy)
    if orderBy != "" {
        params["order_by"] = orderBy
    }
    
    // Подработка
    partTimeIDs := s.extractPartTimeIDs(config.PartTime)
    if len(partTimeIDs) > 0 {
        params["part_time"] = partTimeIDs
    }
    
    // Метки вакансий
    labelIDs := s.extractVacancyLabelIDs(config.VacancyLabel)
    if len(labelIDs) > 0 {
        params["label"] = labelIDs
    }
    
    return params
}

// Helper methods

func (s *SearchService) createDefaultConfig(ctx context.Context, userID int64) (*models.SearchConfig, error) {
    config := &models.SearchConfig{
        UserID:               userID,
        ApplyOnceAtCompany:   true,
        SkipCompaniesWithTest: false,
        MaxAppliesNum:        200,
        OnlyWithSalary:       false,
        // Дефолтные значения для вложенных структур
        SearchField:  models.SearchField{Name: true, CompanyName: true, Description: true},
        Currency:     models.Currency{RUR: true},
        Experience:   models.Experience{DoesntMatter: true},
        Employment:   models.Employment{Full: true},
        Schedule:     models.Schedule{FullDay: true, Remote: true},
        OrderBy:      models.OrderBy{Relevance: true},
        Period:       models.Period{Month: true},
    }
    
    if err := s.searchRepo.Create(ctx, config); err != nil {
        return nil, fmt.Errorf("create default config: %w", err)
    }
    
    return config, nil
}

func (s *SearchService) validateSearchConfig(config *models.SearchConfig) error {
    if config.JobTitle == "" {
        return fmt.Errorf("job_title is required")
    }
    
    if config.MaxAppliesNum <= 0 || config.MaxAppliesNum > 1000 {
        return fmt.Errorf("max_applies_num must be between 1 and 1000")
    }
    
    return nil
}

func (s *SearchService) extractExperienceIDs(exp models.Experience) []string {
    ids := []string{}
    if exp.DoesntMatter {
        return []string{} // Empty means "doesn't matter"
    }
    if exp.NoExperience {
        ids = append(ids, "noExperience")
    }
    if exp.Between1And3 {
        ids = append(ids, "between1And3")
    }
    if exp.Between3And6 {
        ids = append(ids, "between3And6")
    }
    if exp.MoreThan6 {
        ids = append(ids, "moreThan6")
    }
    return ids
}

func (s *SearchService) extractEmploymentIDs(emp models.Employment) []string {
    ids := []string{}
    if emp.Full {
        ids = append(ids, "full")
    }
    if emp.Part {
        ids = append(ids, "part")
    }
    if emp.Project {
        ids = append(ids, "project")
    }
    if emp.Volunteer {
        ids = append(ids, "volunteer")
    }
    if emp.Probation {
        ids = append(ids, "probation")
    }
    return ids
}

func (s *SearchService) extractScheduleIDs(sched models.Schedule) []string {
    ids := []string{}
    if sched.FullDay {
        ids = append(ids, "fullDay")
    }
    if sched.Shift {
        ids = append(ids, "shift")
    }
    if sched.Flexible {
        ids = append(ids, "flexible")
    }
    if sched.Remote {
        ids = append(ids, "remote")
    }
    if sched.FlyInFlyOut {
        ids = append(ids, "flyInFlyOut")
    }
    return ids
}

func (s *SearchService) extractPartTimeIDs(pt models.PartTime) []string {
    ids := []string{}
    if pt.Project {
        ids = append(ids, "project")
    }
    if pt.Part {
        ids = append(ids, "part")
    }
    if pt.FromFourToSixHoursInADay {
        ids = append(ids, "from_four_to_six_hours_in_a_day")
    }
    if pt.OnlySaturdayAndSunday {
        ids = append(ids, "only_saturday_and_sunday")
    }
    if pt.StartAfterSixteen {
        ids = append(ids, "start_after_sixteen")
    }
    return ids
}

func (s *SearchService) extractVacancyLabelIDs(vl models.VacancyLabel) []string {
    ids := []string{}
    if vl.WithAddress {
        ids = append(ids, "with_address")
    }
    if vl.AcceptHandicapped {
        ids = append(ids, "accept_handicapped")
    }
    if vl.NotFromAgency {
        ids = append(ids, "not_from_agency")
    }
    if vl.AcceptKids {
        ids = append(ids, "accept_kids")
    }
    if vl.AccreditedIT {
        ids = append(ids, "accredited_it")
    }
    if vl.LowPerformance {
        ids = append(ids, "low_performance")
    }
    return ids
}

func (s *SearchService) extractPeriod(p models.Period) int {
    if p.OneDay {
        return 1
    }
    if p.ThreeDays {
        return 3
    }
    if p.Week {
        return 7
    }
    if p.Month {
        return 30
    }
    return 0 // All time
}

func (s *SearchService) extractOrderBy(ob models.OrderBy) string {
    if ob.Relevance {
        return "relevance"
    }
    if ob.PublicationTime {
        return "publication_time"
    }
    if ob.SalaryDesc {
        return "salary_desc"
    }
    if ob.SalaryAsc {
        return "salary_asc"
    }
    return "relevance" // Default
}
```

### Подшаг 3: Job Service (Orchestrator)

#### Файл: `core/services/job_service.go`

```go
package services

import (
    "context"
    "fmt"
    "time"
    
    "your-app/core/models"
    "your-app/core/repository"
    "your-app/core/queue"
)

type JobService struct {
    jobRepo        *repository.JobRepository
    appRepo        *repository.ApplicationRepository
    searchService  *SearchService
    resumeService  *ResumeService
    llmService     *LLMService
    queue          *queue.RedisQueue
}

func NewJobService(
    jobRepo *repository.JobRepository,
    appRepo *repository.ApplicationRepository,
    searchService *SearchService,
    resumeService *ResumeService,
    llmService *LLMService,
    queue *queue.RedisQueue,
) *JobService {
    return &JobService{
        jobRepo:       jobRepo,
        appRepo:       appRepo,
        searchService: searchService,
        resumeService: resumeService,
        llmService:    llmService,
        queue:         queue,
    }
}

// StartJob создает и запускает новую задачу поиска
func (s *JobService) StartJob(ctx context.Context, userID int64) (*models.Job, error) {
    // 1. Проверка активной подписки
    // TODO: Check subscription

    // 2. Проверка наличия резюме
    resume, err := s.resumeService.GetCurrentResume(ctx, userID)
    if err != nil {
        return nil, fmt.Errorf("resume not found: %w", err)
    }

    // 3. Проверка конфигурации поиска
    searchConfig, err := s.searchService.GetSearchConfig(ctx, userID)
    if err != nil {
        return nil, fmt.Errorf("search config not found: %w", err)
    }

    // 4. Проверка ограничения по времени (не чаще раза в сутки)
    lastJob, err := s.jobRepo.GetLastByUserID(ctx, userID)
    if err == nil && lastJob != nil {
        if lastJob.CreatedAt.Add(24 * time.Hour).After(time.Now()) {
            return nil, fmt.Errorf("too soon: last job was %v ago", time.Since(lastJob.CreatedAt))
        }
    }

    // 5. Создание задачи
    job := &models.Job{
        UserID:         userID,
        SearchConfigID: searchConfig.ID,
        Status:         models.JobStatusPending,
        CreatedAt:      time.Now(),
        UpdatedAt:      time.Now(),
    }

    if err := s.jobRepo.Create(ctx, job); err != nil {
        return nil, fmt.Errorf("create job: %w", err)
    }

    // 6. Отправка задачи в очередь
    if err := s.queue.PushJob(ctx, job.ID); err != nil {
        return nil, fmt.Errorf("push to queue: %w", err)
    }

    return job, nil
}

// GetJobStatus получает текущий статус задачи
func (s *JobService) GetJobStatus(ctx context.Context, jobID, userID int64) (*models.Job, error) {
    job, err := s.jobRepo.GetByID(ctx, jobID)
    if err != nil {
        return nil, fmt.Errorf("get job: %w", err)
    }

    if job.UserID != userID {
        return nil, fmt.Errorf("access denied")
    }

    return job, nil
}

// CancelJob отменяет выполнение задачи
func (s *JobService) CancelJob(ctx context.Context, jobID, userID int64) error {
    job, err := s.jobRepo.GetByID(ctx, jobID)
    if err != nil {
        return fmt.Errorf("get job: %w", err)
    }

    if job.UserID != userID {
        return fmt.Errorf("access denied")
    }

    if job.Status != models.JobStatusRunning && job.Status != models.JobStatusPending {
        return fmt.Errorf("cannot cancel job with status: %s", job.Status)
    }

    job.Status = models.JobStatusCancelled
    job.UpdatedAt = time.Now()

    if err := s.jobRepo.Update(ctx, job); err != nil {
        return fmt.Errorf("update job: %w", err)
    }

    return nil
}

// GetApplications получает список откликов для задачи
func (s *JobService) GetApplications(ctx context.Context, jobID, userID int64, page, perPage int) ([]*models.Application, int, error) {
    job, err := s.jobRepo.GetByID(ctx, jobID)
    if err != nil {
        return nil, 0, fmt.Errorf("get job: %w", err)
    }

    if job.UserID != userID {
        return nil, 0, fmt.Errorf("access denied")
    }

    applications, total, err := s.appRepo.GetByJobID(ctx, jobID, page, perPage)
    if err != nil {
        return nil, 0, fmt.Errorf("get applications: %w", err)
    }

    return applications, total, nil
}
```

### Подшаг 4: Worker Implementation

#### Файл: `core/workers/job_worker.go`

```go
package workers

import (
    "context"
    "fmt"
    "log"
    "strings"
    "time"
    
    "your-app/core/clients"
    "your-app/core/models"
    "your-app/core/repository"
    "your-app/core/services"
)

type JobWorker struct {
    jobRepo       *repository.JobRepository
    appRepo       *repository.ApplicationRepository
    searchService *services.SearchService
    resumeService *services.ResumeService
    llmService    *services.LLMService
    hhClient      *clients.HHClient
}

func NewJobWorker(
    jobRepo *repository.JobRepository,
    appRepo *repository.ApplicationRepository,
    searchService *services.SearchService,
    resumeService *services.ResumeService,
    llmService *services.LLMService,
    hhClient *clients.HHClient,
) *JobWorker {
    return &JobWorker{
        jobRepo:       jobRepo,
        appRepo:       appRepo,
        searchService: searchService,
        resumeService: resumeService,
        llmService:    llmService,
        hhClient:      hhClient,
    }
}

// ProcessJob обрабатывает задачу поиска и рассылки откликов
func (w *JobWorker) ProcessJob(ctx context.Context, jobID int64) error {
    // 1. Получить задачу
    job, err := w.jobRepo.GetByID(ctx, jobID)
    if err != nil {
        return fmt.Errorf("get job: %w", err)
    }

    // 2. Обновить статус на "running"
    job.Status = models.JobStatusRunning
    now := time.Now()
    job.StartedAt = &now
    job.UpdatedAt = now
    if err := w.jobRepo.Update(ctx, job); err != nil {
        return fmt.Errorf("update job status: %w", err)
    }

    // 3. Загрузить конфигурацию
    searchConfig, err := w.searchService.GetSearchConfig(ctx, job.UserID)
    if err != nil {
        return w.failJob(ctx, job, fmt.Sprintf("get search config: %v", err))
    }

    // 4. Загрузить резюме
    resume, err := w.resumeService.GetCurrentResume(ctx, job.UserID)
    if err != nil {
        return w.failJob(ctx, job, fmt.Sprintf("get resume: %v", err))
    }

    // 5. Получить access token
    accessToken := "" // TODO: Get from user or secrets
    
    // 6. Построить параметры поиска
    searchParams := w.searchService.BuildSearchParams(searchConfig)
    
    // 7. Основной цикл обработки вакансий
    page := 0
    resumeVacanciesProcessed := false
    
    for {
        // Проверка отмены задачи
        if err := w.checkCancellation(ctx, job); err != nil {
            return err
        }

        // Проверка лимита откликов
        if job.SuccessApplies >= searchConfig.MaxAppliesNum {
            log.Printf("Job %d: reached max applies limit", jobID)
            break
        }

        // Поиск вакансий
        var vacancies []map[string]interface{}
        
        // Сначала похожие на резюме
        if !resumeVacanciesProcessed {
            vacancies, err = w.searchSimilarVacancies(ctx, resume.ResumeID, accessToken, searchParams, page)
            if err != nil {
                log.Printf("Job %d: error searching similar vacancies: %v", jobID, err)
            }
            
            if len(vacancies) == 0 {
                resumeVacanciesProcessed = true
            }
        }
        
        // Потом общий поиск
        if resumeVacanciesProcessed {
            searchParams["text"] = searchConfig.JobTitle
            vacancies, err = w.searchVacancies(ctx, accessToken, searchParams, page)
            if err != nil {
                return w.failJob(ctx, job, fmt.Sprintf("search vacancies: %v", err))
            }
        }

        if len(vacancies) == 0 {
            log.Printf("Job %d: no more vacancies found", jobID)
            break
        }

        // Обработка вакансий
        for _, vacancy := range vacancies {
            success := w.processVacancy(ctx, job, searchConfig, resume, vacancy, accessToken)
            
            // Обновление статистики
            job.ProcessedVacancies++
            
            if success {
                job.SuccessApplies++
            }
            
            // Сохранение прогресса каждые 10 вакансий
            if job.ProcessedVacancies%10 == 0 {
                job.CurrentPage = page
                job.UpdatedAt = time.Now()
                if err := w.jobRepo.Update(ctx, job); err != nil {
                    log.Printf("Job %d: error updating job: %v", jobID, err)
                }
            }
            
            // Пауза между откликами (антибан)
            time.Sleep(10 * time.Second)
            
            // Проверка лимита
            if job.SuccessApplies >= searchConfig.MaxAppliesNum {
                break
            }
        }

        page++
    }

    // 8. Завершение задачи
    return w.completeJob(ctx, job)
}

// processVacancy обрабатывает одну вакансию, возвращает true если отклик успешен
func (w *JobWorker) processVacancy(
    ctx context.Context,
    job *models.Job,
    config *models.SearchConfig,
    resume *models.Resume,
    vacancy map[string]interface{},
    accessToken string,
) bool {
    vacancyID := vacancy["id"].(string)
    companyName := vacancy["employer"].(map[string]interface{})["name"].(string)
    vacancyTitle := vacancy["name"].(string)
    vacancyURL := vacancy["alternate_url"].(string)
    
    log.Printf("Job %d: processing vacancy %s - %s", job.ID, companyName, vacancyTitle)
    
    // 1. Проверка черного списка
    if w.isBlacklisted(companyName, config.JobBlacklist) {
        log.Printf("Job %d: company %s is blacklisted", job.ID, companyName)
        job.SkippedVacancies++
        return false
    }
    
    // 2. Проверка дубликатов (уже откликались)
    isApplied, err := w.appRepo.IsAlreadyApplied(ctx, job.UserID, vacancyID, companyName, config.ApplyOnceAtCompany)
    if err != nil {
        log.Printf("Job %d: error checking duplicates: %v", job.ID, err)
    }
    if isApplied {
        log.Printf("Job %d: already applied to %s", job.ID, companyName)
        job.SkippedVacancies++
        return false
    }
    
    // 3. Получить детали вакансии
    vacancyDetails, err := w.hhClient.GetVacancyDetails(vacancyID, accessToken)
    if err != nil {
        log.Printf("Job %d: error getting vacancy details: %v", job.ID, err)
        job.FailedApplies++
        job.ErrorCount++
        return false
    }
    
    // 4. Преобразовать в структуру
    vacancyData := w.convertToVacancyData(vacancyDetails)
    
    // 5. LLM оценка соответствия
    score, err := w.llmService.JobIsInteresting(ctx, job.UserID, resume, vacancyData)
    if err != nil {
        log.Printf("Job %d: LLM error: %v", job.ID, err)
        job.FailedApplies++
        job.ErrorCount++
        return false
    }
    
    // Порог интересности
    if score < 70 {
        log.Printf("Job %d: vacancy score %d is too low", job.ID, score)
        w.saveApplication(ctx, job, vacancyID, companyName, vacancyTitle, vacancyURL, vacancyData, models.AppStatusSkipped, "Low score", &score, nil, nil)
        job.SkippedVacancies++
        return false
    }
    
    // 6. Генерация сопроводительного письма
    var coverLetter string
    if config.FixedCoverLetter != nil && *config.FixedCoverLetter != "" {
        coverLetter = *config.FixedCoverLetter
    } else {
        coverLetter, err = w.llmService.GenerateCoverLetter(ctx, job.UserID, resume, vacancyData)
        if err != nil {
            log.Printf("Job %d: error generating cover letter: %v", job.ID, err)
            job.FailedApplies++
            job.ErrorCount++
            return false
        }
    }
    
    // 7. Отправка отклика
    err = w.hhClient.ApplyToVacancy(vacancyID, resume.ResumeID, coverLetter, accessToken)
    if err != nil {
        log.Printf("Job %d: error applying to vacancy: %v", job.ID, err)
        w.saveApplication(ctx, job, vacancyID, companyName, vacancyTitle, vacancyURL, vacancyData, models.AppStatusFailed, err.Error(), &score, &coverLetter, nil)
        job.FailedApplies++
        job.ErrorCount++
        return false
    }
    
    // 8. Сохранение успешного отклика
    w.saveApplication(ctx, job, vacancyID, companyName, vacancyTitle, vacancyURL, vacancyData, models.AppStatusSuccess, "", &score, &coverLetter, nil)
    
    log.Printf("Job %d: successfully applied to %s - %s", job.ID, companyName, vacancyTitle)
    
    return true
}

// Helper methods

func (w *JobWorker) searchSimilarVacancies(ctx context.Context, resumeID, accessToken string, params map[string]interface{}, page int) ([]map[string]interface{}, error) {
    params["page"] = page
    params["per_page"] = 10
    
    response, err := w.hhClient.GetSimilarVacancies(resumeID, accessToken, params)
    if err != nil {
        return nil, err
    }
    
    items, ok := response["items"].([]interface{})
    if !ok {
        return []map[string]interface{}{}, nil
    }
    
    vacancies := make([]map[string]interface{}, len(items))
    for i, item := range items {
        vacancies[i] = item.(map[string]interface{})
    }
    
    return vacancies, nil
}

func (w *JobWorker) searchVacancies(ctx context.Context, accessToken string, params map[string]interface{}, page int) ([]map[string]interface{}, error) {
    params["page"] = page
    params["per_page"] = 10
    
    response, err := w.hhClient.SearchVacancies(accessToken, params)
    if err != nil {
        return nil, err
    }
    
    items, ok := response["items"].([]interface{})
    if !ok {
        return []map[string]interface{}{}, nil
    }
    
    vacancies := make([]map[string]interface{}, len(items))
    for i, item := range items {
        vacancies[i] = item.(map[string]interface{})
    }
    
    return vacancies, nil
}

func (w *JobWorker) isBlacklisted(companyName string, blacklist []string) bool {
    companyLower := strings.ToLower(strings.TrimSpace(companyName))
    for _, black := range blacklist {
        if strings.ToLower(strings.TrimSpace(black)) == companyLower {
            return true
        }
    }
    return false
}

func (w *JobWorker) convertToVacancyData(details map[string]interface{}) models.VacancyData {
    // TODO: Implement conversion from hh.ru API response to VacancyData
    return models.VacancyData{}
}

func (w *JobWorker) saveApplication(
    ctx context.Context,
    job *models.Job,
    vacancyID, companyName, vacancyTitle, vacancyURL string,
    vacancyData models.VacancyData,
    status models.ApplicationStatus,
    skipReason string,
    score *int,
    coverLetter *string,
    qa []models.QA,
) {
    app := &models.Application{
        JobID:            job.ID,
        UserID:           job.UserID,
        VacancyID:        vacancyID,
        CompanyName:      companyName,
        VacancyTitle:     vacancyTitle,
        VacancyURL:       vacancyURL,
        VacancyData:      vacancyData,
        Status:           status,
        LLMScore:         score,
        CoverLetter:      coverLetter,
        QuestionsAnswers: qa,
        AppliedAt:        time.Now(),
        CreatedAt:        time.Now(),
        UpdatedAt:        time.Now(),
    }
    
    if skipReason != "" {
        app.SkipReason = &skipReason
    }
    
    if err := w.appRepo.Create(ctx, app); err != nil {
        log.Printf("Job %d: error saving application: %v", job.ID, err)
    }
}

func (w *JobWorker) checkCancellation(ctx context.Context, job *models.Job) error {
    updatedJob, err := w.jobRepo.GetByID(ctx, job.ID)
    if err != nil {
        return fmt.Errorf("get job: %w", err)
    }
    
    if updatedJob.Status == models.JobStatusCancelled {
        return fmt.Errorf("job cancelled by user")
    }
    
    return nil
}

func (w *JobWorker) failJob(ctx context.Context, job *models.Job, errorMsg string) error {
    job.Status = models.JobStatusFailed
    job.ErrorMessage = &errorMsg
    now := time.Now()
    job.CompletedAt = &now
    job.UpdatedAt = now
    
    if err := w.jobRepo.Update(ctx, job); err != nil {
        return fmt.Errorf("update job: %w", err)
    }
    
    return fmt.Errorf("job failed: %s", errorMsg)
}

func (w *JobWorker) completeJob(ctx context.Context, job *models.Job) error {
    job.Status = models.JobStatusCompleted
    now := time.Now()
    job.CompletedAt = &now
    job.UpdatedAt = now
    
    if err := w.jobRepo.Update(ctx, job); err != nil {
        return fmt.Errorf("update job: %w", err)
    }
    
    log.Printf("Job %d completed: %d successful applies out of %d processed vacancies",
        job.ID, job.SuccessApplies, job.ProcessedVacancies)
    
    return nil
}
```

---

## Frontend Implementation

### Подшаг 1: Search Config Page

#### Файл: `frontend/src/views/SearchConfig.vue`

```vue
<template>
  <div class="search-config-page">
    <!-- Header -->
    <div class="page-header">
      <h1>{{ $t('search.config.title') }}</h1>
      <p class="subtitle">{{ $t('search.config.subtitle') }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>{{ $t('common.loading') }}</p>
    </div>

    <!-- Main Form -->
    <div v-else class="config-container">
      <!-- Save Button (Sticky) -->
      <div class="save-bar">
        <button 
          @click="saveConfig" 
          :disabled="saving || !hasChanges"
          class="btn-save"
        >
          <span v-if="saving" class="spinner-small"></span>
          {{ saving ? $t('common.saving') : $t('common.save') }}
        </button>
        <div v-if="saveSuccess" class="save-success">
          ✓ {{ $t('search.config.saved') }}
        </div>
      </div>

      <form @submit.prevent="saveConfig" class="config-form">
        <!-- Section 1: Basic Settings -->
        <section class="form-section">
          <h2>{{ $t('search.config.basic') }}</h2>
          
          <div class="form-group">
            <label for="jobTitle">{{ $t('search.config.job_title') }}*</label>
            <input
              id="jobTitle"
              v-model="config.job_title"
              type="text"
              :placeholder="$t('search.config.job_title_placeholder')"
              required
            />
          </div>

          <div class="form-group">
            <label for="keywords">{{ $t('search.config.keywords') }}</label>
            <input
              id="keywords"
              v-model="config.keywords"
              type="text"
              :placeholder="$t('search.config.keywords_placeholder')"
            />
            <span class="hint">{{ $t('search.config.keywords_hint') }}</span>
          </div>

          <div class="form-group">
            <label for="wordsToExclude">{{ $t('search.config.exclude_words') }}</label>
            <input
              id="wordsToExclude"
              v-model="config.words_to_exclude"
              type="text"
              :placeholder="$t('search.config.exclude_words_placeholder')"
            />
          </div>
        </section>

        <!-- Section 2: Search Fields -->
        <section class="form-section">
          <h2>{{ $t('search.config.search_in') }}</h2>
          
          <div class="checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.search_field.name" />
              <span>{{ $t('search.config.in_title') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.search_field.company_name" />
              <span>{{ $t('search.config.in_company') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.search_field.description" />
              <span>{{ $t('search.config.in_description') }}</span>
            </label>
          </div>
        </section>

        <!-- Section 3: Location -->
        <section class="form-section">
          <h2>{{ $t('search.config.location') }}</h2>
          
          <div class="form-group">
            <label for="area">{{ $t('search.config.area') }}</label>
            <input
              id="area"
              v-model="config.area"
              type="text"
              :placeholder="$t('search.config.area_placeholder')"
            />
          </div>

          <div class="form-group">
            <label for="metro">{{ $t('search.config.metro') }}</label>
            <input
              id="metro"
              v-model="config.metro"
              type="text"
              :placeholder="$t('search.config.metro_placeholder')"
            />
          </div>
        </section>

        <!-- Section 4: Salary -->
        <section class="form-section">
          <h2>{{ $t('search.config.salary') }}</h2>
          
          <div class="form-row">
            <div class="form-group flex-1">
              <label for="salary">{{ $t('search.config.min_salary') }}</label>
              <input
                id="salary"
                v-model.number="config.salary"
                type="number"
                :placeholder="$t('search.config.salary_placeholder')"
              />
            </div>

            <div class="form-group" style="width: 150px">
              <label>{{ $t('search.config.currency') }}</label>
              <div class="radio-group-inline">
                <label class="radio-label">
                  <input type="radio" v-model="currency" value="RUR" />
                  <span>RUB</span>
                </label>
                <label class="radio-label">
                  <input type="radio" v-model="currency" value="EUR" />
                  <span>EUR</span>
                </label>
                <label class="radio-label">
                  <input type="radio" v-model="currency" value="USD" />
                  <span>USD</span>
                </label>
              </div>
            </div>
          </div>

          <div class="checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.only_with_salary" />
              <span>{{ $t('search.config.only_with_salary') }}</span>
            </label>
          </div>
        </section>

        <!-- Section 5: Experience -->
        <section class="form-section">
          <h2>{{ $t('search.config.experience') }}</h2>
          
          <div class="radio-group">
            <label class="radio-label">
              <input type="radio" v-model="experience" value="doesntMatter" />
              <span>{{ $t('search.config.exp_any') }}</span>
            </label>
            <label class="radio-label">
              <input type="radio" v-model="experience" value="noExperience" />
              <span>{{ $t('search.config.exp_no') }}</span>
            </label>
            <label class="radio-label">
              <input type="radio" v-model="experience" value="between1And3" />
              <span>{{ $t('search.config.exp_1_3') }}</span>
            </label>
            <label class="radio-label">
              <input type="radio" v-model="experience" value="between3And6" />
              <span>{{ $t('search.config.exp_3_6') }}</span>
            </label>
            <label class="radio-label">
              <input type="radio" v-model="experience" value="moreThan6" />
              <span>{{ $t('search.config.exp_6plus') }}</span>
            </label>
          </div>
        </section>

        <!-- Section 6: Employment Type -->
        <section class="form-section">
          <h2>{{ $t('search.config.employment') }}</h2>
          
          <div class="checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.employment.full" />
              <span>{{ $t('search.config.emp_full') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.employment.part" />
              <span>{{ $t('search.config.emp_part') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.employment.project" />
              <span>{{ $t('search.config.emp_project') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.employment.volunteer" />
              <span>{{ $t('search.config.emp_volunteer') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.employment.probation" />
              <span>{{ $t('search.config.emp_probation') }}</span>
            </label>
          </div>
        </section>

        <!-- Section 7: Schedule -->
        <section class="form-section">
          <h2>{{ $t('search.config.schedule') }}</h2>
          
          <div class="checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.schedule.full_day" />
              <span>{{ $t('search.config.sched_full') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.schedule.shift" />
              <span>{{ $t('search.config.sched_shift') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.schedule.flexible" />
              <span>{{ $t('search.config.sched_flexible') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.schedule.remote" />
              <span>{{ $t('search.config.sched_remote') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.schedule.fly_in_fly_out" />
              <span>{{ $t('search.config.sched_fly') }}</span>
            </label>
          </div>
        </section>

        <!-- Section 8: Advanced Settings -->
        <section class="form-section">
          <h2>{{ $t('search.config.advanced') }}</h2>
          
          <div class="form-group">
            <label for="maxApplies">{{ $t('search.config.max_applies') }}</label>
            <input
              id="maxApplies"
              v-model.number="config.max_applies_num"
              type="number"
              min="1"
              max="1000"
              required
            />
            <span class="hint">{{ $t('search.config.max_applies_hint') }}</span>
          </div>

          <div class="form-group">
            <label for="blacklist">{{ $t('search.config.blacklist') }}</label>
            <textarea
              id="blacklist"
              v-model="blacklistText"
              rows="3"
              :placeholder="$t('search.config.blacklist_placeholder')"
            ></textarea>
          </div>

          <div class="checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.apply_once_at_company" />
              <span>{{ $t('search.config.once_per_company') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.skip_companies_with_test" />
              <span>{{ $t('search.config.skip_tests') }}</span>
            </label>
          </div>

          <div class="form-group">
            <label for="coverLetter">{{ $t('search.config.fixed_cover_letter') }}</label>
            <textarea
              id="coverLetter"
              v-model="config.fixed_cover_letter"
              rows="6"
              :placeholder="$t('search.config.cover_letter_placeholder')"
            ></textarea>
            <span class="hint">{{ $t('search.config.cover_letter_hint') }}</span>
          </div>
        </section>

        <!-- Action Buttons -->
        <div class="form-actions">
          <button type="button" @click="resetToDefault" class="btn-secondary">
            {{ $t('search.config.reset_default') }}
          </button>
          <button type="submit" :disabled="saving || !hasChanges" class="btn-primary">
            {{ saving ? $t('common.saving') : $t('common.save_and_continue') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { searchApi } from '@/api/search'

export default {
  name: 'SearchConfig',
  setup() {
    const router = useRouter()
    const store = useStore()
    
    const loading = ref(true)
    const saving = ref(false)
    const saveSuccess = ref(false)
    const originalConfig = ref(null)
    
    const config = reactive({
      job_title: '',
      keywords: '',
      words_to_exclude: '',
      search_field: {
        name: true,
        company_name: true,
        description: true,
      },
      area: '',
      metro: '',
      salary: null,
      only_with_salary: false,
      currency: { rur: true, eur: false, usd: false },
      experience: { doesnt_matter: true, no_experience: false, between_1_and_3: false, between_3_and_6: false, more_than_6: false },
      employment: { full: true, part: false, project: false, volunteer: false, probation: false },
      schedule: { full_day: true, shift: false, flexible: false, remote: true, fly_in_fly_out: false },
      part_time: { project: false, part: false, from_four_to_six_hours_in_a_day: false, only_saturday_and_sunday: false, start_after_sixteen: false },
      vacancy_label: { with_address: false, accept_handicapped: false, not_from_agency: false, accept_kids: false, accredited_it: true, low_performance: false },
      order_by: { relevance: true, publication_time: false, salary_desc: false, salary_asc: false },
      period: { all_time: false, month: true, week: false, three_days: false, one_day: false },
      job_blacklist: [],
      fixed_cover_letter: null,
      apply_once_at_company: true,
      skip_companies_with_test: false,
      max_applies_num: 200,
      max_total_applies_num: null,
    })

    // Computed для удобства работы с radio группами
    const currency = computed({
      get: () => {
        if (config.currency.eur) return 'EUR'
        if (config.currency.usd) return 'USD'
        return 'RUR'
      },
      set: (val) => {
        config.currency.rur = val === 'RUR'
        config.currency.eur = val === 'EUR'
        config.currency.usd = val === 'USD'
      }
    })

    const experience = computed({
      get: () => {
        if (config.experience.no_experience) return 'noExperience'
        if (config.experience.between_1_and_3) return 'between1And3'
        if (config.experience.between_3_and_6) return 'between3And6'
        if (config.experience.more_than_6) return 'moreThan6'
        return 'doesntMatter'
      },
      set: (val) => {
        config.experience.doesnt_matter = val === 'doesntMatter'
        config.experience.no_experience = val === 'noExperience'
        config.experience.between_1_and_3 = val === 'between1And3'
        config.experience.between_3_and_6 = val === 'between3And6'
        config.experience.more_than_6 = val === 'moreThan6'
      }
    })

    const blacklistText = computed({
      get: () => config.job_blacklist.join(', '),
      set: (val) => {
        config.job_blacklist = val
          .split(',')
          .map(s => s.trim())
          .filter(s => s !== '')
      }
    })

    const hasChanges = computed(() => {
      return JSON.stringify(config) !== JSON.stringify(originalConfig.value)
    })

    // Загрузка конфигурации
    const loadConfig = async () => {
      loading.value = true
      
      try {
        const response = await searchApi.getSearchConfig()
        Object.assign(config, response.data)
        originalConfig.value = JSON.parse(JSON.stringify(config))
      } catch (err) {
        console.error('Failed to load config:', err)
      } finally {
        loading.value = false
      }
    }

    // Сохранение конфигурации
    const saveConfig = async () => {
      saving.value = true
      saveSuccess.value = false
      
      try {
        await searchApi.updateSearchConfig(config)
        originalConfig.value = JSON.parse(JSON.stringify(config))
        
        // Сохранить в Vuex
        await store.dispatch('search/fetchConfig')
        
        saveSuccess.value = true
        setTimeout(() => {
          saveSuccess.value = false
        }, 3000)
        
      } catch (err) {
        console.error('Failed to save config:', err)
        alert('Ошибка при сохранении настроек')
      } finally {
        saving.value = false
      }
    }

    // Сброс к дефолтным настройкам
    const resetToDefault = () => {
      if (confirm('Вы уверены? Все настройки будут сброшены.')) {
        Object.assign(config, {
          // ... default values
        })
      }
    }

    onMounted(() => {
      loadConfig()
    })

    return {
      loading,
      saving,
      saveSuccess,
      config,
      currency,
      experience,
      blacklistText,
      hasChanges,
      saveConfig,
      resetToDefault,
    }
  },
}
</script>

<style scoped>
.search-config-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}

.page-header {
  margin-bottom: 40px;
}

.page-header h1 {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 16px;
  color: #666;
}

/* Save Bar (Sticky) */
.save-bar {
  position: sticky;
  top: 20px;
  z-index: 10;
  background: white;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 32px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn-save {
  padding: 12px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-save:hover:not(:disabled) {
  background: #2563eb;
}

.btn-save:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.save-success {
  color: #10b981;
  font-size: 14px;
  font-weight: 500;
}

/* Form Sections */
.form-section {
  background: white;
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.form-section h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e2e8f0;
}

.form-group {
  margin-bottom: 24px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.hint {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

.form-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.flex-1 {
  flex: 1;
}

/* Checkbox Group */
.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
}

.checkbox-label input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

/* Radio Group */
.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-group-inline {
  display: flex;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
}

.radio-label input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 32px;
}

.btn-primary,
.btn-secondary {
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
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

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 20px;
}
</style>
```

---

## UX/UI Design

### Принципы минимизации клиентского пути

#### Сценарий: Первый запуск поиска

```
Setup Resume → Configure Search → Start Job → Monitor Progress → View Results
     ↓               ↓                ↓              ↓                 ↓
  Шаг 2           Шаг 3a           Шаг 3b         Шаг 3c           Шаг 3d
  10 сек          60 сек          1 клик       Авто (Real-time)   Готово!
  
Общее время: 2-3 минуты активной работы пользователя
Время рассылки: автоматическое (10-60 минут в фоне)
```

#### Ключевые UX решения

1. **Smart Defaults**
   - Все параметры поиска предзаполнены разумными значениями
   - Можно запустить поиск сразу без настройки
   - "Quick Start" кнопка на Dashboard

2. **Progressive Configuration**
   - Базовые настройки (3-4 поля) → Запуск
   - Продвинутые настройки - опционально
   - Accordion для редко используемых параметров

3. **Simple Progress Tracking**
   - Polling обновление статистики (каждые 30 секунд)
   - Показываем только общие цифры (успешно/пропущено/ошибки)
   - Прогресс-бар с процентами
   - Кнопка "Обновить" для ручного обновления

4. **Interview Management**
   - Список всех откликов с возможностью добавить дату собеседования
   - Фильтры: все/с собеседованием/без ответа
   - Календарь предстоящих собеседований
   - Заметки к каждому отклику

5. **Error Recovery**
   - Автоматический retry при сбоях
   - Сохранение прогресса (resume from checkpoint)
   - Понятные сообщения об ошибках

6. **Mobile-First**
   - Запуск задачи с телефона
   - Простой мониторинг прогресса
   - Push-уведомления через Telegram

### UI Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         DASHBOARD                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  📊 Статистика                                        │       │
│  │  ┌─────────┬─────────┬─────────┐                    │       │
│  │  │ Сегодня │ Неделя  │  Месяц  │                    │       │
│  │  │   15    │   73    │   287   │                    │       │
│  │  └─────────┴─────────┴─────────┘                    │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  🎯 Запустить поиск                                   │       │
│  │  Последний запуск: 23 часа назад                      │       │
│  │                                                        │       │
│  │  [⚙️ Настроить параметры]  [🚀 Быстрый запуск]       │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  📋 Последние отклики                                 │       │
│  │  ✓ Яндекс - Go Developer (Score: 92)                 │       │
│  │  ✓ Сбер - Backend Developer (Score: 85)              │       │
│  │  ⊘ Google - скипнуто (Low score: 45)                 │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

                    ↓ Click "Быстрый запуск"

┌─────────────────────────────────────────────────────────────────┐
│                     JOB PROGRESS PAGE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  STATUS: 🔄 В процессе              [🔄 Обновить] [❌ Отменить]  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░   45/200         ││
│  │  22.5% завершено                                              ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  📊 Статистика:                                               ││
│  │                                                               ││
│  │  ✅ Успешно откликнулись:  45                                ││
│  │  ⊘  Пропущено:              12                               ││
│  │  ❌ Ошибки:                  3                                ││
│  │  📝 Всего обработано:       60 вакансий                      ││
│  │                                                               ││
│  │  ⏱️ Начало: 14:05 | Обновлено: 14:23                          ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  💡 Задача выполняется в фоне. Вы можете закрыть эту страницу   │
│     и вернуться позже.                                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

                    ↓ Job Completed

┌─────────────────────────────────────────────────────────────────┐
│                     COMPLETION SCREEN                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🎉 Поиск завершен!                                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  📊 Итоги:                                                    ││
│  │                                                               ││
│  │  ✅ Успешно откликнулись: 195                                ││
│  │  ⊘  Пропущено: 78                                            ││
│  │  ❌ Ошибки: 3                                                 ││
│  │  📝 Всего обработано: 276 вакансий                           ││
│  │                                                               ││
│  │  ⏱️ Время выполнения: 47 минут                                ││
│  │  💰 Стоимость LLM: $0.23                                      ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  [Посмотреть все отклики]  [Запустить еще раз]                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

                    ↓ Click "Посмотреть все отклики"

┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATIONS LIST PAGE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  📋 Мои отклики (195)                                            │
│                                                                   │
│  [Все] [С собеседованием 📅 12] [Без ответа] [Отказ]            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  🏢 Яндекс                                   📅 28 окт, 15:00 ││
│  │  Go Developer                                                 ││
│  │  Score: 92 | Откликнулись: 27 окт                            ││
│  │  [Посмотреть детали] [Изменить дату]                         ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  🏢 Сбер                                   [📅 Добавить дату] ││
│  │  Backend Developer                                            ││
│  │  Score: 88 | Откликнулись: 27 окт                            ││
│  │  [Посмотреть детали]                                          ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  🏢 Тинькофф                                📅 30 окт, 10:00  ││
│  │  Senior Go Developer                                          ││
│  │  Score: 95 | Откликнулись: 27 окт                            ││
│  │  Заметка: Обсудить remote работу                             ││
│  │  [Посмотреть детали] [Изменить дату]                         ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  [Показать еще]                            Стр 1 из 10           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Responsive Design

**Desktop (>1024px):**
- Sidebar navigation
- Real-time progress в центре
- Детали справа

**Tablet (768-1023px):**
- Collapsed sidebar
- Single column layout
- Floating progress bar

**Mobile (<768px):**
- Bottom navigation
- Sticky progress bar вверху
- Swipe для деталей

---

## API Contracts

### Endpoints

#### GET /api/v1/search-config

Получить конфигурацию поиска пользователя.

**Response 200:**
```json
{
  "id": 123,
  "user_id": 456,
  "job_title": "Backend Developer",
  "keywords": "golang, python, api",
  "words_to_exclude": "php, wordpress",
  "search_field": {
    "name": true,
    "company_name": true,
    "description": true
  },
  "area": "Москва, Санкт-Петербург",
  "salary": 200000,
  "only_with_salary": false,
  "currency": { "rur": true, "eur": false, "usd": false },
  "experience": { "doesnt_matter": false, "between_3_and_6": true, "more_than_6": false },
  "employment": { "full": true, "remote": true },
  "schedule": { "full_day": true, "remote": true },
  "max_applies_num": 200,
  "apply_once_at_company": true,
  "job_blacklist": ["Google", "Meta"],
  "fixed_cover_letter": null,
  "updated_at": "2025-10-27T12:00:00Z"
}
```

---

#### PUT /api/v1/search-config

Обновить конфигурацию поиска.

**Request:**
```json
{
  "job_title": "Go Developer",
  "keywords": "golang, kubernetes, microservices",
  "salary": 250000,
  "max_applies_num": 150
}
```

**Response 200:**
```json
{
  "id": 123,
  "updated_at": "2025-10-27T13:00:00Z",
  "status": "success"
}
```

---

#### POST /api/v1/jobs/start

Запустить новую задачу поиска и рассылки откликов.

**Request:**
```json
{
  "force": false
}
```

**Response 200:**
```json
{
  "job": {
    "id": 789,
    "user_id": 456,
    "status": "pending",
    "created_at": "2025-10-27T14:00:00Z"
  },
  "estimated_duration_minutes": 45,
  "message": "Job created and queued for processing"
}
```

**Response 429 (Too Early):**
```json
{
  "error": "too_soon",
  "message": "Последний поиск был 6 часов назад. Следующий запуск возможен через 18 часов.",
  "next_run_available_at": "2025-10-28T08:00:00Z"
}
```

---

#### GET /api/v1/jobs/{id}

Получить статус задачи.

**Response 200:**
```json
{
  "id": 789,
  "user_id": 456,
  "status": "running",
  "total_vacancies": 276,
  "processed_vacancies": 120,
  "success_applies": 95,
  "skipped_vacancies": 20,
  "failed_applies": 5,
  "current_page": 12,
  "started_at": "2025-10-27T14:05:00Z",
  "created_at": "2025-10-27T14:00:00Z",
  "updated_at": "2025-10-27T14:25:00Z"
}
```

---

#### POST /api/v1/jobs/{id}/cancel

Отменить выполнение задачи.

**Response 200:**
```json
{
  "id": 789,
  "status": "cancelled",
  "message": "Job cancelled successfully"
}
```

---

#### GET /api/v1/jobs/{id}/applications

Получить список откликов для задачи.

**Query Parameters:**
- `page` (int, default=1)
- `per_page` (int, default=20, max=100)
- `status` (string: success, skipped, failed)

**Response 200:**
```json
{
  "applications": [
    {
      "id": 1001,
      "vacancy_id": "98765432",
      "company_name": "Яндекс",
      "vacancy_title": "Go Developer",
      "status": "success",
      "llm_score": 92,
      "cover_letter": "Здравствуйте! ...",
      "applied_at": "2025-10-27T14:10:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 95
  }
}
```

---

#### PUT /api/v1/applications/{id}/interview

Установить/обновить дату собеседования для отклика.

**Request:**
```json
{
  "interview_date": "2025-10-28T15:00:00Z",
  "interview_notes": "Обсудить зарплатные ожидания и remote"
}
```

**Response 200:**
```json
{
  "id": 1001,
  "interview_date": "2025-10-28T15:00:00Z",
  "interview_notes": "Обсудить зарплатные ожидания и remote",
  "updated_at": "2025-10-27T16:30:00Z"
}
```

---

#### DELETE /api/v1/applications/{id}/interview

Удалить дату собеседования.

**Response 200:**
```json
{
  "id": 1001,
  "message": "Interview date removed"
}
```

---

#### GET /api/v1/applications/interviews

Получить список предстоящих собеседований.

**Query Parameters:**
- `from` (datetime, default=now)
- `to` (datetime, optional)
- `sort` (string: asc, desc, default=asc)

**Response 200:**
```json
{
  "interviews": [
    {
      "id": 1001,
      "vacancy_id": "98765432",
      "company_name": "Яндекс",
      "vacancy_title": "Go Developer",
      "interview_date": "2025-10-28T15:00:00Z",
      "interview_notes": "Обсудить зарплатные ожидания",
      "applied_at": "2025-10-27T14:10:00Z"
    }
  ],
  "total": 12
}
```

---

## Database Schema

### Таблица: search_configs

```sql
CREATE TABLE search_configs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_title VARCHAR(500) NOT NULL,
    keywords TEXT,
    words_to_exclude TEXT,
    professional_role VARCHAR(255),
    industry VARCHAR(500),
    area VARCHAR(500),
    metro VARCHAR(500),
    salary INTEGER,
    only_with_salary BOOLEAN DEFAULT FALSE,
    
    -- JSON fields for complex structures
    search_field JSONB NOT NULL DEFAULT '{"name": true, "company_name": true, "description": true}',
    currency JSONB NOT NULL DEFAULT '{"rur": true, "eur": false, "usd": false}',
    experience JSONB NOT NULL DEFAULT '{"doesnt_matter": true}',
    employment JSONB NOT NULL DEFAULT '{"full": true}',
    schedule JSONB NOT NULL DEFAULT '{"full_day": true, "remote": true}',
    part_time JSONB DEFAULT '{}',
    vacancy_label JSONB DEFAULT '{}',
    order_by JSONB NOT NULL DEFAULT '{"relevance": true}',
    period JSONB NOT NULL DEFAULT '{"month": true}',
    
    job_blacklist TEXT[] DEFAULT '{}',
    fixed_cover_letter TEXT,
    apply_once_at_company BOOLEAN DEFAULT TRUE,
    skip_companies_with_test BOOLEAN DEFAULT FALSE,
    max_applies_num INTEGER NOT NULL DEFAULT 200,
    max_total_applies_num INTEGER,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_config UNIQUE(user_id)
);

CREATE INDEX idx_search_configs_user_id ON search_configs(user_id);
```

### Таблица: jobs

```sql
CREATE TABLE jobs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    search_config_id BIGINT NOT NULL REFERENCES search_configs(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_vacancies INTEGER DEFAULT 0,
    processed_vacancies INTEGER DEFAULT 0,
    success_applies INTEGER DEFAULT 0,
    skipped_vacancies INTEGER DEFAULT 0,
    failed_applies INTEGER DEFAULT 0,
    current_page INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
```

### Таблица: applications

```sql
CREATE TABLE applications (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vacancy_id VARCHAR(50) NOT NULL,
    company_id VARCHAR(50),
    company_name VARCHAR(500) NOT NULL,
    vacancy_title VARCHAR(500) NOT NULL,
    vacancy_url TEXT NOT NULL,
    vacancy_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL,
    skip_reason TEXT,
    llm_score INTEGER,
    cover_letter TEXT,
    questions_answers JSONB,
    interview_date TIMESTAMP,
    interview_notes TEXT,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('success', 'skipped', 'failed'))
);

CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_vacancy_id ON applications(vacancy_id);
CREATE INDEX idx_applications_company_name ON applications(company_name);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_applied_at ON applications(applied_at DESC);
CREATE INDEX idx_applications_interview_date ON applications(interview_date) WHERE interview_date IS NOT NULL;
```

---

## Progress Tracking

### Подход: Polling вместо WebSocket

**Почему Polling:**
- ✅ Проще в реализации и поддержке
- ✅ Не требует постоянного соединения
- ✅ Меньше нагрузка на сервер
- ✅ Пользователю не нужна детальная информация в реальном времени
- ✅ Достаточно знать общую статистику

**Как работает:**

1. **Frontend** периодически (каждые 30 секунд) опрашивает API:
   ```javascript
   // Автоматический polling
   setInterval(async () => {
     if (job.status === 'running') {
       const updated = await jobApi.getJobStatus(job.id)
       commit('UPDATE_JOB', updated)
     }
   }, 30000)
   ```

2. **Backend** возвращает текущее состояние из БД:
   - Статус задачи (pending, running, completed, failed, cancelled)
   - Успешных откликов
   - Пропущенных вакансий
   - Ошибок
   - Время начала

3. **UI обновляется** автоматически:
   - Прогресс-бар (45/200 = 22.5%)
   - Статистика
   - Время выполнения

4. **Кнопка "Обновить"** для ручного обновления:
   ```javascript
   async function refresh() {
     loading.value = true
     await fetchJobStatus()
     loading.value = false
   }
   ```

**Оптимизация:**
- Polling останавливается когда задача завершена
- При неактивной вкладке (Page Visibility API) - увеличиваем интервал до 60 сек
- При ошибках сети - exponential backoff (30s → 60s → 120s)

---

## Interview Management

### Основной Use Case

Пользователь откликнулся на 200 вакансий → получил приглашения на собеседования → нужно отслеживать даты.

### Функциональность

**1. Добавление даты собеседования:**
```javascript
// API call
PUT /api/v1/applications/{id}/interview
{
  "interview_date": "2025-10-28T15:00:00Z",
  "interview_notes": "Обсудить зарплату и remote"
}
```

**2. Календарь предстоящих собеседований:**
- Фильтр по датам (сегодня, неделя, месяц)
- Сортировка по дате
- Уведомления за день до собеседования (через Telegram)

**3. Заметки к каждому отклику:**
- Что обсудить
- Результат собеседования
- Контакты HR
- Следующие шаги

**4. Статусы собеседований:**
- Назначено (interview_date != null)
- Прошло (interview_date < now)
- Предстоящее (interview_date > now)

### UI Components

**ApplicationCard.vue:**
```vue
<div class="application-card">
  <div class="company">{{ application.company_name }}</div>
  <div class="title">{{ application.vacancy_title }}</div>
  
  <!-- Interview Date -->
  <div v-if="application.interview_date" class="interview-date">
    📅 {{ formatDate(application.interview_date) }}
    <button @click="editInterview">Изменить</button>
  </div>
  <div v-else>
    <button @click="addInterview">📅 Добавить дату собеседования</button>
  </div>
  
  <!-- Notes -->
  <div v-if="application.interview_notes" class="notes">
    {{ application.interview_notes }}
  </div>
</div>
```

**InterviewModal.vue:**
```vue
<div class="modal">
  <h3>Добавить дату собеседования</h3>
  
  <input type="datetime-local" v-model="interviewDate" />
  
  <textarea 
    v-model="interviewNotes" 
    placeholder="Заметки (что обсудить, контакты и т.д.)"
  ></textarea>
  
  <button @click="save">Сохранить</button>
</div>
```

### Backend Logic

**ApplicationService:**
```go
func (s *ApplicationService) SetInterviewDate(
    ctx context.Context,
    applicationID, userID int64,
    interviewDate time.Time,
    notes string,
) error {
    // 1. Check ownership
    app, err := s.appRepo.GetByID(ctx, applicationID)
    if err != nil {
        return err
    }
    if app.UserID != userID {
        return ErrAccessDenied
    }
    
    // 2. Update
    app.InterviewDate = &interviewDate
    if notes != "" {
        app.InterviewNotes = &notes
    }
    app.UpdatedAt = time.Now()
    
    return s.appRepo.Update(ctx, app)
}
```

---

## Последовательность реализации

### Фаза 1: Backend Core (3-4 дня)

**День 1: Models и Repository**
1. ✅ Создать `core/models/search_config.go`
   - Все структуры конфигурации
   - Validation tags
   
2. ✅ Создать `core/models/job.go`
   - Job, Application, Progress models
   
3. ✅ Создать `core/repository/search_config_repo.go`
   - CRUD операции
   - PostgreSQL queries

4. ✅ Создать `core/repository/job_repo.go`
   - CRUD для jobs и applications
   - Queries для статистики

**День 2: Services**
5. ✅ Создать `core/services/search_service.go`
   - Get/Update search config
   - Build search params для hh.ru API
   
6. ✅ Создать `core/services/job_service.go`
   - Start/Cancel/Get job
   - Get applications

**День 3: Worker**
7. ✅ Создать `core/workers/job_worker.go`
   - Process job logic
   - Search vacancies
   - Apply to vacancies
   - LLM integration
   
8. ✅ Создать `core/queue/redis_queue.go`
   - Push/Pop jobs
   - Worker pool

**День 4: HTTP Handlers**
9. ✅ Создать `core/handlers/search_config.go`
   - GET/PUT /api/v1/search-config
   
10. ✅ Создать `core/handlers/job.go`
    - POST /api/v1/jobs/start
    - GET /api/v1/jobs/{id}
    - POST /api/v1/jobs/{id}/cancel
    - GET /api/v1/jobs/{id}/applications
    
11. ✅ Создать `core/handlers/application.go`
    - PUT /api/v1/applications/{id}/interview
    - DELETE /api/v1/applications/{id}/interview
    - GET /api/v1/applications/interviews

### Фаза 2: Frontend (3-4 дня)

**День 1: Search Config Page**
1. ✅ Создать `src/views/SearchConfig.vue`
   - Все секции формы
   - Валидация
   - Сохранение
   
2. ✅ Создать `src/api/search.js`
   - API methods
   
3. ✅ Создать `src/store/modules/search.js`
   - Vuex state management

**День 2: Dashboard с кнопкой запуска**
4. ✅ Обновить `src/views/Dashboard.vue`
   - Кнопка "Запустить поиск"
   - Quick start flow
   - Статистика
   
5. ✅ Создать `src/api/job.js`
   - Job API methods

**День 3: Progress Monitoring и Applications**
6. ✅ Создать `src/views/JobProgress.vue`
   - Simple progress display с polling (каждые 30 сек)
   - Job statistics
   - Cancel и Refresh buttons
   
7. ✅ Создать `src/views/Applications.vue`
   - Список всех откликов
   - Фильтры (все/с собеседованием/без ответа)
   - Добавление/редактирование дат собеседований
   - Заметки к откликам
   
8. ✅ Создать `src/store/modules/job.js`
   - Job state management
   
9. ✅ Создать `src/store/modules/application.js`
   - Applications state management
   - Interview management
   
10. ✅ Создать `src/api/application.js`
    - Application API methods

**День 4: Polish и Integration**
11. ✅ Routing setup
12. ✅ i18n translations
13. ✅ Error handling
14. ✅ Loading states
15. ✅ Polling implementation

### Фаза 3: Testing и Optimization (2-3 дня)

**День 1: Backend Testing**
1. ✅ Unit tests для services
2. ✅ Integration tests для worker
3. ✅ API tests для handlers

**День 2: Frontend Testing**
4. ✅ Component tests
5. ✅ E2E tests для полного flow
6. ✅ Polling mechanism tests
7. ✅ Interview management tests

**День 3: Optimization**
8. ✅ Performance profiling
9. ✅ Database query optimization
10. ✅ API response caching
11. ✅ Polling interval optimization

---

## Метрики успеха

### Performance
- **Job processing time:** 10-60 минут для 200 откликов
- **API response time:** < 500ms
- **Database queries:** < 50ms
- **Polling interval:** 30 секунд (настраиваемо)

### UX
- **Time to start job:** < 2 клика от Dashboard
- **Time to configure:** < 3 минуты
- **Progress updates:** Polling каждые 30 секунд + кнопка "Обновить"
- **Interview management:** < 10 секунд на добавление даты

### Quality
- **Test coverage:** > 80%
- **Zero critical bugs**
- **All edge cases handled**
- **Graceful error recovery**

### Business
- **Success rate:** > 90% успешных откликов
- **User satisfaction:** положительная обратная связь
- **System reliability:** 99.9% uptime

---

## Заключение

Этот документ содержит полное описание Шага 3 (Настройка параметров поиска и рассылка откликов) с детальными инструкциями для реализации.

**Ключевые особенности:**
- ✅ Простой мониторинг прогресса через Polling (без WebSocket)
- ✅ Минимальный клиентский путь (2 клика для запуска)
- ✅ Управление датами собеседований и заметками
- ✅ Фоновая обработка задач через Worker Pool
- ✅ Robust error handling и recovery
- ✅ Масштабируемая архитектура
- ✅ Полная интеграция с существующей логикой

**Основные упрощения по сравнению с первоначальным планом:**
- ❌ Убран WebSocket - используется простой polling
- ✅ Показываем только общую статистику (без деталей текущих вакансий)
- ✅ Добавлен функционал управления датами собеседований

**Общее время реализации:** 8-11 дней  
**Приоритет:** Critical (основная функциональность продукта)

---

**Автор:** Search & Application Flow Documentation  
**Версия:** 2.0 (Упрощенная, без WebSocket)  
**Дата:** 27 октября 2025  
**Изменения:** Убран WebSocket, добавлен polling и управление собеседованиями

