---
name: nextjs-seo
description: |
  Next.js 프로젝트의 SEO 최적화를 수행하는 스킬. App Router 기반 Metadata API, sitemap.ts, robots.ts, JSON-LD 구조화 데이터, Open Graph/Twitter Card, 동적 메타데이터(generateMetadata), OG 이미지 자동 생성, 다국어 SEO(i18n), Core Web Vitals 최적화 등 Next.js SEO의 모든 영역을 커버한다.

  트리거 키워드: "SEO", "검색 최적화", "메타태그", "메타데이터", "sitemap", "robots.txt", "구조화 데이터", "structured data", "JSON-LD", "Open Graph", "OG 이미지", "Twitter Card", "canonical", "검색엔진", "구글 노출", "검색 순위", "크롤링", "인덱싱", "generateMetadata", "rich snippet", "rich results", "schema.org", "Core Web Vitals", "lighthouse SEO", "og:image", "소셜 미리보기", "공유 미리보기", "SNS 공유 최적화", "AEO", "GEO", "AI 검색 최적화".

  Next.js 프로젝트에서 SEO 관련 요청이 오면 반드시 이 스킬을 사용할 것. "구글에 안 뜨는데요", "공유하면 미리보기가 안 나와요", "메타태그 어떻게 넣어요" 같은 간접적 표현에도 트리거한다.
---

# Next.js SEO Optimizer

Next.js App Router 프로젝트의 SEO를 체계적으로 최적화하는 스킬.
단순 메타태그 추가가 아니라, 검색엔진과 AI 검색(Perplexity, ChatGPT Search 등)까지 포괄하는 풀스택 SEO 전략을 다룬다.

---

## 전제 조건

- Next.js 14+ App Router (`app/` 디렉토리) 사용 프로젝트
- Pages Router(`pages/`)를 사용 중이라면 App Router 마이그레이션을 먼저 권유하거나, Pages Router 환경에 맞는 `next-seo` 패키지 기반 안내를 제공

---

## 워크플로우

### Step 1: 프로젝트 현황 진단

프로젝트 코드를 받으면 아래 항목을 점검한다. 코드가 없으면 사용자에게 어떤 종류의 프로젝트인지 물어본다.

#### SEO 진단 체크리스트

| 카테고리 | 점검 항목 | 상태 |
|---|---|---|
| **메타데이터** | root layout에 `metadata` export가 있는가? | |
| | `title.template` 패턴을 사용하는가? | |
| | 각 페이지마다 고유한 title/description이 있는가? | |
| | `metadataBase`가 설정되어 있는가? | |
| **동적 페이지** | 동적 라우트에 `generateMetadata`를 사용하는가? | |
| | `generateStaticParams`로 빌드 타임 생성을 하는가? | |
| **Open Graph** | OG title, description, image가 있는가? | |
| | OG 이미지 크기가 1200×630인가? | |
| | Twitter Card 메타데이터가 있는가? | |
| **구조화 데이터** | JSON-LD가 페이지에 포함되어 있는가? | |
| | 콘텐츠 유형에 맞는 Schema.org 타입을 사용하는가? | |
| **크롤링** | `sitemap.ts` 파일이 존재하는가? | |
| | `robots.ts` 파일이 존재하는가? | |
| | canonical URL이 설정되어 있는가? | |
| **성능** | `next/image`를 사용하는가? (alt 포함) | |
| | `next/font`를 사용하는가? | |
| | 불필요한 클라이언트 컴포넌트가 없는가? | |
| **다국어** | 다국어 지원이 필요한가? | |
| | `alternates.languages`가 설정되어 있는가? | |

진단 결과를 요약하고, 우선순위별 개선 항목을 제시한다.

---

### Step 2: 핵심 SEO 인프라 구축

진단 결과에 따라 아래 순서로 구현한다. 이미 구현된 항목은 건너뛴다.

#### 2-1. Root Layout 메타데이터 기반 설정

모든 페이지가 상속받는 기본 메타데이터를 설정한다.

**필수 구현 사항:**
- `metadataBase` — OG 이미지 등 상대 URL의 base. 빠뜨리면 소셜 플랫폼이 이미지를 못 불러온다
- `title.template` — `%s | 사이트명` 패턴으로 모든 하위 페이지에 일관된 타이틀 부여
- `title.default` — 하위 페이지에서 title을 정의하지 않았을 때의 fallback
- `description` — 사이트 전체를 대표하는 설명 (155자 이내 권장)
- `openGraph` 기본값 — siteName, locale, type
- `twitter.card` — `summary_large_image` 권장

**참고:** `references/metadata-examples.md`에 상세 코드 예시가 있다.

#### 2-2. sitemap.ts

`app/sitemap.ts`에 동적 사이트맵을 생성한다. Next.js가 자동으로 `/sitemap.xml`에서 서빙한다.

**핵심 원칙:**
- 정적 페이지 + 동적 페이지(DB/CMS 조회) 모두 포함
- `lastModified`를 실제 업데이트 시간으로 설정
- `changeFrequency`와 `priority`는 페이지 중요도에 따라 차등 부여
- 50,000 URL 또는 50MB 초과 시 sitemap index 패턴 사용
- canonical URL만 포함 (중복, 리다이렉트, 404 페이지 제외)

