# Технологический стек

Обоснование выбора технологий для Go-реализации XX Auto Jobs Applier.

## Backend

### 1. Go (Golang)

**Версия:** 1.21+

**Почему Go:**
- ✅ **Производительность** - в 10-50 раз быстрее Python для concurrent operations
- ✅ **Concurrency** - goroutines идеальны для параллельной обработки вакансий
- ✅ **Компиляция** - один бинарный файл, легко деплоить
- ✅ **Memory efficiency** - меньше потребление памяти чем Python
- ✅ **Стандартная библиотека** - HTTP server, JSON, networking из коробки
- ✅ **Typing** - статическая типизация снижает количество ошибок
- ✅ **Ecosystem** - отличные библиотеки для web, database, Redis

**Альтернативы:**
- ❌ **Node.js** - медленнее Go, callback hell, хуже для CPU-intensive tasks
- ❌ **Java** - слишком тяжеловесный, медленный старт, больше памяти
- ❌ **Rust** - сложнее разработка, меньше библиотек, дольше time-to-market

### 2. Web Framework

**Выбор: Gin vs Echo**

#### Gin (рекомендуется)

```go
import "github.com/gin-gonic/gin"

router := gin.Default()
router.GET("/api/v1/users/me", handlers.GetCurrentUser)
router.POST("/api/v1/auth/login", handlers.Login)
```

**Преимущества:**
- ✅ Самый популярный (50k+ stars на GitHub)
- ✅ Быстрый (benchmarks показывают высокую производительность)
- ✅ Простой API
- ✅ Middleware ecosystem
- ✅ JSON валидация из коробки
- ✅ Отличная документация

#### Echo (альтернатива)

```go
import "github.com/labstack/echo/v4"

e := echo.New()
e.GET("/api/v1/users/me", handlers.GetCurrentUser)
```

**Преимущества:**
- ✅ Минималистичный
- ✅ Хорошая производительность
- ✅ Встроенный WebSocket support

**Решение:** Использовать **Gin** для MVP (больше community support)

### 3. ORM vs SQL Builder

**Выбор: GORM vs sqlx vs pgx**

#### GORM (рекомендуется для MVP)

```go
import "gorm.io/gorm"

type User struct {
    ID        uint
    Email     string
    CreatedAt time.Time
}

db.Create(&user)
db.First(&user, 1)
db.Where("email = ?", email).First(&user)
```

**Преимущества:**
- ✅ Полноценный ORM (как Django ORM в Python)
- ✅ Auto migrations
- ✅ Associations (has many, belongs to)
- ✅ Hooks (BeforeCreate, AfterUpdate)
- ✅ Быстрая разработка

**Недостатки:**
- ❌ Производительность ниже чем raw SQL
- ❌ Сложные запросы требуют raw SQL

#### sqlx (для production оптимизаций)

```go
import "github.com/jmoiron/sqlx"

db.Get(&user, "SELECT * FROM users WHERE id = $1", userID)
db.Select(&users, "SELECT * FROM users WHERE subscription_end > NOW()")
```

**Преимущества:**
- ✅ Тонкая обёртка над database/sql
- ✅ Высокая производительность
- ✅ Полный контроль над SQL

**Недостатки:**
- ❌ Больше boilerplate кода
- ❌ Нет auto migrations

**Решение:** 
- **MVP:** GORM (быстрая разработка)
- **Post-MVP:** Переписать критичные запросы на sqlx

### 4. PostgreSQL Driver

**Выбор:** pgx (через GORM)

```go
import (
    "gorm.io/driver/postgres"
    "gorm.io/gorm"
)

dsn := "host=localhost user=user password=pass dbname=db port=5432"
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
```

**Почему pgx:**
- ✅ Нативный PostgreSQL драйвер (быстрее pq)
- ✅ Поддержка prepared statements
- ✅ Connection pooling
- ✅ LISTEN/NOTIFY support

### 5. Redis Client

**Выбор:** go-redis

```go
import "github.com/redis/go-redis/v9"

rdb := redis.NewClient(&redis.Options{
    Addr: "localhost:6379",
})

rdb.LPush(ctx, "jobs:pending", jobJSON)
rdb.BRPop(ctx, 0, "jobs:worker1")
```

**Почему go-redis:**
- ✅ Самая популярная библиотека (17k+ stars)
- ✅ Поддержка Redis Cluster
- ✅ Pipelining и transactions
- ✅ Pub/Sub
- ✅ Context support

### 6. Authentication

**JWT:** golang-jwt/jwt

