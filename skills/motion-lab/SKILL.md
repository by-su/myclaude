---
name: motion-lab
description: React + Tailwind + Framer Motion + GSAP을 사용해 프론트엔드 애니메이션, 인터랙션, 모션 데모를 생성한다. 스택이 명시되지 않았으면 단일 .html 파일로 만든다. 마이크로 인터랙션(버튼 호버/클릭/폼 피드백), 스크롤 트리거/패럴럭스/페이지 전환, 랜딩페이지 히어로 섹션, drag/layout/gesture 같은 복잡한 UI 모션 요청에 반드시 사용. "애니메이션 만들어줘", "인터랙션 추천", "모션", "Framer Motion으로", "GSAP", "ScrollTrigger", "히어로 섹션", "스크롤 시 ~", "버튼 호버", "마이크로 인터랙션", "페이지 전환", "parallax", "reveal", "stagger", "split text", "drag", "layout animation", "magnetic button" 같은 표현이 등장하면 무조건 트리거. 단순 hover 한 줄짜리 CSS 요청부터 복잡한 시퀀스 데모까지 전부 다룬다.
---

# motion-lab

브라우저에서 바로 열어볼 수 있는 단일 `.html` 파일로 React + Tailwind + Framer Motion + GSAP 기반의 모션 데모를 만든다.

## 무엇을 만드는가

기본 출력 형식은 **단일 `.html` 파일**이다. 사용자가 `open file.html`만 하면 즉시 데모가 실행되어야 한다. 외부 빌드/번들링 없이 CDN(esm.sh, unpkg)으로 모든 의존성을 로드한다.

사용자가 명시적으로 .tsx 컴포넌트로 달라고 한 경우(`내 프로젝트에 넣을`, `Next.js에 추가`, `import해서 쓸`)에만 단일 `.tsx`로 출력한다. 그 외에는 항상 `.html`.

## 라이브러리 선택

좋은 모션은 라이브러리 선택에서 시작한다. 망설이지 말고 아래 기준을 따른다.

| 상황 | 선택 | 이유 |
|---|---|---|
| 컴포넌트 mount/unmount, hover/tap, drag, layout 변화 | **Framer Motion** | 선언적, AnimatePresence, layoutId, gestures가 압도적 |
| 긴 타임라인, 스크롤 스크럽, 픽셀 정밀 시퀀스, SVG path | **GSAP + ScrollTrigger** | timeline, scrub, pin, snap이 압도적으로 강함 |
| 단순 hover, 페이드, transform | **Tailwind / CSS** | 가장 가볍고 깔끔. 의존성 없음 |

한 데모에 GSAP과 Framer Motion을 섞어도 된다. 진입 애니메이션은 Framer Motion, 스크롤 시퀀스는 GSAP — 흔하고 좋은 조합이다.

## 디자인 원칙

모션 코드를 쓰기 전에 이 원칙들을 머릿속에 가지고 시작한다. 이게 평범한 데모와 "premium" 느낌 데모를 가른다.

### 1. 좋은 easing이 80%다

브라우저 기본(`ease`, `ease-in-out`)은 절대 쓰지 않는다. 다음을 기본으로:

- **`EASE_OUT_QUART = [0.22, 1, 0.36, 1]`** — Apple-style, 가장 자주 쓰는 default. 거의 모든 enter/exit, hover에 잘 어울림.
- **`EASE_SNAPPY = [0.4, 0, 0.2, 1]`** — Material expressive. 짧고 결단력 있는 변화에.
- **`EASE_EXPO_OUT = [0.16, 1, 0.3, 1]`** — 강한 감속. 빠르게 시작하고 슉 멈춤.
- **Spring**: Framer Motion `type: "spring", stiffness: 260, damping: 26`이 default 추천. 더 통통 튀게 하려면 `stiffness: 400, damping: 18`.
- **Linear**: 스크롤 스크럽일 때만. 그 외에는 거의 쓰지 않음.

GSAP에서는 `power2.out`, `power3.out`, `expo.out`이 default. `none`이나 `power1` 같은 약한 easing은 쓰지 않는다.

### 2. 시간 감각