#### 2-3. robots.ts

`app/robots.ts`에 크롤링 규칙을 정의한다.

**핵심 원칙:**
- 공개 페이지는 `allow: '/'`
- `/api/`, `/admin/`, `/_next/` 등 크롤링 불필요한 경로는 `disallow`
- sitemap URL을 명시
- `/sitemap.xml` 자체를 disallow하지 않도록 주의

#### 2-4. Canonical URL

모든 페이지에 canonical URL을 설정하여 중복 콘텐츠 문제를 방지한다.

**설정 방법:** metadata 객체의 `alternates.canonical` 사용

**주의:** www vs non-www, trailing slash 유무로 중복 인식될 수 있으므로 하나로 통일

---

### Step 3: 페이지별 메타데이터 최적화

#### 정적 페이지

`export const metadata: Metadata = { ... }` 로 직접 정의한다.

**작성 원칙:**
- `title`: 60자 이내, 핵심 키워드를 앞쪽에 배치
- `description`: 155자 이내, 행동 유도 문구 포함, 키워드 자연스럽게 포함
- 각 페이지마다 고유한 title과 description — 절대 복붙하지 않는다

#### 동적 페이지 (generateMetadata)

DB나 CMS에서 가져온 데이터로 동적 메타데이터를 생성한다.

**핵심 원칙:**
- `generateMetadata`는 Server Component에서만 사용 가능
- 정적 페이지에는 사용하지 않는다 (불필요한 오버헤드)
- fetch 요청은 `generateMetadata`, `generateStaticParams`, Page 컴포넌트 간 자동 메모이제이션
- 데이터가 없으면 `notFound()` 호출
- OG image URL을 동적으로 생성

**참고:** `references/metadata-examples.md`에 generateMetadata 패턴 상세 예시

---

### Step 4: Open Graph & Twitter Card

소셜 미디어 공유 시 풍부한 미리보기를 제공한다.

**OG 이미지 가이드라인:**
- 크기: 1200×630px (범용 최적 사이즈)
- 포맷: PNG 또는 JPG
- 파일명에 키워드 포함 권장
- `metadataBase` 없이 상대 경로 사용하면 소셜 플랫폼이 못 불러온다

**동적 OG 이미지 (ImageResponse):**
- `opengraph-image.tsx` 파일로 JSX/CSS 기반 동적 이미지 생성 가능
- 동적 라우트별 고유 OG 이미지 자동 생성에 유용
- `next/og`에서 `ImageResponse`를 import

**Twitter Card:**
- `card: 'summary_large_image'` — 큰 이미지 미리보기
- `card: 'summary'` — 작은 이미지 미리보기
- OG 태그와 별도로 twitter 전용 태그도 설정하는 것을 권장

**검증 도구:**
- Facebook Sharing Debugger: `https://developers.facebook.com/tools/debug/`
- Twitter Card Validator: `https://cards-dev.twitter.com/validator`
- LinkedIn Post Inspector: `https://www.linkedin.com/post-inspector/`

---

### Step 5: 구조화 데이터 (JSON-LD)

검색 결과에서 리치 스니펫(별점, FAQ, 가격 등)을 표시하기 위한 구조화 데이터를 추가한다.

**구현 방식:**
- `<script type="application/ld+json">` 태그를 `layout.tsx` 또는 `page.tsx`에 직접 렌더링
- `next/script`가 아닌 네이티브 `<script>` 태그 사용 (JSON-LD는 실행 코드가 아님)
- XSS 방지: `<` 문자를 `\u003c`로 이스케이프하거나, `serialize-javascript` 같은 라이브러리 사용

**콘텐츠별 권장 Schema 타입:**

| 콘텐츠 유형 | Schema 타입 | 리치 결과 |
|---|---|---|
| 블로그/기사 | `Article`, `BlogPosting` | 날짜, 저자, 이미지 |
| 퀴즈/테스트 | `Quiz`, `WebApplication` | 앱 정보, 설명 |
| FAQ | `FAQPage` | 질문/답변 드롭다운 |
| 제품 | `Product` | 가격, 재고, 별점 |
| 이벤트 | `Event` | 날짜, 장소 |
| 조직 | `Organization` | 로고, 연락처 |
| 웹사이트 | `WebSite` | 사이트 검색 |
| 인물 | `Person` | 프로필 정보 |
| 레시피 | `Recipe` | 조리시간, 칼로리, 별점 |
| 동영상 | `VideoObject` | 썸네일, 재생시간 |

**재사용 가능한 컴포넌트 패턴:**
별도 `<JsonLd />` 컴포넌트를 만들어 재사용하면 일관성을 유지하기 쉽다.

**검증:**
- Google Rich Results Test: `https://search.google.com/test/rich-results`
- Schema Markup Validator: `https://validator.schema.org/`

**참고:** `references/jsonld-schemas.md`에 Schema 타입별 상세 코드 예시

