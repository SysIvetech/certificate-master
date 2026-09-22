# ============================================================
# Certificate Master Frontend - Next.js Dockerfile
# ============================================================
# 주의: NEXT_PUBLIC_* 값은 빌드 타임에 브라우저 번들에 그대로
# 하드코딩됩니다. 따라서 dev/prod 환경마다 이 이미지를 별도로
# 빌드해야 합니다 (백엔드처럼 동일 이미지를 dev -> prod로
# 승격할 수 없음). GitHub Actions에서 환경별 build-args로
# 주입합니다 (.github/workflows/deploy.yml 참고).
#
# NEXT_PUBLIC_API_URL 은 next.config.mjs rewrites()(/api/* → 백엔드)의
# 대상 주소로, 역시 빌드 시점에 .next/routes-manifest.json 에 고정됩니다.
# 비어 있으면 빌드가 실패합니다 (컨테이너 실행 시 주입해도 반영되지 않음).
#
# INTERNAL_API_URL 은 서버 컴포넌트(lib/api/server.ts)가 요청 시점에 읽으므로
# 컨테이너 실행 시 docker-compose environment로 주입하면 됩니다.
# ============================================================

FROM node:20-alpine AS base
RUN corepack enable

# ------------------------------------------------------------
# Stage 1: Dependencies
# ------------------------------------------------------------
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ------------------------------------------------------------
# Stage 2: Build
# ------------------------------------------------------------
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 클라이언트 번들에 포함되는 공개 환경 변수 (빌드 타임 고정)
ARG NEXT_PUBLIC_AUTH_ENABLED=false
ARG NEXT_PUBLIC_AUTH_API_URL
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
ARG NEXT_PUBLIC_NAVER_SITE_VERIFICATION
ARG NEXT_PUBLIC_GA_MEASUREMENT_ID
ARG NEXT_PUBLIC_GTM_ID
ENV NEXT_PUBLIC_AUTH_ENABLED=$NEXT_PUBLIC_AUTH_ENABLED \
    NEXT_PUBLIC_AUTH_API_URL=$NEXT_PUBLIC_AUTH_API_URL \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION=$NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION \
    NEXT_PUBLIC_NAVER_SITE_VERIFICATION=$NEXT_PUBLIC_NAVER_SITE_VERIFICATION \
    NEXT_PUBLIC_GA_MEASUREMENT_ID=$NEXT_PUBLIC_GA_MEASUREMENT_ID \
    NEXT_PUBLIC_GTM_ID=$NEXT_PUBLIC_GTM_ID \
    NEXT_TELEMETRY_DISABLED=1

RUN pnpm build

# ------------------------------------------------------------
# Stage 3: Runtime
# ------------------------------------------------------------
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=5100

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.mjs ./next.config.mjs

RUN mkdir -p /app/logs && chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 5100

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD node -e "require('http').get('http://localhost:5100/', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["pnpm", "start"]