- 호버/탭 피드백: **150-220ms**
- UI 상태 변화 (탭 전환 등): **250-400ms**
- 페이지/라우트 전환: **400-700ms**
- 히어로 등장: **700-1200ms** + 자식들 사이 stagger 60-100ms
- 스크롤 스크럽: 화면 진행에 따라

너무 빠르면 인지 안 되고, 너무 느리면 답답하다. 의심될 때는 짧은 쪽으로.

### 3. 무엇을 animate 하나

- **절대 X**: `width`, `height`, `top/left/right/bottom`, `margin`, `padding` — layout/paint 유발, 끊김.
- **적극 O**: `transform` (x, y, scale, rotate), `opacity`, `filter`, `clip-path` — compositor에서 처리.

크기 변화는 `scale`, 위치 이동은 `x/y`. 색상은 그대로 색상(컴포지터가 처리). `aspect-ratio` 변경 같은 layout-trigger는 `layout` prop으로 처리(Framer Motion이 FLIP으로 알아서 함).

### 4. 접근성

모든 데모에 다음을 포함한다:

- `prefers-reduced-motion: reduce` 대응 (템플릿이 CSS와 `<MotionConfig reducedMotion="user">`로 처리)
- 클릭 가능한 모션 요소는 키보드 포커스로도 동작
- 색상은 충분한 대비 (어두운 배경에 흰 텍스트가 default)

### 5. Stagger는 60-100ms

리스트, 그리드, 텍스트 라인 등장에서 자식들 사이에 60-100ms stagger를 준다. 더 짧으면 한꺼번에 보이고, 더 길면 답답하다. 단어 단위 텍스트 reveal은 30-50ms로 짧게.

### 6. 진입 애니메이션은 항상 opacity 동반

`y: 20 → 0`만 하면 갑자기 튀어나오는 느낌. **항상 `opacity: 0 → 1`을 같이** 한다. 예외는 거의 없다.

### 7. 무한 루프 절제

호버 안 한 상태에서 계속 도는 애니메이션은 시각적 소음이다. 의미가 있을 때만(로딩, 미묘한 텍스처) 쓰고, 그 외에는 trigger 기반.

## 작업 흐름

1. **요청 파싱**: 무슨 모션을 원하는지 짚는다. 모호하면 한 번만 짧게 질문 ("히어로에서 텍스트가 한 줄씩 슬라이드인 vs. 글자 단위 split-text 중 어느 쪽?").
2. **라이브러리 결정**: 위 표대로.
3. **카테고리 레퍼런스 읽기**: 작업 카테고리에 맞는 `references/<category>.md`를 먼저 읽고 패턴 확인.
4. **`assets/demo-template.html` 베이스로 작성**: 템플릿을 복사하고 `App` 컴포넌트만 채운다. 템플릿 헤더, importmap, MotionConfig wrapper는 그대로 유지.
5. **파일명 정하기**: 의미 있는 kebab-case (`hero-split-text.html`, `magnetic-button.html`, `scroll-pin-cards.html`). 현재 작업 디렉터리(cwd)에 저장.
6. **사용자에게 결과 알림**: 절대 경로 + `open <path>` 명령 + 1-2줄 기법 요약 + 짧은 확장 제안 1개.

## ⚠️ 절대 빼먹지 말 것 — 자주 하는 실수 (Critical)

처음부터 새로 .html을 작성하든 템플릿을 복사하든, **다음 importmap 항목이 반드시 들어가야 한다**:

```json
"react": "https://esm.sh/react@18.3.1",
"react/jsx-runtime": "https://esm.sh/react@18.3.1/jsx-runtime",
"react/jsx-dev-runtime": "https://esm.sh/react@18.3.1/jsx-dev-runtime",
```

**이유**: `<script type="text/babel" data-presets="react">`로 JSX를 변환할 때 Babel standalone은 **automatic JSX runtime**을 기본으로 쓴다. 이게 JSX를 컴파일하면 내부적으로 다음과 같은 import를 만들어낸다:

```js
import { jsx as _jsx } from "react/jsx-runtime";
```

importmap에 이 specifier가 없으면 브라우저 콘솔에 다음 에러가 뜨고 **검은 화면만 보인다**:

