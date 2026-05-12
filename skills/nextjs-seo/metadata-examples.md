# Metadata API 상세 코드 패턴

Next.js App Router의 Metadata API를 활용한 SEO 메타데이터 구현 예시 모음.

---

## 목차

1. [Root Layout 기본 설정](#1-root-layout-기본-설정)
2. [정적 페이지 메타데이터](#2-정적-페이지-메타데이터)
3. [동적 페이지 (generateMetadata)](#3-동적-페이지-generatemetadata)
4. [SEO 유틸리티 함수 (lib/seo.ts)](#4-seo-유틸리티-함수)
5. [동적 OG 이미지 (ImageResponse)](#5-동적-og-이미지)
6. [sitemap.ts](#6-sitemapTs)
7. [robots.ts](#7-robotsts)
8. [다국어 메타데이터](#8-다국어-메타데이터)

---

## 1. Root Layout 기본 설정

```tsx
// app/layout.tsx
import type { Metadata } from 'next';

const SITE_URL = 'https://example.com';
const SITE_NAME = 'My App';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    template: '%s | ' + SITE_NAME,
    default: SITE_NAME + ' - 사이트 핵심 설명',
  },
  description: '사이트를 대표하는 설명. 155자 이내. 핵심 키워드를 자연스럽게 포함.',
  keywords: ['키워드1', '키워드2', '키워드3'],
  authors: [{ name: '작성자명' }],
  creator: '작성자명',
  openGraph: {
    type: 'website',
    locale: 'ko_KR',
    url: SITE_URL,
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: '소셜 공유 시 표시될 설명',
    images: [
      {
        url: '/og-image.png', // metadataBase 기준 상대 경로
        width: 1200,
        height: 630,
        alt: SITE_NAME,
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: SITE_NAME,
    description: '트위터 공유 시 표시될 설명',
    images: ['/og-image.png'],
    // creator: '@twitter_handle', // 있으면 추가
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: SITE_URL,
  },
  verification: {
    // google: 'google-site-verification-code',
    // naver: 'naver-site-verification-code',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

**핵심 포인트:**
- `metadataBase`가 없으면 OG 이미지 등의 상대 URL이 절대 URL로 변환되지 않아 소셜 플랫폼에서 이미지를 못 불러온다
- `title.template`에 `%s`는 하위 페이지의 title로 치환된다
- `title.default`는 하위 페이지에서 title을 정의하지 않았을 때 사용된다

---

## 2. 정적 페이지 메타데이터

```tsx
// app/about/page.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '소개',           // → "소개 | My App" (template 적용)
  description: '이 서비스에 대한 상세 소개. 무엇을 하는 서비스인지 155자 이내로.',
  openGraph: {
    title: '소개 - My App',
    description: '이 서비스에 대한 상세 소개.',
    url: '/about',
  },
  alternates: {
    canonical: '/about',
  },
};

export default function AboutPage() {
  return <main>...</main>;
}
```

**주의:** 정적 페이지에는 `generateMetadata`를 쓰지 않는다 — 불필요한 런타임 오버헤드.

---

## 3. 동적 페이지 (generateMetadata)

### 기본 패턴

```tsx
// app/quiz/[slug]/page.tsx
import type { Metadata, ResolvingMetadata } from 'next';
import { notFound } from 'next/navigation';

type Props = {
  params: Promise<{ slug: string }>;
};

// 빌드 타임에 정적 생성할 경로 지정
export async function generateStaticParams() {
  const quizzes = await getQuizzes();
  return quizzes.map((quiz) => ({ slug: quiz.slug }));
}

// 동적 메타데이터 생성
export async function generateMetadata(
  { params }: Props,
  parent: ResolvingMetadata
): Promise<Metadata> {
  const { slug } = await params;
  const quiz = await getQuizBySlug(slug);

  if (!quiz) return {};

  // parent metadata에서 이전 OG 이미지를 가져올 수도 있다
  // const previousImages = (await parent).openGraph?.images || [];

  return {
    title: quiz.title,
    description: quiz.description,
    openGraph: {
      title: quiz.title,
      description: quiz.description,
      url: `/quiz/${slug}`,
      type: 'website',
      images: [
        {
          url: quiz.ogImage || `/api/og?title=${encodeURIComponent(quiz.title)}`,
          width: 1200,
          height: 630,
          alt: quiz.title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: quiz.title,
      description: quiz.description,
    },
    alternates: {
      canonical: `/quiz/${slug}`,
    },
  };
}

export default async function QuizPage({ params }: Props) {
  const { slug } = await params;
  const quiz = await getQuizBySlug(slug);

  if (!quiz) notFound();

  return (
    <>
      {/* JSON-LD 구조화 데이터 */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Quiz',
            name: quiz.title,
            description: quiz.description,
            url: `https://example.com/quiz/${slug}`,
          }).replace(/</g, '\\u003c'),  // XSS 방지
        }}
      />
      <main>
        {/* 콘텐츠 */}
      </main>
    </>
  );
}
```

**핵심 포인트:**
- `generateMetadata`에서의 fetch는 같은 데이터에 대해 Page 컴포넌트와 자동 메모이제이션된다
- 데이터가 없으면 빈 객체 `{}`를 반환하거나 `notFound()` 호출
- `generateStaticParams`와 함께 쓰면 빌드 타임에 정적 HTML + 메타태그 생성 (최적)
- `params`는 Next.js 15+에서 Promise 타입

### absolute title (template 무시)

```tsx
export const metadata: Metadata = {
  title: {
    absolute: '특별 페이지 - 커스텀 타이틀',
  },
};
// → "특별 페이지 - 커스텀 타이틀" (template 무시)
```

---

## 4. SEO 유틸리티 함수

메타데이터 생성 로직을 중앙화하면 일관성 유지에 유리하다.

```tsx
// lib/seo.ts
import type { Metadata } from 'next';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://example.com';
const SITE_NAME = 'My App';

type SeoParams = {
  title: string;
  description: string;
  path: string;
  ogImage?: string;
  type?: 'website' | 'article';
  publishedTime?: string;
  modifiedTime?: string;
  noIndex?: boolean;
};

export function generateSeoMetadata({
  title,
  description,
  path,
  ogImage,
  type = 'website',
  publishedTime,
  modifiedTime,
  noIndex = false,
}: SeoParams): Metadata {
  const url = `${SITE_URL}${path}`;
  const image = ogImage || `${SITE_URL}/og-image.png`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url,
      siteName: SITE_NAME,
      type,
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
      ...(publishedTime && { publishedTime }),
      ...(modifiedTime && { modifiedTime }),
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [image],
    },
    alternates: {
      canonical: url,
    },
    ...(noIndex && {
      robots: { index: false, follow: false },
    }),
  };
}
```

**사용 예시:**

```tsx
// app/quiz/[slug]/page.tsx
import { generateSeoMetadata } from '@/lib/seo';

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const quiz = await getQuizBySlug(slug);
  if (!quiz) return {};

  return generateSeoMetadata({
    title: quiz.title,
    description: quiz.description,
    path: `/quiz/${slug}`,
    ogImage: quiz.ogImage,
  });
}
```

---

## 5. 동적 OG 이미지

Next.js의 `ImageResponse`로 페이지별 고유 OG 이미지를 자동 생성할 수 있다.

### 파일 기반 (특정 라우트)

```tsx
// app/quiz/[slug]/opengraph-image.tsx
import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = '퀴즈 OG 이미지';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default async function Image({
  params,
}: {
  params: { slug: string };
}) {
  const quiz = await getQuizBySlug(params.slug);

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#1a1a2e',
          color: 'white',
          fontSize: 48,
          fontWeight: 'bold',
          padding: '40px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: 24, marginBottom: 20, color: '#8b5cf6' }}>
          ✨ 나의 레벨 테스트
        </div>
        <div>{quiz?.title || '퀴즈'}</div>
        <div style={{ fontSize: 20, marginTop: 20, color: '#a0a0a0' }}>
          example.com
        </div>
      </div>
    ),
    { ...size }
  );
}
```

### Route Handler 기반 (범용)

```tsx
// app/api/og/route.tsx
import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get('title') || 'My App';

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0f0f23',
          color: '#ffffff',
          fontSize: 48,
          fontWeight: 'bold',
        }}
      >
        {title}
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
```

---

## 6. sitemap.ts

```tsx
// app/sitemap.ts
import type { MetadataRoute } from 'next';