```go
import "github.com/golang-jwt/jwt/v5"

claims := jwt.MapClaims{
    "user_id": userID,
    "email":   email,
    "exp":     time.Now().Add(24 * time.Hour).Unix(),
}

token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
tokenString, _ := token.SignedString([]byte(jwtSecret))
```

**OAuth:** golang.org/x/oauth2

```go
import "golang.org/x/oauth2"

config := &oauth2.Config{
    ClientID:     hhClientID,
    ClientSecret: hhClientSecret,
    Endpoint: oauth2.Endpoint{
        AuthURL:  "https://hh.ru/oauth/authorize",
        TokenURL: "https://hh.ru/oauth/token",
    },
}
```

### 7. Validation

**go-playground/validator**

```go
import "github.com/go-playground/validator/v10"

type SearchConfig struct {
    JobTitle   string `validate:"required,min=3,max=255"`
    MaxApplies int    `validate:"required,gte=1,lte=500"`
    Email      string `validate:"required,email"`
}

validate := validator.New()
err := validate.Struct(searchConfig)
```

### 8. HTTP Client

**Стандартная библиотека + retryablehttp**

```go
import "github.com/hashicorp/go-retryablehttp"

client := retryablehttp.NewClient()
client.RetryMax = 3
client.RetryWaitMin = 1 * time.Second

resp, err := client.Get("https://api.hh.ru/vacancies")
```

**Для hh.ru API:**
```go
type HHClient struct {
    client       *retryablehttp.Client
    accessToken  string
    refreshToken string
}

func (c *HHClient) GetVacancies(params VacancySearchParams) ([]Vacancy, error) {
    req, _ := retryablehttp.NewRequest("GET", "https://api.hh.ru/vacancies", nil)
    req.Header.Set("Authorization", "Bearer "+c.accessToken)
    // ...
}
```

---

## Selenium Alternative

### Chromedp vs Rod

**Chromedp (рекомендуется)**

```go
import "github.com/chromedp/chromedp"

ctx, cancel := chromedp.NewContext(context.Background())
defer cancel()

var value string
err := chromedp.Run(ctx,
    chromedp.Navigate("https://hh.ru/applicant/resumes"),
    chromedp.WaitVisible("#answer-form"),
    chromedp.SetValue("#question-1", answer1),
    chromedp.Click("#submit-button"),
)
```

**Преимущества:**
- ✅ Нативная Go библиотека (без внешних зависимостей)
- ✅ Использует Chrome DevTools Protocol
- ✅ Высокая производительность
- ✅ Context-based API (легко таймауты и отмены)

**Rod (альтернатива)**

```go
import "github.com/go-rod/rod"

browser := rod.New().MustConnect()
page := browser.MustPage("https://hh.ru")
page.MustElement("#question-1").MustInput(answer1)
page.MustElement("#submit-button").MustClick()
```

**Преимущества:**
- ✅ Более высокоуровневый API
- ✅ Автоматический retry
- ✅ Лучше для скрейпинга

**Решение:** **Chromedp** (более контролируемый, легче отладка)

---

## LLM Integration

### LangChain Go vs Нативные SDK

**Выбор: Нативные SDK**

#### Google Gemini

```go
import "github.com/google/generative-ai-go/genai"

ctx := context.Background()
client, _ := genai.NewClient(ctx, option.WithAPIKey(apiKey))
model := client.GenerativeModel("gemini-2.0-flash")

resp, _ := model.GenerateContent(ctx, genai.Text(prompt))
text := resp.Candidates[0].Content.Parts[0].(genai.Text)
```

#### OpenAI

```go
import "github.com/sashabaranov/go-openai"

client := openai.NewClient(apiKey)
resp, _ := client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
    Model: openai.GPT4oMini,
    Messages: []openai.ChatCompletionMessage{
        {Role: "system", Content: systemPrompt},
        {Role: "user", Content: userPrompt},
    },
})

answer := resp.Choices[0].Message.Content
```

#### GigaChat (Сбер)

```go
// Использовать REST API через HTTP client
type GigaChatClient struct {
    client *http.Client
    token  string
}

func (c *GigaChatClient) Generate(prompt string) (string, error) {
    body := map[string]interface{}{
        "model": "GigaChat",
        "messages": []map[string]string{
            {"role": "user", "content": prompt},
        },
    }
    // POST https://gigachat.devices.sberbank.ru/api/v1/chat/completions
}
```

**Почему не LangChain Go:**
- ❌ Ещё не стабильный (early stage)
- ❌ Ограниченная функциональность
- ❌ Лучше использовать нативные SDK

---

## Frontend

### React vs Vue.js

**Выбор: React** (рекомендуется)