```
Uncaught TypeError: Failed to resolve module specifier "react/jsx-runtime".
Relative references must start with either "/", "./", or "../".
```

`react` 만 있고 `react/jsx-runtime` 이 빠진 importmap은 그 자체로 버그다. **항상 셋(`react`, `react/jsx-runtime`, `react/jsx-dev-runtime`)을 묶음으로** 적는다고 외워두기.

(보조 안전망: `<script type="text/babel" ... data-react-runtime="classic">`을 쓰면 classic runtime으로 컴파일되어 jsx-runtime import를 발생시키지 않는다. 하지만 1차 방어선은 importmap을 제대로 채우는 것.)

자체 importmap을 새로 짤 일이 거의 없으므로, **무조건 `assets/demo-template.html`을 복사해서 시작**하는 게 가장 안전하다.

## 카테고리별 레퍼런스

작업 시작 전에 카테고리에 맞는 파일을 읽는다. 안 읽고 짐작으로 쓰지 말 것 — 거기에 검증된 레시피가 있다.

| 카테고리 | 파일 |
|---|---|
| 마이크로 인터랙션 (버튼, 폼, 토글, 카드 hover) | `references/micro-interactions.md` |
| 스크롤 / 페이지 전환 (parallax, scrub, reveal, route transition) | `references/scroll-and-transitions.md` |
| 랜딩페이지 히어로 (split text, 인터랙티브 BG, 마우스 follow) | `references/hero-patterns.md` |
| 복잡한 UI 모션 (drag-reorder, shared layout, card stack, modal) | `references/complex-motion.md` |

라이브러리 자체 API가 헷갈리면:

- `references/framer-motion.md` — motion 컴포넌트, variants, AnimatePresence, layout, gestures, useScroll
- `references/gsap.md` — gsap.to/from/timeline, ScrollTrigger 옵션 정리

## 안티패턴 (절대 하지 말 것)

- `transition: all` — 무엇이 움직이는지 의도 불명확, 성능도 나쁨
- 1000ms 이상의 hover 트랜지션 — 사용자가 답답함
- 진입 시 `y` 변화만 하고 `opacity` 빠뜨림 — 튀어나오는 느낌
- 동시에 너무 많은 요소가 움직임 — 시각적 소음
- 회전이 어색한 각도 (47도, 134도 같은) — 90도, 180도, 360도 단위로
- 호버 안 했는데 계속 도는 무한 루프 — 의미 없으면 빼기
- 모든 element를 `motion.div`로 래핑 — 필요한 노드만
- Tailwind만으로 충분한데 GSAP 끌어오기 — 의존성 늘리지 말 것
- `width`/`height` animate — 잘림. `scale` 또는 layout prop으로.
- `easeInOut`만 반복 사용 — 변화의 끝이 흐물거림. 대부분 `easeOut`이 정답.
- importmap에 `react`만 적고 `react/jsx-runtime`, `react/jsx-dev-runtime` 빠뜨림 — Babel automatic JSX runtime 때문에 무조건 검은 화면. 위 "절대 빼먹지 말 것" 섹션 참고.

## 결과 제시 형식

데모를 만든 뒤 사용자에게 다음 형태로 알린다:

```
✓ /절대/경로/<filename>.html

브라우저로 열기: open /절대/경로/<filename>.html

기법: <라이브러리 + 핵심 기법 1-2줄>
예) Framer Motion `layoutId`로 카드 간 shared element transition.
    Easing은 [0.22, 1, 0.36, 1], 카드 사이 stagger 80ms.

확장 아이디어: <1-2개, 짧게>
예) 같은 패턴을 GSAP ScrollTrigger로 묶어 스크롤로 트리거하면 히어로 섹션에서 강력해요.
```

길게 설명하지 않는다. 사용자는 데모를 직접 본 후 다음 요청을 던질 것이다.

## 한 가지만 더

좋은 모션은 "이게 지금 무슨 의미인가"를 강화한다. 의미 없는 모션을 화려하게 넣지 말 것. 진입은 "여기에 새로 등장했어", 호버는 "이건 누를 수 있어", layoutId는 "이건 같은 것의 다른 모습이야"를 전달한다. 이 의도를 항상 머릿속에 두고 모션을 고른다.
