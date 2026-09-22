"""FastAPI application entry point.

This module creates and configures the FastAPI application instance.
"""

import logging
import logging.handlers
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.chroma import router as chroma_router
from app.api.v1 import router as api_v1_router
from app.core.config import get_settings


def setup_logging(settings) -> None:
    """로깅 설정. LOG_DIR이 지정되면 파일 로깅도 활성화."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()

    # stdout 핸들러
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(stream_handler)

    # 파일 핸들러 (LOG_DIR 설정 시)
    if settings.LOG_DIR:
        try:
            os.makedirs(settings.LOG_DIR, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                os.path.join(settings.LOG_DIR, "backend.log"),
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)

            # 에러 전용 로그
            error_handler = logging.handlers.RotatingFileHandler(
                os.path.join(settings.LOG_DIR, "error.log"),
                maxBytes=50 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(error_handler)
        except PermissionError:
            root_logger.warning(
                f"파일 로깅 설정 실패: '{settings.LOG_DIR}' 쓰기 권한 없음. "
                f"stdout만 사용합니다."
            )


setup_logging(get_settings())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    print(f"Starting Certificate Master API in {settings.ENVIRONMENT} mode")

    # BM25 인덱스 빌드 (하이브리드 검색용)
    try:
        from app.core.database import get_db
        from app.models.certificate import Certificate
        from app.services.search.bm25_service import get_bm25_service

        db = next(get_db())
        try:
            certs = db.query(Certificate).filter(Certificate.overview.isnot(None)).all()

            cert_dicts = []
            for cert in certs:
                cert_dict = cert.to_dict() if hasattr(cert, "to_dict") else {}
                cert_dict["id"] = str(cert.id)
                cert_dicts.append(cert_dict)

            bm25 = get_bm25_service()
            bm25.build_index(cert_dicts)
            logger.info(f"BM25 인덱스 빌드 완료: {len(cert_dicts)}건")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"BM25 인덱스 빌드 실패 (서비스는 계속 동작): {e}")

    yield
    # Shutdown
    print("Shutting down Certificate Master API")


settings = get_settings()

app = FastAPI(
    title="Certificate Master API",
    description="Backend API for Certificate Master - Korean certificate information platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
# Always use explicit origins from config to support credentials
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

logger.info("📋 CORS Configuration:")
logger.info(f"  - Environment: {settings.ENVIRONMENT}")
logger.info(f"  - Origins: {cors_origins}")
logger.info("  - Credentials: True")
logger.info("  - Methods: *")
logger.info("  - Headers: *")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    logger.info("=" * 80)
    logger.info(f"🌍 Incoming Request: {request.method} {request.url.path}")
    logger.info(f"📍 Origin: {request.headers.get('origin', 'N/A')}")
    logger.info(
        f"🔑 Authorization: {request.headers.get('authorization', 'N/A')[:30]}..."
    )
    logger.info(f"📦 Content-Type: {request.headers.get('content-type', 'N/A')}")

    response = await call_next(request)

    logger.info(f"📤 Response Status: {response.status_code}")
    logger.info("=" * 80)

    return response


# Include API router
app.include_router(api_v1_router, prefix="/api")
app.include_router(chroma_router)


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Health status of the API service.
    """
    return {
        "status": "healthy",
        "service": "certificate-master-api",
        "environment": settings.ENVIRONMENT,
    }


# 모니터링 대시보드용 표준 헬스체크. 어느 origin에서도 조회 가능.
# 기존 /health 는 앱 내부 규약이 다르므로 그대로 두고 별도 엔드포인트 추가.
@app.get("/healthz")
async def healthz():
    return JSONResponse(
        content={
            "status": "ok",
            "service": "cert.i-ve.ai",
            "version": "0.1.0",
            "commit": os.environ.get("GIT_COMMIT", "unknown"),
            "builtAt": os.environ.get("BUILD_TIMESTAMP"),
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
    )


@app.get("/health/db")
async def database_health_check():
    """Database health check endpoint.

    Returns:
        Database connection status (MariaDB).
    """
    from sqlalchemy import text

    from app.core.database import get_engine

    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM certificates"))
            count = result.fetchone()[0]
        return {
            "status": "healthy",
            "database": "connected",
            "has_data": count > 0,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Certificate Master API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