**Почему React:**
- ✅ Самое большое сообщество
- ✅ Больше готовых компонентов (Material-UI, Ant Design)
- ✅ React Query для кэширования API запросов
- ✅ Next.js для SSR (если понадобится)

**Tech Stack:**
```
React 18+
TypeScript
Vite (build tool)
React Router (navigation)
React Query (data fetching)
Material-UI или Ant Design (UI components)
Zustand или Redux Toolkit (state management)
Socket.io-client (WebSocket для real-time updates)
```

**Пример:**
```tsx
import { useQuery } from '@tanstack/react-query'
import { getApplications } from '@/api'

function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: getApplications
  })

  if (isLoading) return <Spinner />

  return (
    <div>
      <h1>Мои отклики</h1>
      {data.applications.map(app => (
        <ApplicationCard key={app.id} application={app} />
      ))}
    </div>
  )
}
```

---

## Infrastructure

### 1. Database

**PostgreSQL 15+**

**Почему PostgreSQL:**
- ✅ ACID гарантии
- ✅ JSONB для гибких структур (vacancy_data, questions_answers)
- ✅ Полнотекстовый поиск
- ✅ Партиционирование таблиц (для масштабирования)
- ✅ Репликация (Master-Slave)
- ✅ Отличная производительность

**Расширения:**
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- UUID генерация
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Полнотекстовый поиск
```

### 2. Cache & Queue

**Redis 7+**

**Использование:**
- ✅ Job queue (FIFO через Lists)
- ✅ Cache (LLM ответы, user sessions)
- ✅ Rate limiting (counters с TTL)
- ✅ Pub/Sub (real-time уведомления)
- ✅ Worker healthcheck (Hash с TTL)

**Конфигурация:**
```redis
maxmemory 2gb
maxmemory-policy allkeys-lru  # Eviction policy
appendonly yes                # Persistence
```

### 3. Message Broker (опционально)

**RabbitMQ vs Redis Streams**

**MVP:** Redis Streams (проще, уже используется Redis)

**Post-MVP:** RabbitMQ (если нужны сложные routing и guarantees)

### 4. Monitoring

**Prometheus + Grafana**

```go
import "github.com/prometheus/client_golang/prometheus"

var (
    applicationsTotal = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "applications_total",
            Help: "Total applications",
        },
        []string{"status"},
    )
)

func init() {
    prometheus.MustRegister(applicationsTotal)
}

// В коде
applicationsTotal.WithLabelValues("success").Inc()
```

**Grafana Dashboards:**
- Business metrics (users, applications, revenue)
- Technical metrics (latency, errors, throughput)
- Cost metrics (LLM cost per user, per application)

### 5. Logging

**Zerolog или Zap**

**Zerolog (рекомендуется - быстрее)**

```go
import "github.com/rs/zerolog/log"

log.Info().
    Int64("user_id", userID).
    Str("vacancy_id", vacancyID).
    Float64("llm_score", 75.5).
    Msg("Application submitted")
```

**Централизованное хранение:**
- **MVP:** Файлы + ротация (lumberjack)
- **Post-MVP:** ELK Stack или Grafana Loki

### 6. Configuration

**Viper**

```go
import "github.com/spf13/viper"

viper.SetConfigName("config")
viper.SetConfigType("yaml")
viper.AddConfigPath(".")

viper.AutomaticEnv() // Читать из ENV variables

dbHost := viper.GetString("database.host")
redisURL := viper.GetString("redis.url")
```

**Приоритет:**
1. ENV variables (для production secrets)
2. config.yaml (для defaults)
3. Flags (для overrides)

---

## External Services

### 1. ЮКасса (YooKassa)

**SDK:** yookassa-sdk-go (unofficial но популярный)

```go
import "github.com/rvinnie/yookassa-sdk-go/yookassa"

client := yookassa.NewClient("shopID", "secretKey")

payment, _ := client.CreatePayment(yookassa.Payment{
    Amount: yookassa.Amount{Value: "500.00", Currency: "RUB"},
    Confirmation: yookassa.Confirmation{
        Type:      "redirect",
        ReturnURL: "https://yourapp.com/billing/success",
    },
})
```

### 2. Telegram Bot API

**tgbotapi**

```go
import tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"

bot, _ := tgbotapi.NewBotAPI(token)
bot.Debug = true

msg := tgbotapi.NewMessage(chatID, "🎉 Новое приглашение на собеседование!")
bot.Send(msg)
```

**Для OAuth:** telegram-login-widget (JS на фронте) + верификация hash на бэкенде

### 3. Email (опционально)

**SMTP через gomail**

```go
import "gopkg.in/gomail.v2"