const BASE_URL = 'https://example.com';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // 정적 페이지
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    {
      url: `${BASE_URL}/about`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.5,
    },
  ];

  // 동적 페이지 (DB/CMS에서 가져오기)
  const quizzes = await getQuizzes();
  const quizPages: MetadataRoute.Sitemap = quizzes.map((quiz) => ({
    url: `${BASE_URL}/quiz/${quiz.slug}`,
    lastModified: quiz.updatedAt,
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }));

  return [...staticPages, ...quizPages];
}
```

**대규모 사이트 (50,000 URL 초과) — sitemap index 패턴:**

```tsx
// app/sitemap.ts
import type { MetadataRoute } from 'next';

export async function generateSitemaps() {
  const totalQuizzes = await getQuizCount();
  const numSitemaps = Math.ceil(totalQuizzes / 50000);

  return Array.from({ length: numSitemaps }, (_, i) => ({ id: i }));
}

export default async function sitemap({
  id,
}: {
  id: number;
}): Promise<MetadataRoute.Sitemap> {
  const start = id * 50000;
  const quizzes = await getQuizzes({ offset: start, limit: 50000 });

  return quizzes.map((quiz) => ({
    url: `https://example.com/quiz/${quiz.slug}`,
    lastModified: quiz.updatedAt,
  }));
}
```

---

## 7. robots.ts

```tsx
// app/robots.ts
import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/', '/admin/', '/_next/', '/private/'],
      },
    ],
    sitemap: 'https://example.com/sitemap.xml',
  };
}
```

---

## 8. 다국어 메타데이터

```tsx
// app/layout.tsx (다국어)
export const metadata: Metadata = {
  alternates: {
    canonical: 'https://example.com',
    languages: {
      'ko-KR': 'https://example.com/ko',
      'en-US': 'https://example.com/en',
      'ja-JP': 'https://example.com/ja',
    },
  },
};
```

```tsx
// app/[lang]/quiz/[slug]/page.tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { lang, slug } = await params;
  const quiz = await getQuiz(slug, lang);

  return {
    title: quiz.title,
    description: quiz.description,
    alternates: {
      canonical: `https://example.com/${lang}/quiz/${slug}`,
      languages: {
        'ko-KR': `https://example.com/ko/quiz/${slug}`,
        'en-US': `https://example.com/en/quiz/${slug}`,
      },
    },
  };
}
```
