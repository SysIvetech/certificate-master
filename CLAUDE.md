# Certificate Master

자격증 정보 + 맞춤형 학습 플랜 + AI 가이드 플랫폼

- **Dev Server**: https://dev-cert.i-ve.ai
- **Status**: MVP Phase 2 (AI Features)

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | FastAPI, MariaDB, ChromaDB, GPT-5-nano |
| Auth | ivetech 통합 인증 서비스 (auth-service, JWT) |
| Frontend | Next.js 14, TypeScript, Tailwind, shadcn/ui, Zustand, TanStack Query |
| Deploy | Docker Compose (backend:8000, frontend:5100) |

## Structure

```
backend/app/
├── api/v1/          # certificates, study_plans, checkins, analytics, recommendations
├── core/            # config, database, security(auth-service JWT 검증)
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
└── services/        # Business logic (analytics, llm, vector_store, embedding)

frontend/src/
├── app/             # Pages: search, certificates/[id], dashboard, study-plans, analytics
├── components/      # ui, auth, certificate, recommend, study-plan, dashboard, analytics
├── hooks/           # use-auth, use-certificates, use-study-plans, use-checkins
├── lib/api/         # API client
└── stores/          # Zustand stores
```

## Commands

```bash
# Backend
cd backend && uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
uv run pytest

# Frontend
cd frontend && npm install && npm run dev
npm test  # Playwright E2E

# Deploy
cd deploy && docker-compose up -d
```

## API Endpoints

- `GET /api/v1/certificates/search|autocomplete|categories|{id}`
- `GET|POST /api/v1/study-plans` | `GET|PATCH|DELETE /api/v1/study-plans/{id}`
- `GET|POST /api/v1/checkins` | `GET /api/v1/checkins/{id}/stats|streak`
- `GET /api/v1/analytics/progress|learning-pattern/{study_plan_id}`
- `POST /api/v1/recommendations`

## Code Style

- **Python**: Black, Ruff, Type hints, 4 spaces
- **TypeScript**: ESLint, Strict mode, 2 spaces
- **Git**: `feat|fix|refactor|docs|test|chore: message`

## Env Variables

```env
# Backend (.env)
AUTH_ENABLED, JWT_SECRET   # ivetech auth-service JWT 검증
MARIADB_HOST, MARIADB_PORT, MARIADB_USER, MARIADB_PASSWORD, MARIADB_DATABASE
CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION_NAME
OPENAI_API_KEY

# Frontend (.env.local)
NEXT_PUBLIC_AUTH_ENABLED, NEXT_PUBLIC_AUTH_API_URL, NEXT_PUBLIC_API_URL
```

## Skills

| 스킬 | 설명 |
|------|------|
| verify-api-consistency | 백엔드 API 엔드포인트의 인증/에러처리/응답형식 일관성 검증 |
| verify-frontend-seo | 프론트엔드 페이지의 메타데이터, JSON-LD, OG, canonical URL 검증 |
| verify-type-safety | TypeScript 타입 안전성 검증 (any 금지, Props 타이핑, API 타이핑) |

## Docs

- [Backend Guide](./backend/CLAUDE.md) | [Frontend Guide](./frontend/CLAUDE.md) | [Deploy Guide](./deploy/README.md)
