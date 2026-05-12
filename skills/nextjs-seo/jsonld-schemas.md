# JSON-LD 구조화 데이터 코드 예시

Schema.org 기반 JSON-LD 구현 패턴 모음. 콘텐츠 유형별로 복사해서 사용할 수 있다.

---

## 목차

1. [공통 패턴 - JsonLd 컴포넌트](#1-공통-패턴)
2. [WebSite](#2-website)
3. [Organization](#3-organization)
4. [Article / BlogPosting](#4-article--blogposting)
5. [FAQ](#5-faq)
6. [Quiz / 레벨 테스트](#6-quiz--레벨-테스트)
7. [Product](#7-product)
8. [BreadcrumbList](#8-breadcrumblist)
9. [WebApplication](#9-webapplication)
10. [VideoObject](#10-videoobject)
11. [Event](#11-event)
12. [Person](#12-person)
13. [여러 Schema 조합](#13-여러-schema-조합)

---

## 1. 공통 패턴

재사용 가능한 `JsonLd` 컴포넌트를 만들면 모든 페이지에서 일관되게 사용할 수 있다.

```tsx
// components/json-ld.tsx
type JsonLdProps = {
  data: Record<string, unknown>;
};

export function JsonLd({ data }: JsonLdProps) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(data).replace(/</g, '\\u003c'),
      }}
    />
  );
}
```

**사용:**

```tsx
import { JsonLd } from '@/components/json-ld';

export default function Page() {
  return (
    <>
      <JsonLd data={{
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'My App',
        url: 'https://example.com',
      }} />
      <main>...</main>
    </>
  );
}
```

**XSS 방지:** `JSON.stringify` 결과에서 `<` 문자를 `\\u003c`로 치환하여 `</script>` 주입을 방지한다.

---

## 2. WebSite

사이트 전체를 설명. root layout에 한 번 넣는다.

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "TypeLab",
  "url": "https://typelab.example.com",
  "description": "다양한 성격 유형 테스트를 제공하는 퀴즈 플랫폼",
  "inLanguage": "ko-KR",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://typelab.example.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
```

`potentialAction`(SearchAction)은 사이트 내 검색 기능이 있을 때만 포함한다.

---

## 3. Organization

사이트 운영 주체 정보. root layout에 넣는다.

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "My Company",
  "url": "https://example.com",
  "logo": "https://example.com/logo.png",
  "sameAs": [
    "https://twitter.com/mycompany",
    "https://github.com/mycompany",
    "https://www.instagram.com/mycompany"
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "email": "hello@example.com",
    "contactType": "customer support"
  }
}
```

---

## 4. Article / BlogPosting

블로그 글, 기사 등. 날짜/저자/이미지가 리치 결과에 표시된다.

```tsx
// app/blog/[slug]/page.tsx
const articleJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'BlogPosting',  // 또는 'Article'
  headline: post.title,
  description: post.excerpt,
  image: post.coverImage,
  datePublished: post.publishedAt,    // ISO 8601
  dateModified: post.updatedAt,       // ISO 8601
  author: {
    '@type': 'Person',
    name: post.author.name,
    url: post.author.url,
  },
  publisher: {
    '@type': 'Organization',
    name: 'My Blog',
    logo: {
      '@type': 'ImageObject',
      url: 'https://example.com/logo.png',
    },
  },
  mainEntityOfPage: {
    '@type': 'WebPage',
    '@id': `https://example.com/blog/${post.slug}`,
  },
  wordCount: post.content.split(/\s+/).length,
  keywords: post.tags.join(', '),
};
```

---

## 5. FAQ

자주 묻는 질문. 검색 결과에 질문/답변 드롭다운이 표시된다.

```tsx
const faqJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: '이 테스트는 얼마나 걸리나요?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '약 3~5분 정도 소요됩니다. 총 15개의 질문에 답하면 결과를 확인할 수 있습니다.',
      },
    },
    {
      '@type': 'Question',
      name: '테스트 결과는 정확한가요?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '이 테스트는 재미 목적으로 제작되었으며, 전문적인 심리 검사를 대체하지 않습니다.',
      },
    },
    {
      '@type': 'Question',
      name: '결과를 공유할 수 있나요?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '네, 결과 페이지에서 SNS 공유 버튼을 통해 친구들과 결과를 공유할 수 있습니다.',
      },
    },
  ],
};
```

**팁:** AI 검색(Perplexity, ChatGPT Search 등)이 FAQ 구조에서 답변을 직접 추출하는 경우가 많다.

---

## 6. Quiz / 레벨 테스트

퀴즈, 성격 테스트, 레벨 테스트 등.

```tsx
const quizJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Quiz',
  name: '나의 연애 레벨 테스트',
  description: '15개의 질문으로 알아보는 나의 연애 레벨! 당신은 연애 초보? 아니면 연애 고수?',
  url: 'https://example.com/quiz/love-level',
  about: {
    '@type': 'Thing',
    name: '연애',
  },
  educationalAlignment: {
    '@type': 'AlignmentObject',
    alignmentType: 'assesses',
    targetName: '연애 성향 파악',
  },
  hasPart: [
    {
      '@type': 'Question',
      name: '데이트 중 어색한 침묵이 흐를 때 당신은?',
      answerCount: 4,
    },
  ],
};
```

**참고:** 결과 페이지에는 별도로 `Quiz` 결과에 대한 정보를 포함할 수 있다.

### 결과 페이지

```tsx
const resultJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  name: '연애 레벨 테스트 결과: 연애 마스터',
  description: '당신의 연애 레벨은 "연애 마스터"입니다! 상대방의 마음을 읽는 데 탁월한 능력을 가지고 있어요.',
  isPartOf: {
    '@type': 'Quiz',
    name: '나의 연애 레벨 테스트',
    url: 'https://example.com/quiz/love-level',
  },
};
```

---

## 7. Product

제품, 서비스. 가격/재고/별점이 리치 결과에 표시된다.

```tsx
const productJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Product',
  name: '프리미엄 퀴즈 팩',
  description: '50개의 프리미엄 성격 테스트 묶음',
  image: ['https://example.com/premium-pack.png'],
  sku: 'QUIZ-PREMIUM-001',
  brand: {
    '@type': 'Brand',
    name: 'TypeLab',
  },
  offers: {
    '@type': 'Offer',
    priceCurrency: 'KRW',
    price: '9900',
    availability: 'https://schema.org/InStock',
    url: 'https://example.com/premium',
  },
  aggregateRating: {
    '@type': 'AggregateRating',
    ratingValue: '4.7',
    reviewCount: '234',
  },
};
```

---

## 8. BreadcrumbList

빵 부스러기 내비게이션. 검색 결과에서 경로가 표시된다.

```tsx
function generateBreadcrumbJsonLd(items: { name: string; url: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

// 사용
const breadcrumbJsonLd = generateBreadcrumbJsonLd([
  { name: '홈', url: 'https://example.com' },
  { name: '퀴즈', url: 'https://example.com/quiz' },
  { name: '연애 레벨 테스트', url: 'https://example.com/quiz/love-level' },
]);
```

---

## 9. WebApplication

웹 앱, 도구, 서비스를 설명할 때 사용.

```tsx
const webAppJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'TypeLab',
  url: 'https://typelab.example.com',
  description: '다양한 성격 유형 테스트를 무료로 제공하는 퀴즈 플랫폼',
  applicationCategory: 'EntertainmentApplication',
  operatingSystem: 'Web',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'KRW',
  },
  browserRequirements: 'Requires JavaScript',
  inLanguage: ['ko', 'en'],
};
```

---

## 10. VideoObject

동영상 콘텐츠. 썸네일과 재생시간이 검색 결과에 표시된다.

```tsx
const videoJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'VideoObject',
  name: '연애 레벨 테스트 소개',
  description: '연애 레벨 테스트가 어떤 건지 1분 만에 알려드립니다',
  thumbnailUrl: 'https://example.com/video-thumb.jpg',
  uploadDate: '2025-01-15T08:00:00+09:00',
  duration: 'PT1M30S',  // ISO 8601 duration
  contentUrl: 'https://example.com/videos/intro.mp4',
  embedUrl: 'https://www.youtube.com/embed/xxxxxx',
};
```

---

## 11. Event

이벤트, 프로모션. 날짜와 장소가 리치 결과에 표시된다.

```tsx
const eventJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Event',
  name: 'TypeLab 런칭 이벤트',
  startDate: '2025-03-01T10:00:00+09:00',
  endDate: '2025-03-31T23:59:59+09:00',
  location: {
    '@type': 'VirtualLocation',
    url: 'https://typelab.example.com/event',
  },
  description: '런칭 기념 모든 테스트 무료!',
  organizer: {
    '@type': 'Organization',
    name: 'TypeLab',
    url: 'https://typelab.example.com',
  },
};
```

---

## 12. Person

인물 프로필. 검색에서 인물 카드가 표시될 수 있다.

```tsx
const personJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Person',
  name: '홍길동',
  jobTitle: 'Backend Developer',
  url: 'https://example.com/about',
  sameAs: [
    'https://github.com/username',
    'https://linkedin.com/in/username',
  ],
  image: 'https://example.com/profile.jpg',
};
```

---

## 13. 여러 Schema 조합

한 페이지에 여러 Schema를 넣으려면 `@graph` 패턴을 사용한다.

```tsx
const combinedJsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      name: 'TypeLab',
      url: 'https://typelab.example.com',
    },
    {
      '@type': 'Organization',
      name: 'TypeLab',
      url: 'https://typelab.example.com',
      logo: 'https://typelab.example.com/logo.png',
    },
  ],
};
```

또는 별도 `<script>` 태그로 각각 넣어도 된다:

```tsx
export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>
        <JsonLd data={websiteJsonLd} />
        <JsonLd data={organizationJsonLd} />
        {children}
      </body>
    </html>
  );
}
```

---

## 검증 도구

구조화 데이터를 배포한 후 반드시 검증한다:

- **Google Rich Results Test**: https://search.google.com/test/rich-results
  - 실제로 리치 결과가 표시될지 확인
- **Schema Markup Validator**: https://validator.schema.org/
  - Schema.org 문법 검증
- **Google Search Console** → 개선사항
  - 배포 후 실제 크롤링 데이터 기반 피드백
