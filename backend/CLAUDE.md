# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Backend - Certificate Master

자격증 정보 + 맞춤형 학습 플랜 + AI 가이드 플랫폼 백엔드

## Tech Stack

| Layer | Stack |
|-------|-------|
| Framework | FastAPI (Python 3.11+) |
| Database | MariaDB (SQLAlchemy) |
| Auth | ivetech 통합 인증 서비스(auth-service) JWT 검증 (`AUTH_ENABLED`로 on/off) |
| Vector Store | ChromaDB |
| AI/LLM | OpenAI API (GPT-5-nano, text-embedding-3-small) |
| Search | SearXNG (메타 검색 엔진) |

---

## Development Commands

```bash
# 의존성 설치
uv sync --extra dev

# 개발 서버 실행
uv run uvicorn app.main:app --reload --port 8000

# 전체 테스트
uv run pytest

# 단일 테스트 파일
uv run pytest tests/unit/test_analytics_service.py -v

# 특정 테스트 함수
uv run pytest tests/unit/test_analytics_service.py::test_function_name -v

# 테스트 (커버리지)
uv run pytest --cov=app --cov-report=html

# 마커별 테스트
uv run pytest -m unit        # 단위 테스트
uv run pytest -m integration # 통합 테스트
uv run pytest -m e2e         # E2E 테스트 (서버 실행 필요)

# SearXNG 실행 (Docker)
docker run -d -p 8888:8080 searxng/searxng

# 데이터 강화
uv run python -m scripts.enrich_certificates --test  # 테스트
uv run python -m scripts.enrich_certificates --all   # 전체
```

---

## Architecture

### Protocol Pattern (의존성 역전)

서비스는 Protocol 인터페이스 + Factory 패턴을 사용:

```
services/
├── search/
│   ├── protocol.py         # SearchServiceProtocol (인터페이스)
│   ├── factory.py          # get_search_service() → 구현체 반환
│   └── searxng_search.py   # SearXNG 구현체
├── embedding/
│   ├── protocol.py         # EmbeddingServiceProtocol
│   ├── factory.py          # get_embedding_service()
│   └── service.py          # OpenAI/Local 구현체
```

**새 서비스 추가 시**: Protocol 정의 → Factory 등록 → 구현체 작성

### 핵심 서비스 흐름

```
API Endpoint → Service → Protocol → 구현체 (SearXNG/OpenAI/ChromaDB)
                 ↓
            LLM Service (GPT-5-nano)
```

### 데이터 흐름

1. **검색**: `certificates.py` → `SearXNGSearchService` → 메타 검색 → 크롤링
2. **추천**: `recommendations.py` → `VectorStore` (ChromaDB) → LLM 프롬프트
3. **학습계획**: `study_plans.py` → `StudyPlanService` → LLM 자동 생성

---

## Test Fixtures (conftest.py)

| Fixture | Scope | 설명 |
|---------|-------|------|
| `client` | module | FastAPI TestClient |
| `authenticated_client` | function | 인증 우회된 TestClient |
| `test_db_session` | function | SQLAlchemy Session |
| `mock_user` | function | MockUser 인스턴스 |
| `sample_certificate_data` | function | 테스트용 자격증 데이터 |
| `clean_test_certificates` | function | TEST_ prefix 데이터 정리 |

---

## Code Style

- **Formatter**: Black (line-length: 88)
- **Linter**: Ruff
- **Type Hints**: 필수
- **Indent**: 4 spaces
- **Docstring**: 한글

---

## Troubleshooting

### CORS 에러
- 500 에러가 CORS 에러로 표시될 수 있음
- 실제 원인 확인: 서버 로그 확인

### 인증 (ivetech auth-service)
- 로그인/회원가입/토큰 발급은 auth-service(`dev-auth.ivetech.co.kr`)가 담당, 이 백엔드는 access token 검증만 수행
- `AUTH_ENABLED=false`(기본값)면 `CurrentUser`가 항상 MockUser
- `AUTH_ENABLED=true`면 `JWT_SECRET`(auth-service의 `jwt.secret`과 동일한 Base64 값) 필수
- 로그아웃 블랙리스트(Redis)는 확인하지 않으므로, 로그아웃한 토큰도 만료(기본 30분)까지 유효

### SearXNG 연결 실패
```bash
curl http://localhost:8888/healthz  # 상태 확인
docker restart searxng              # Docker 재시작
```
