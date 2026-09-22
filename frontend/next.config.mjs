import bundleAnalyzer from '@next/bundle-analyzer'

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Barrel file import 최적화 (Vercel Best Practice: bundle-barrel-imports)
  // lucide-react 등의 barrel import를 빌드 타임에 직접 import로 변환하여
  // 번들 사이즈 절감 및 개발 서버 부팅 속도 향상
  experimental: {
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-icons',
      '@radix-ui/react-avatar',
      '@radix-ui/react-checkbox',
      '@radix-ui/react-dialog',
      '@radix-ui/react-label',
      '@radix-ui/react-progress',
      '@radix-ui/react-select',
      '@radix-ui/react-separator',
      '@radix-ui/react-slider',
      '@radix-ui/react-slot',
      '@radix-ui/react-tabs',
    ],
  },

  // 이미지 최적화 설정
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.supabase.co',
      },
    ],
  },

  // /search → / 리다이렉트
  async redirects() {
    return [
      {
        source: '/search',
        destination: '/',
        permanent: true,
      },
    ];
  },

  // API 프록시 설정 (브라우저 → /api/* → Next.js 서버 → 백엔드)
  //
  // 주의: rewrites() 결과는 `next build` 시점에 .next/routes-manifest.json 에 고정됩니다.
  // 따라서 NEXT_PUBLIC_API_URL 은 컨테이너 실행 시점이 아니라 "빌드 시점"에 있어야 합니다.
  // 값이 비어 있으면 /api/:path* -> /api/:path* 로 자기 자신을 가리켜 모든 API가 404가
  // 되므로(2026-09 dev-cert 장애), 빌드를 실패시켜 잘못된 이미지가 배포되지 않게 합니다.
  async rewrites() {
    const backendUrl = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
    if (!/^https?:\/\/[^/]+/.test(backendUrl)) {
      throw new Error(
        `NEXT_PUBLIC_API_URL 이 비어 있거나 올바른 URL이 아닙니다: "${process.env.NEXT_PUBLIC_API_URL ?? ''}". ` +
          '빌드 시점에 백엔드 주소(예: http://localhost:8000)를 지정하세요.'
      );
    }
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${backendUrl}/health`,
      },
      {
        source: '/docs',
        destination: `${backendUrl}/docs`,
      },
      {
        source: '/openapi.json',
        destination: `${backendUrl}/openapi.json`,
      },
    ];
  },

  // 프로덕션 최적화
  swcMinify: true,
  compiler: {
    // React 프로덕션 최적화
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error', 'warn'] } : false,
  },

  // 번들 최적화
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
    },
  },

  // ESLint 9 flat config는 Next.js 14의 구 ESLint API(useEslintrc, extensions)와 호환 불가
  // granite build 시 ESLint 검사를 건너뛰고, 별도 lint 명령으로 처리
  eslint: {
    ignoreDuringBuilds: true,
  },

  // 트레일링 슬래시 제거 (SEO)
  trailingSlash: false,

  // 파워드 바이 헤더 제거
  poweredByHeader: false,
};

export default withBundleAnalyzer(nextConfig);