---

### Step 6: 성능 최적화 (Core Web Vitals)

Google은 Core Web Vitals를 검색 랭킹 요소로 사용한다.

**이미지 최적화:**
- 반드시 `next/image` 사용 — 자동 포맷 변환, 리사이즈, lazy loading
- 모든 이미지에 의미 있는 `alt` 텍스트 (이미지 검색 트래픽에 영향)
- above-the-fold 이미지에 `priority` 속성
- `sizes` 속성으로 반응형 이미지 최적화

**폰트 최적화:**
- `next/font`로 Layout Shift 방지 (font-display: swap 자동 적용)
- 시스템 폰트 fallback 설정

**렌더링 전략:**
- SEO가 중요한 페이지는 Server Component (기본값) 유지
- 인터랙션이 필요한 부분만 Client Component로 분리
- `generateStaticParams`로 동적 라우트를 빌드 타임에 정적 생성 (SSG)
- ISR(Incremental Static Regeneration)으로 정적 페이지 주기적 갱신

**코드 스플리팅:**
- `dynamic(() => import(...), { ssr: false })` — 무거운 클라이언트 컴포넌트 지연 로딩
- `<Suspense>` boundary로 스트리밍 렌더링 활용

**시맨틱 HTML:**
- `<header>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<footer>` 사용
- 페이지당 `<h1>` 하나, 이후 `<h2>`, `<h3>` 계층 유지
- 설명이 담긴 앵커 텍스트 ("여기를 클릭" 대신 구체적 문구)

---

### Step 7: 다국어 SEO (필요 시)

다국어 지원이 필요한 프로젝트에서만 수행한다.

**구현 사항:**
- `alternates.languages`로 각 언어별 URL 매핑
- `hreflang` 태그 자동 생성
- 언어별 고유 metadata (title, description을 각 언어로 작성)
- sitemap에 다국어 URL 포함
- `<html lang="...">` 속성 올바르게 설정

---

### Step 8: AI 검색 최적화 (AEO/GEO)

2025년 이후 AI 검색(ChatGPT Search, Perplexity, Gemini 등)에 대응한다.

**전략:**
- FAQ 섹션 + `FAQPage` JSON-LD — AI가 답변을 직접 추출
- 콘텐츠를 질문-답변 형식으로 구조화
- 명확한 H2/H3 헤딩으로 섹션 구분
- 간결하고 정확한 첫 문단 (AI가 발췌하기 좋은 형태)
- 구조화 데이터를 풍부하게 작성하면 AI 검색에서 인용될 확률 상승

---

### Step 9: 배포 후 모니터링

**필수 작업:**
- Google Search Console에 sitemap 제출
- robots.txt 접근 가능 여부 확인
- Lighthouse SEO 점수 측정 (90+ 목표)
- Google Rich Results Test로 구조화 데이터 검증
- 소셜 미디어 공유 미리보기 테스트

**지속적 모니터링:**
- Search Console에서 크롤링 에러, 인덱싱 상태, CWV 추세 확인
- PageSpeed Insights로 실사용자 성능 데이터 확인

---

## 출력 가이드라인

### 코드를 직접 작성/수정할 때

1. 프로젝트 구조를 파악하고 기존 코드 스타일에 맞춘다
2. TypeScript를 사용 중이면 `Metadata` 타입을 import하여 타입 안전성 확보
3. 유틸리티 함수(`lib/seo.ts`)를 만들어 메타데이터 생성 로직을 재사용
4. 변경 사항을 파일별로 정리하여 설명

### 가이드만 제공할 때

1. 체크리스트 기반으로 현재 상태 진단 → 우선순위 제시
2. 각 항목에 대한 코드 예시를 포함
3. 검증 방법(도구, URL)을 함께 안내

---

## 흔한 실수 & 주의사항

- `metadataBase` 미설정 → OG 이미지가 상대 경로로 남아 소셜 플랫폼에서 안 보임
- 모든 페이지에 동일한 title/description → 검색엔진이 중복 콘텐츠로 판단
- 정적 페이지에 `generateMetadata` 사용 → 불필요한 런타임 오버헤드
- Client Component에서 metadata export 시도 → 작동하지 않음 (Server Component 전용)
- `next-seo` 패키지와 Metadata API 혼용 → 태그 충돌 가능
- canonical URL 미설정 → www/non-www, trailing slash로 중복 인덱싱
- robots.txt에서 CSS/JS 에셋 차단 → 크롤러가 페이지를 제대로 렌더링 못함
- OG 이미지 크기 미준수 (1200×630이 아닌 경우) → 잘림 또는 깨짐
- `dangerouslySetInnerHTML`로 JSON-LD 삽입 시 XSS 미방지

---

## 참고 파일

- `references/metadata-examples.md` — Metadata API 상세 코드 패턴 (root layout, 정적 페이지, generateMetadata, OG 이미지)
- `references/jsonld-schemas.md` — Schema.org 타입별 JSON-LD 코드 예시 (Article, FAQ, Product, Quiz, WebSite, Organization 등)