m := gomail.NewMessage()
m.SetHeader("From", "noreply@yourapp.com")
m.SetHeader("To", user.Email)
m.SetHeader("Subject", "Подписка активирована")
m.SetBody("text/html", emailBody)

d := gomail.NewDialer("smtp.gmail.com", 587, smtpUser, smtpPass)
d.DialAndSend(m)
```

---

## Development Tools

### 1. Dependency Management

**Go Modules** (встроено в Go)

```bash
go mod init github.com/yourcompany/auto-jobs-applier
go mod tidy
go mod vendor  # Для vendor зависимостей
```

### 2. Testing

**Стандартная библиотека + testify**

```go
import (
    "testing"
    "github.com/stretchr/testify/assert"
)

func TestCreateUser(t *testing.T) {
    user := CreateUser("test@example.com", "password")
    assert.NotNil(t, user)
    assert.Equal(t, "test@example.com", user.Email)
}
```

**Mock генерация:** gomock или mockery

### 3. Linting

**golangci-lint** (агрегатор линтеров)

```yaml
# .golangci.yml
linters:
  enable:
    - govet
    - errcheck
    - staticcheck
    - gosimple
    - ineffassign
    - unused
    - gofmt
    - goimports
```

### 4. Code Generation

**go generate для:**
- Mock генерация (mockgen)
- Swagger docs (swag)
- SQL queries (sqlc) - альтернатива GORM

### 5. Hot Reload

**air**

```toml
# .air.toml
[build]
  cmd = "go build -o ./tmp/main ."
  bin = "tmp/main"
  include_ext = ["go", "yaml"]
  exclude_dir = ["tmp", "vendor"]
```

```bash
air  # Автоматический перезапуск при изменениях
```

---

## Deployment

### MVP: Docker Compose

**Dockerfile (multi-stage build):**

```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

# Run stage
FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE 8080
CMD ["./main"]
```

**docker-compose.yml:** См. [architecture-go.md](architecture-go.md#deployment)

### Production: Kubernetes

**Helm Charts** для управления deployments

```bash
helm install auto-jobs-applier ./helm-charts
helm upgrade auto-jobs-applier ./helm-charts
```

---

## CI/CD

**GitHub Actions**

```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.21'
      - run: go test -v -race -coverprofile=coverage.out ./...
      - run: go tool cover -html=coverage.out -o coverage.html

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: golangci/golangci-lint-action@v3
        with:
          version: latest

  build:
    needs: [test, lint]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: registry.yourcompany.com/core:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/core core=registry.yourcompany.com/core:${{ github.sha }}
```

---

## Cost Estimation

### Development

| Инструмент | Стоимость |
|-----------|-----------|
| Go | Бесплатно |
| PostgreSQL | Бесплатно |
| Redis | Бесплатно |
| Все библиотеки | Бесплатно (Open Source) |

### Production (месяц)

| Сервис | Конфигурация | Стоимость |
|--------|--------------|-----------|
| **VPS (Core)** | 4 vCPU, 8GB RAM | $40 |
| **VPS (Workers)** | 2 vCPU, 4GB RAM × 5 | $100 |
| **PostgreSQL** | Managed (50GB) | $30 |
| **Redis** | Managed (2GB) | $15 |
| **Domain + SSL** | - | $10 |
| **Monitoring** | Grafana Cloud | $0-50 |
| **LLM API** | Gemini (зависит от usage) | $100-500 |
| **Telegram Bot** | Бесплатно | $0 |
| **ЮКасса** | 2.8% от оборота | % |
| **ИТОГО** | - | **$295-745/мес** |

**При 10,000 MAU:**
- Больше workers (30-50) → $600-1000
- Больше LLM расходов → $500-2000
- **ИТОГО:** $1,500-3,500/мес

**Revenue (при подписке 500₽/мес):**
- 10% conversion trial → paid = 1,000 платных
- 1,000 * 500₽ = 500,000₽/мес ≈ $5,000
- **Profit:** $5,000 - $3,500 = **$1,500/мес**

---

## Заключение

Технологический стек спроектирован для:

✅ **Быстрой разработки MVP** (3-4 месяца)  
✅ **Масштабируемости** (до 100k+ пользователей)  
✅ **Надёжности** (мониторинг, retry, graceful shutdown)  
✅ **Экономичности** (open source инструменты)  
✅ **Maintainability** (чистый код, типизация, тесты)

**Следующий шаг:** Начать разработку Core модуля (API Gateway + User Management)

---

**Автор:** Tech Stack Documentation  
**Версия:** 1.0  
**Дата:** 22 октября 2025

