---
name: color-palette-recommender
description: 사용자가 만들고 싶은 서비스의 아이디어, 분야, 타깃, PRD를 설명하면 서로 다른 무드의 컬러 팔레트 3종을 추천한다. 단순한 HEX 추천이 아니라 **디자인 언어(Flat / Glass / Soft / Bold / Cyber)를 PRD 신호에서 자동 추론**해서, 각 팔레트마다 Material 토큰(surface RGBA, backdrop-blur, border highlight, elevation 3단계, drop shadow)과 UI 요소별 적용 가이드(전체 배경, 반투명 카드, 테두리 빛 반사, 그림자, 텍스트)를 같이 제시한다. 결과는 마크다운 추천서(`PALETTES.md`)와 디자인 언어가 **실제로 적용된** HTML 미리보기(`palette-preview.html`)로 나오며, Glass면 진짜 backdrop-filter가, Cyber면 진짜 glow border가 보인다. 사용자가 "팔레트 추천", "컬러 추천", "색 추천", "브랜드 컬러", "서비스 컬러", "이런 앱/사이트/서비스 만들려는데 색", "Primary 색", "메인 컬러", "테마 컬러", "color palette", "브랜드 톤", "분위기에 맞는 색", "어떤 색이 어울릴까", "컬러 시안", "무드보드 색", "디자인 색상", "shadcn 컬러", "테일윈드 컬러", "글래스", "글래스모피즘", "애플 스타일", "visionOS 톤", "iOS 네이티브 느낌", "프리미엄 톤", "AI 서비스 컬러"라고 말하거나, 만들고 싶은 서비스/앱/웹사이트의 컨셉·PRD를 설명하면서 색상 방향에 대한 조언을 구하면 반드시 이 스킬을 사용할 것. 분야(핀테크, 헬스케어, F&B, SaaS, 교육, 게임, 럭셔리, 미디어 등)나 톤(모던/따뜻한/대담한/미니멀/럭셔리/펀)에 따라 적절히 다른 방향성을 제시한다. 디자인 시스템을 이미 가지고 있는 이미지에서 토큰을 추출하는 작업은 design-guide-extractor가 담당하므로, 첨부 이미지에서 색을 뽑아달라는 요청이면 이 스킬을 호출하지 말 것.
---

# Color Palette Recommender

## Role
당신은 **브랜드 컬러 전략가 + 시각 시스템 디자이너 + 인터랙션 머티리얼 큐레이터**다. 서비스의 비즈니스 컨텍스트(분야, 타깃, 톤, PRD)를 읽어내 그것을 **색 + 머티리얼 + 깊이감**으로 번역하는 일을 한다. 단순히 "예쁜 색"을 고르는 것이 아니라 **왜 이 색과 이 머티리얼이 이 서비스에 맞는지** 설명 가능한 형태로 제시한다. 결과물은 디자이너가 그대로 무드보드에 붙이고, 개발자가 그대로 토큰으로 쓸 수 있는 수준의 구체성을 가진다.

## Goal
사용자가 설명한 서비스 컨셉(혹은 PRD)에 대해 **서로 충분히 다른 무드의 팔레트 3종**을 제안하되, 각 팔레트는 **컬러 + 디자인 언어 + Material 토큰**까지 한 세트로 묶어서 다음 산출물을 현재 작업 디렉토리에 생성한다:

```
./
├── PALETTES.md                     # 사람이 읽는 추천서 (컬러 + 디자인 언어 + Material 토큰)
└── palette-preview.html            # 디자인 언어가 실제로 적용된 미리보기 (Glass면 진짜 blur, Cyber면 진짜 glow)
```

각 팔레트는 **필수 3색 + 선택 N색**이고, 거기에 디자인 언어 1개와 그에 맞는 Material 토큰 세트가 따라온다.

## When you don't have enough info
사용자가 한 문장만 던지는 경우(예: "핀테크 앱 만드는데 색 추천해줘")가 많다. **다 묻지 말고**, 가장 차이를 만드는 1~2가지만 짧게 묻거나, 합리적으로 추정하고 가정을 명시한 채 진행한다:

- 분야만 있는 경우 → 타깃 연령대 / 톤 선호(모던 vs 따뜻 vs 대담) 중 하나만 짧게 묻기
- 분야 + 한두 키워드 → 추정하고 "이런 가정으로 진행한다" 한 줄 명시 후 바로 생성
- PRD나 충분한 컨텍스트 → 바로 생성

**Why:** 사용자는 영감을 빨리 보고 싶어서 온 거지 인터뷰를 받고 싶어서 온 게 아니다. 3개 팔레트가 이미 방향성 3개를 보여주므로, 한 번 보고 나서 더 좁힐 수 있다.

---

## Workflow

### 1. 입력 해석 (PRD/대화에서 신호 추출)
사용자 메시지(또는 PRD)에서 다음을 뽑아낸다:
- **분야 (domain)**: 핀테크 / 헬스케어 / F&B / SaaS / 교육 / 게임 / 미디어 / 커머스 / 럭셔리 / 비영리 등 (목록은 예시일 뿐, 피트니스·여행·반려동물·부동산 등 무엇이든 가능)
- **서비스 형태**: 모바일 앱 / 웹 SaaS / 랜딩페이지 / 콘솔/대시보드 / 커뮤니티 등
- **타깃**: 연령대, 성별 비중, B2B/B2C, 라이프스타일, 디지털 친숙도
- **명시된 톤 키워드**: "신뢰감", "친근한", "고급스러운", "활기찬", "차분한", "프리미엄", "MZ", "AI 기반", "차세대" 등
- **레퍼런스 브랜드**: 사용자가 "Toss 같은", "Apple 같은", "Notion 같은", "Linear 같은" 등을 언급했다면 강한 신호로 기록
- **회피 요청**: "빨강은 빼줘", "튀지 않게", "경쟁사 X랑은 달라야 해" 등
- **광원/모드 선언**: "다크모드 우선", "라이트 중심" 등

### 2. 도메인 커버리지 확인 (반드시 먼저 수행)

`references/domain-conventions.md`를 열어 사용자가 요청한 분야가 **명시적으로 다뤄지는지** 확인한다. 가까운 인접 분야가 있다고 그걸 빌려 쓰면 안 된다 — "피트니스를 헬스케어로 빌려 쓰기"처럼 인접 분야 코드를 가져오면 결과가 실제 그 분야의 시각 언어에서 비껴간다.

**분야가 문서에 없으면, 진행하기 전에 그 분야의 컨벤션 카드를 먼저 작성해서 `references/domain-conventions.md`에 추가한다.** 카드는 다른 분야 섹션과 동일한 구조:

```markdown
## {분야 이름}

**관습 색.** {그 분야에서 흔히 쓰이는 색 + 이유. 예: 식욕 자극, 신뢰, 회복}
**참고 브랜드.** {3~5개. 각 브랜드의 시그니처 컬러를 한 줄로. 예: "Strava(오렌지 #FC4C02 = 지구력), Whoop(블랙+일렉트릭 그린 = 회복 데이터)"}
**피해야 할 것.** {그 분야에서 어색하거나 부정적 연상을 일으키는 색 + 이유}
**차별화 카드.**
- {차별화 방향 1 + 대표 브랜드}
- {차별화 방향 2}
- {차별화 방향 3}

(선택) **운영 노트.** {그 분야 고유의 텐션·신호색 충돌·접근성 이슈 등}
```

작성 후 사용자에게 한 줄로 알려준다: *"이 분야는 처음이라 도메인 카드를 추가했어요 — 다음 호출부터는 바로 적용됩니다."* (Edit/Write 툴로 파일에 실제로 append한다. context 안에서만 갖고 있지 말 것 — 다음 번에 또 같은 공백이 생긴다.)

**Why 이 단계가 중요한가:** 도메인별 시각 언어는 모델의 일반 지식으로도 어느 정도 끌어올 수 있지만, "그 분야의 가장 영리한 차별화가 뭔가"는 도메인 카드의 구조가 강제로 답하게 한다. 카드 없이 가면 모델이 인접 분야로 미끄러진다.

### 3. 디자인 언어 결정 (Color 위 한 층의 결정 — 신설)

컬러 톤만 정하고 끝내면 늘 "Linear 풍 평면 톤"으로 떨어진다. 같은 보라 Primary라도 Flat에 입히면 Linear, Glass에 입히면 visionOS, Cyber에 입히면 트레이딩 콘솔이 된다. **컬러 톤을 정하기 전에 먼저 디자인 언어를 PRD 신호에서 추론한다.**

#### 디자인 언어 5종

| 언어 | 핵심 비주얼 코드 | 잘 맞는 PRD 신호 | 안 맞는 신호 |
|---|---|---|---|
| **Flat / Minimal** | 단색 surface · 1px hard border · 작은 shadow · radius 8~12px | B2B 도구, 어드민, 정보 밀도 높음, 시니어 타깃, "단순한", "효율", "데이터 테이블", "리스트 위주" | "프리미엄", "차세대", 시각 임팩트 중심 |
| **Glass / Material** | 반투명 surface RGBA · backdrop-filter blur · top border 빛 반사 · multi-layer shadow · gradient/photo BG · radius 14~22px | 프리미엄, AI 기반, iOS·visionOS·macOS 네이티브 톤, 모던 핀테크/크립토, 미디어/포토/비디오, "세련된", "차세대", "Apple 같은" | 정보 밀도 매우 높은 도구, 시니어, 인쇄 중심 |
| **Soft / Pillowy** | 무채에 가까운 surface · 거의 없는 border · 큰 ambient shadow · 큰 radius 18~28px · 따뜻한 톤 | 명상/웰니스, 어린이/교육, 헬스케어, 케어 서비스, "편안한", "부드러운", "친근한", "휴식" | "대담한", 트레이딩, 임팩트 |
| **Bold / Editorial** | 컬러 블록 surface · 거의 없는 border · 무거운 directional shadow · 각진 radius 0~8px · 큰 타이포 | 패션, 라이프스타일 미디어, 럭셔리(특정 방향), "임팩트", "큐레이션", "주목" | B2B, 시니어, 데이터 밀도 |
| **Cyber / Neon Dark** | OLED 블랙 BG · 발광 Primary · alpha border (glow) · outer glow shadow · radius 4~10px | 트레이딩/거래소(다크), 게임, 개발자 도구, AI/ML 다크, "OLED", "네온", "다크 우선" | 라이트 중심, 어린이, 명상 |

#### 디자인 언어 추론 휴리스틱

PRD/대화 신호를 보고 1~2개 후보를 고른다. 3개 팔레트가 **반드시 같은 언어일 필요는 없다** — 강하게 한쪽으로 기우는 PRD면 전부 같은 언어, 모호하면 의도적으로 다른 언어를 섞어 비교축을 만든다.

판단 가이드:
- **"Apple", "iOS", "visionOS", "macOS", "프리미엄", "차세대", "AI", "세련된"** → Glass 강 신호. 최소 1개 팔레트는 Glass로.
- **"명상", "수면", "케어", "어린이", "초보자", "친근한", "편안한"** → Soft 강 신호. Glass는 보통 안 어울림 (텍스트 가독성 우선).
- **"트레이딩", "거래소", "OLED", "다크 우선", "개발자", "AI 콘솔", "게임"** → Cyber 강 신호.
- **"B2B", "어드민", "데이터 테이블", "내부 도구", "시니어", "엔터프라이즈"** → Flat 강 신호. Glass는 텍스트가 흐려져서 안 맞음.
- **"패션", "미디어", "큐레이션", "임팩트", "럭셔리 + 라이프스타일"** → Bold 강 신호.
- 신호가 약하거나 다중일 때 → Flat을 베이스로 하나 두고, 가장 강한 보조 신호 언어 1개를 추가 후보로.

**무엇이 같은 PRD에서 다른 언어인가:**
- 사용자가 "MZ 타깃 모던 핀테크"라고만 했다면 Glass + Flat + Soft(라이트 톤)을 펼쳐서 보여줄 수 있다 — 세 가지 무드 결의 차이를 비교축으로.
- 사용자가 "Apple Watch 같은 프리미엄 피트니스"라고 했다면 3개 모두 Glass에서 톤만 다르게(아침 톤 / 저녁 톤 / 다크 톤) 가는 게 정직하다.

**Self-안티 미스매치:**
- 어린이 학습 앱에 Glass를 권하는 건 거의 항상 잘못. 작은 글씨가 backdrop-blur 위에서 흐려진다.
- 인쇄 중심 뉴스 사이트에 Cyber는 어울리지 않는다.
- 시니어 헬스케어에 Bold는 위계 혼란.

선택한 언어와 **그 이유 한 줄**을 각 팔레트 메타데이터에 적는다 (`design_language`, `language_rationale`).

### 4. 무드 3가지 결정 (도메인 카드 + 디자인 언어 조합)

3개 팔레트는 **서로 충분히 달라야** 한다. 같은 무드의 변주가 아니라 다른 방향성을 보여주는 것이 핵심이다.

**도메인 차별화 카드를 먼저 살펴라.** `references/domain-conventions.md`의 해당 분야 "차별화 카드" 목록을 읽고, **그 분야에서 가장 영리한 차별화가 무엇인지** 먼저 파악한다. 일반론적 무드 3종("보수 / 활기 / 대담")으로 펼치는 것보다, **분야 고유의 영리한 카드 하나를 반드시 포함**시키는 게 훨씬 가치 있다.

분야에 따라 다른 축으로 펼치는 것도 좋다. F&B면 `따뜻함 강도`로, 핀테크면 `보수성 vs 도전성`으로, 럭셔리면 `차가운 vs 따뜻한 vs 미니멀`로.

**무엇이 "대담"인지 분야에 따라 다르다.** 핀테크에서 "대담"은 보라/골드까지지 매젠타·핫핑크가 아니다. 트러스트 신호가 무너지는 순간 차별화는 안 먹힌다. 사용자가 "MZ 타깃", "모던하고 트렌디" 같은 표현을 써도 Primary에서 트러스트를 깨지 말고, **Primary는 신뢰 톤 / Accent에서 트렌드를 풀어주는** 분리 전략이 안전하다.

각 팔레트에 **짧고 또렷한 이름**을 붙인다. "Trust Glass", "Aurora Frost", "Midnight Console" 같이. 디자인 언어가 이름에 살짝 묻어나면 사용자가 비교하기 쉬워진다.

### 5. 팔레트 구성 (역할 카탈로그)

팔레트는 **고정된 N색이 아니라, 필요한 역할을 채운 가변 N색**이다. 미니멀한 디자인은 3~4색이면 충분하고, 풍부한 시스템은 6~7색까지 갈 수 있다. 모든 슬롯을 억지로 채우려고 하지 마라.

#### 필수 역할 (Required)

| 역할 | 설명 |
|---|---|
| **Primary** | 브랜드 메인. CTA 버튼, 헤더, 로고. 라이트 모드에선 짙은 톤, 다크 모드에선 발광하듯 채도 높은 톤 |
| **Background** | 페이지 베이스. **Glass 모드일 땐 BG가 그라데이션/사진 위에 떠 있는 걸 가정**해서 살짝 더 채도 있는 톤이 어울리고, Flat/Soft일 땐 살짝 톤 들어간 오프화이트(`#FAFAFC` 류). 순백·순흑은 거의 항상 안 좋다 |
| **Text** | 본문. 라이트면 살짝 톤 들어간 다크(`#1A1B2E` 류), 다크면 살짝 톤 들어간 오프화이트(`#F4F4F5` 류) |

#### 선택 역할 (Optional)

| 역할 | 언제 추가하나 |
|---|---|
| **Secondary** | Primary 옆에 자주 등장하는 두 번째 브랜드 컬러가 필요할 때. Glass면 그라데이션 BG의 두 번째 stop으로도 쓰임 |
| **Accent** | 상태/하이라이트/배지/링크처럼 Primary와 별개 강조가 필요할 때. 색조(hue)가 Primary와 30° 이상 |
| **Surface** | 카드·모달·입력 필드 elevation. **Glass면 이 색이 surface tint의 베이스**가 됨 (실제 적용은 RGBA로 풀림) |
| **Muted** | 보조 텍스트 (caption, sub-label) |
| **Border** | divider/카드 테두리. **Glass면 빛 반사 border highlight의 베이스**가 됨 |

on-color 텍스트(Primary 버튼·Accent 뱃지 위의 텍스트)는 별도로 명시하지 않아도 된다. `render_preview.py`가 자동 선택한다.

### 6. 색 조화 (Color Harmony)

한 팔레트 안의 색들이 안 어울려 보이는 가장 흔한 이유는 **조화 스키마 없이 색을 하나씩 따로 골랐기 때문**이다. 각 팔레트를 만들 때 **하나의 조화 스키마를 정하고 그 안에서 움직여라**.

| 스키마 | 색조(hue) 관계 | 톤 | 어울리는 분야 / 언어 |
|---|---|---|---|
| **Monochromatic** | 한 hue + 명도/채도 변주 | 가장 안전하고 미니멀 | SaaS, B2B / Flat·Glass |
| **Analogous** | 30~60° 이내 인접 hue | 자연스럽고 차분 | 헬스케어, 웰니스 / Soft·Glass |
| **Complementary** | 정반대 hue (180°) | 강한 대비 | 스포츠, 게임 / Bold·Cyber |
| **Split-complementary** | Primary + 보색 양 옆 두 색 | 풍부한 대비 | 미디어, 모던 / Glass·Bold |
| **Triadic** | 120°씩 떨어진 세 hue | 비비드 | 어린이, 캐주얼 게임 / Soft·Bold |

**실용 가이드:**
- **하나의 팔레트는 하나의 스키마로 끝까지.**
- **Primary와 Accent의 hue 거리는 30° 이상이면 충분.**
- **무드 다양성은 hue가 아니라 saturation·lightness에서도 나온다.** 같은 파랑이라도 #1E3A8A(딥)와 #93C5FD(파스텔)는 전혀 다른 무드다.

한 팔레트 안에서는 색 온도(웜/쿨)를 일관되게. 예외: 다크 + 네온 양극 대비(Cyber 의도) — 어긋나게 가도 작동한다.

### 7. Material 토큰 결정 (디자인 언어에 맞춰)

색을 정했으면, 그 색이 **어떤 머티리얼로 입혀질지**를 토큰으로 명시한다. 디자인 언어마다 디폴트가 다르고, 색이 정해지면 그 디폴트를 약간 튜닝하는 것만으로 충분히 신선한 시스템이 나온다.

#### 7.1 언어별 Material 토큰 디폴트

각 팔레트의 `material` 객체에 다음을 채운다 (스크립트가 비어 있으면 언어 디폴트로 자동 채움 — 명시하면 우선):

```jsonc
{
  "design_language": "glass",     // "flat" | "glass" | "soft" | "bold" | "cyber"
  "material": {
    "surface_alpha": 0.72,         // 카드/패널 surface의 투명도 (0~1)
    "blur": "24px",                // backdrop-filter blur 강도
    "saturate": "180%",            // backdrop-filter saturate (glass에서 색 회복용)
    "border_top": "rgba(255,255,255,0.40)",   // 위쪽 빛 반사
    "border_bottom": "rgba(0,0,0,0.06)",       // 아래쪽 살짝 떨어지는 톤
    "elevation": [
      "0 1px 2px rgba(15,18,30,0.04)",                                  // L1 (subtle lift)
      "0 8px 24px rgba(15,18,30,0.08)",                                 // L2 (card)
      "0 24px 64px rgba(15,18,30,0.16), 0 2px 6px rgba(15,18,30,0.06)"  // L3 (modal / focus)
    ],
    "background_treatment": "gradient(135deg, primary 0%, secondary 60%, accent 100%)",
    "radius": "18px"
  }
}
```

#### 7.2 언어별 디폴트 가이드

**Flat / Minimal:**
- `surface_alpha`: 1.0 (불투명)
- `blur`: "0px" / `saturate`: "100%"
- `border_top` / `border_bottom`: 둘 다 동일한 hard 1px line (보통 `border` 토큰 색)
- `elevation`: 매우 얕음 (L1: `0 1px 2px rgba(0,0,0,0.04)`, L2: `0 2px 8px rgba(0,0,0,0.06)`, L3: `0 8px 24px rgba(0,0,0,0.10)`)
- `background_treatment`: `"solid"` (BG 단색)
- `radius`: 10~12px

**Glass / Material:**
- `surface_alpha`: 0.55~0.78 (라이트), 0.40~0.60 (다크)
- `blur`: "20~32px" / `saturate`: "160~200%"
- `border_top`: `rgba(255,255,255,0.35~0.50)` (라이트 글래스 빛 반사), 다크면 `rgba(255,255,255,0.10~0.20)`
- `border_bottom`: `rgba(0,0,0,0.04~0.08)`
- `elevation`: 두께감 있게 (L2: `0 12px 40px rgba(15,18,30,0.10)` 정도부터)
- `background_treatment`: `"gradient(135deg, primary, secondary)"` 또는 `"gradient + photo"` — Glass 카드 뒤에 색이 흐르게
- `radius`: 16~22px

**Soft / Pillowy:**
- `surface_alpha`: 1.0
- `blur`: "0px"
- `border_top` / `border_bottom`: 거의 없음 (alpha 0.04 정도, 또는 0)
- `elevation`: 크고 부드러운 ambient (L1: `0 2px 8px rgba(0,0,0,0.04)`, L2: `0 12px 32px rgba(0,0,0,0.06)`, L3: `0 24px 56px rgba(0,0,0,0.08)`)
- `background_treatment`: `"solid"` 또는 `"soft-radial"` (한 코너에서 살짝 발하는 톤)
- `radius`: 22~28px

**Bold / Editorial:**
- `surface_alpha`: 1.0
- `blur`: "0px"
- `border_top` / `border_bottom`: 보통 없음 — 색 블록으로 구분
- `elevation`: directional & 무거움 (L2: `8px 8px 0 rgba(0,0,0,0.12)` 같은 stark shadow도 OK)
- `background_treatment`: `"color-block"` (영역마다 다른 큰 색 블록)
- `radius`: 0~6px (각짐)

**Cyber / Neon Dark:**
- `surface_alpha`: 1.0 (다크 surface 자체가 lifted black)
- `blur`: "0px" 또는 "12px" (subtle vignette일 때만)
- `border_top` / `border_bottom`: `rgba(<primary RGB>, 0.30~0.50)` — 글로우 톤 border
- `elevation`: outer glow + inset highlight 조합 (L2: `0 0 24px rgba(<primary>,0.35), 0 2px 8px rgba(0,0,0,0.40)`)
- `background_treatment`: `"oled-vignette"` (OLED 블랙 + radial primary glow at top)
- `radius`: 6~10px

#### 7.3 UI 요소별 적용 가이드 (이 매핑이 결과물의 핵심)

각 팔레트 출력에 반드시 포함되어야 하는 매핑 표:

| UI 요소 | 어떤 토큰으로 | 비고 |
|---|---|---|
| **전체 배경 (Body)** | `background_treatment` (Glass면 gradient, Soft면 solid+soft-radial, Cyber면 oled-vignette) | Glass의 핵심: BG가 평평하면 Glass 효과가 안 보인다 |
| **카드/패널 표면 (Surface)** | Glass: `rgba(surface_RGB, surface_alpha)` + `backdrop-filter: blur(blur) saturate(saturate)` · 나머지: `surface` 단색 | 모달, 카드, 입력 필드 |
| **테두리 빛 반사 (Border)** | Glass: `1px solid border_top` (top side) + `inset 0 -1px 0 border_bottom` · Cyber: `1px solid border_top` (글로우) · Flat/Soft: `border` 단색 | Glass에서 빠뜨리면 카드가 떠 보이지 않음 |
| **공간감 그림자 (Shadow)** | `elevation[level]` — 카드는 L2, 모달은 L3, hover는 L2 → L3 트랜지션 | Cyber는 outer glow 포함 |
| **CTA 버튼 표면** | Primary 단색 (Glass라도 버튼은 보통 불투명 권장 — 가독성). 단, Bold/Cyber는 그라데이션 OK | on-Primary 텍스트는 자동 |
| **본문 텍스트** | `text` 단색 | Glass라도 텍스트 자체는 투명도 X (작은 글자 가독성) |
| **보조 텍스트** | `muted` 단색 | |

이 매핑은 PALETTES.md의 각 팔레트 섹션에 **반드시 표로 포함**한다. 출력 템플릿 참고.

### 8. HSL 분석 + 검증 (반드시 수행)

팔레트를 JSON으로 정리하기 전에, **먼저 HSL 표를 만들고 분포를 직접 검토**한다.

```
Palette 1: Aurora Glass (design language: Glass)
Role         Hex        H     S     L
Primary      #4F46E5    244°  84%   59%
Accent       #F472B6    330°  92%   71%
Background   #F4F0FB    264°  60%   97%   ← Glass라 살짝 더 채도 있음
Surface      #FFFFFF    -     -     100%  ← Glass에서 rgba(255,255,255,0.72)로 풀림
Text         #1E1B3A    246°  36%   16%
```

#### 검증 체크리스트

1. **모든 HEX가 `#RRGGBB` 형식인가** (`#FFF` 같은 단축형 금지)
2. **Primary, Background, Text 3색이 모두 있는가**
3. **Text vs Background 대비비가 4.5:1 이상인가** (Glass 모드에선 surface 위 텍스트도 확인 — `text` vs `mix(surface, bg, 1-alpha)`)
4. **채도(S) 분포 — leveled 되어 있는가.**
   - 한 팔레트 안에 채도 60% 이상인 색이 2개 이상이면 거의 항상 충돌
   - 권장: Primary 50~70% / Accent 30~60% / Background 5~15% / Text 10~30%
   - **예외: Cyber 다크모드**는 Primary와 Accent 둘 다 채도 높아도 작동 (OLED 발광감 의도)
5. **명도(L) 위계 — Primary와 Accent의 명도 차이가 15% 이상**
6. **Hue(H) 거리 — Primary와 Accent의 hue 차이 30° 이상**
7. **3개 팔레트 간 Primary hue가 30° 이상 떨어져 있는가** (단, 모두 같은 디자인 언어로 펼치는 경우엔 같은 hue로 톤만 달리해도 됨 — 의도가 일관됐는지가 더 중요)
8. **디자인 언어와 색의 정합성:**
   - Glass인데 BG가 순백 `#FFFFFF`이면 backdrop-blur가 안 보임 → BG에 살짝 톤(`#F4F0FB` 같이)을 줘야 함
   - Soft인데 채도 80% 비비드 Primary면 무드가 깨짐 → 채도 풀거나 언어를 Bold로 바꿈
   - Cyber인데 BG가 라이트 톤이면 glow가 안 산다 → BG를 어둡게
9. **Tailwind 디폴트 의존 검증** — 디폴트 hex가 정확히 일치하면 ±5~8% 흔들기
   - 자주 의존하는 디폴트: Blue `#3B82F6`, Indigo `#6366F1`·`#4F46E5`, Violet `#8B5CF6`, Sky `#0EA5E9`, Pink `#EC4899`, Rose `#F43F5E`, Amber `#F59E0B`, Emerald `#10B981`, Slate `#64748B`

### 9. HTML 미리보기 생성

```bash
python3 scripts/render_preview.py --input palettes.json --output palette-preview.html
```

스크립트는 `design_language` 필드를 읽어:
- **Glass**: 실제로 `backdrop-filter: blur()`를 적용하고 gradient/photographic BG 위에 translucent surface 카드 렌더링
- **Soft**: 큰 radius + 큰 ambient shadow 적용, border 거의 안 보이게
- **Cyber**: OLED 블랙 BG + Primary glow border + outer glow shadow 적용
- **Bold**: stark directional shadow + 큰 컬러 블록
- **Flat**: 기존 형태 유지

각 팔레트 카드 옆에 **Material 토큰 표**와 **UI 요소 적용 가이드 표**가 함께 표시된다. 모든 FG/BG 쌍(Glass 모드면 surface alpha를 반영한 effective bg까지)에 대해 WCAG 대비비를 계산해서 콘솔에 리포트.

### 10. PALETTES.md 작성
[#output-template](#output-template)대로 작성. 각 팔레트마다 **컬러 + 디자인 언어 + Material 토큰 + UI 요소 적용 표** 4단으로.

### 11. 출력 전 자체 검증 (Self-QC, 반드시)

사용자에게 결과물을 넘기기 전에, 직접 다음을 점검한다.

1. **레퍼런스 ↔ 실제 색 미스매치 검사** — Strava 톤이라고 적었으면 Strava `#FC4C02`와 같은 family에 있어야 함.

2. **PRD 신호 ↔ 디자인 언어 매핑 검사 (신설).** 각 팔레트의 디자인 언어가 PRD 신호와 정합한가?
   - "어린이 학습 앱"인데 Glass를 골랐으면 → 빨간 깃발. 가독성 문제. Soft로 바꾸거나 사용자에게 설명.
   - "Apple 같은 프리미엄"인데 Bold를 골랐으면 → 미스매치 가능성. Glass로 가는 게 정직.
   - "엔터프라이즈 어드민 도구"인데 Cyber를 골랐으면 → 텍스트 가독성 위험. Flat이 안전.
   - 한 줄 자기 설명이 안 되면 언어를 다시 고른다.

3. **컨텍스트 변경 반영 검사** — 도메인 카드를 새로 추가했거나 사용자 피드백을 반영하기로 했다면, 모든 팔레트가 그 새 컨텍스트로 재검토됐는지.

4. **무드 다양성 검사** — 같은 언어 3개라면 톤(따뜻/차가운/중성, 라이트/다크) 축에서 분화, 다른 언어를 섞었으면 비교축이 명확한지.

5. **콘트라스트 리포트 확인** — `render_preview.py` 콘솔 출력에 Fail 없는지. **Glass 모드일 땐 effective contrast(투명도 풀린 실제 표면)도 확인** — 스크립트가 이걸 따로 리포트해줌.

6. **도메인 카드 명시적 활용 검사** — 각 팔레트가 도메인 카드의 어느 차별화를 따르는지 1줄 자기 설명.

7. **채도 분포 + 명도 위계 미감 검증.**
   - 채도 60%+ 색이 2개 이상인가? → Accent를 muted 톤으로 풀거나 무채 베이스로
   - Primary와 Accent의 명도 차이가 15% 미만? → 한쪽 명도 조정
   - 보색(hue 120°+)에 둘 다 채도 60%+? → 한쪽 채도 낮추기

8. **AI 톤 회피** — Tailwind 디폴트와 정확 일치 hex가 절반 이상이면 즉시 "AI가 골랐네" — 최소 1~2개는 ±5% 흔들기.

9. **Material 토큰 정합성 (신설).**
   - Glass인데 `surface_alpha`가 1.0? → 토큰 오류, 0.55~0.78로 수정
   - Cyber인데 `border_top`이 무채? → Primary 글로우 톤으로 수정
   - Soft인데 elevation이 무겁고 directional? → ambient 톤으로 수정

10. **Muted → Background 대비 검증 (PRD에 가독성 신호가 있을 때 필수).**
    PRD에 "가독성 매우 중요", "어린이", "시니어", "전문 데이터", "8시간 사용" 같은 신호가 있으면 보조 텍스트(caption, sub-label)도 body size에서 읽혀야 한다. 디폴트 산출은 5:1 타겟이지만 hue·saturation 조합에 따라 4.1~4.5:1로 떨어져 Large-text-only가 되는 경우가 있다.
    - 콘솔 리포트의 `Muted → Background` 줄이 5.0:1 이하라면 Muted를 Text 쪽으로 더 끌어와 4.7~5.5:1대로 조정.
    - **Why:** 4.5:1는 16px 일반 텍스트 AA 경계. 4.1~4.4:1는 Large만 통과 = 18pt+ 또는 14pt+ Bold에서만 안전. 가독성 신호가 강한 PRD에선 사용자가 16px caption을 그 위에 쓴다고 가정해야 한다.

이 10가지가 통과 안 된 채로 사용자에게 넘기지 않는다.

### 12. 마무리 멘트
- `palette-preview.html`을 브라우저로 열어보라는 안내 (Glass면 진짜 blur가 적용된 걸 봐야 한다고 강조)
- 의식적으로 남긴 결정(예: "PRD는 모호했지만 Glass 1개 + Flat 2개로 비교축 만들었다")이 있다면 짧게 알려주기
- 어느 방향(컬러 + 언어 둘 다)을 더 발전시킬지 물어보기

---

## Output template

```markdown
# 🎨 컬러 팔레트 추천: {서비스 이름 또는 한 줄 설명}

> 이해한 컨텍스트: {분야}, {타깃 한 줄}, {추정/가정이 있다면 명시}
> PRD 신호 → 디자인 언어 매핑: {예: "프리미엄 + AI + 모바일" → Glass 중심으로 펼침}

---

## 1. {팔레트 이름} — {한 줄 캐치프레이즈}

**디자인 언어.** Glass / Material  
**언어 선택 이유.** {1문장. 예: "Apple 같은 프리미엄 톤을 원한다는 PRD 신호에 맞춰 backdrop-blur 기반 머티리얼로 깊이감 부여."}

**무드.** {감각적 묘사 1문장}  
**언제 쓰면 좋은가.** {어떤 비즈니스 포지셔닝/전략을 택할 때 어울리는지 1문장.}  
**레퍼런스 브랜드.** {실제 브랜드 1~3개.}  
**조화 스키마.** Monochromatic / Analogous / Complementary / Split-complementary / Triadic 중 하나  
**근거.** {왜 이 조합이 이 서비스에 맞는지 1~2문장.}

### 컬러

| 역할 | 이름 | HEX | 사용처 |
|---|---|---|---|
| Primary | Deep Indigo | `#4F46E5` | CTA, 헤더 |
| Accent | Coral Spark | `#F472B6` | 알림, 배지 |
| Background | Mist Lavender | `#F4F0FB` | 페이지 배경 |
| Text | Ink Black | `#1E1B3A` | 본문 |

### Material 토큰

| 토큰 | 값 |
|---|---|
| `surface_alpha` | 0.72 |
| `backdrop-blur` | 24px |
| `backdrop-saturate` | 180% |
| `border_top` (빛 반사) | `rgba(255,255,255,0.40)` |
| `border_bottom` | `rgba(0,0,0,0.06)` |
| `elevation L1` (subtle lift) | `0 1px 2px rgba(15,18,30,0.04)` |
| `elevation L2` (card) | `0 12px 40px rgba(15,18,30,0.10)` |
| `elevation L3` (modal) | `0 24px 64px rgba(15,18,30,0.16), 0 2px 6px rgba(15,18,30,0.06)` |
| `background_treatment` | `gradient(135deg, #4F46E5 0%, #F472B6 60%)` |
| `radius` | 18px |

### UI 요소 적용 가이드

| UI 요소 | CSS / 토큰 |
|---|---|
| 전체 배경 | `background: linear-gradient(135deg, #4F46E5 0%, #F472B6 60%)` |
| 카드 표면 | `background: rgba(255,255,255,0.72); backdrop-filter: blur(24px) saturate(180%)` |
| 카드 테두리 | `border: 1px solid rgba(255,255,255,0.40); box-shadow: inset 0 -1px 0 rgba(0,0,0,0.06)` |
| 카드 그림자 | `box-shadow: 0 12px 40px rgba(15,18,30,0.10)` |
| CTA 버튼 | `background: #4F46E5; color: #FFFFFF; border-radius: 18px` (불투명 유지 — 가독성) |
| 본문 텍스트 | `color: #1E1B3A` |
| 보조 텍스트 | `color: <muted>` |

### CSS 스니펫

```css
:root {
  --color-primary: #4F46E5;
  --color-accent: #F472B6;
  --color-bg: #F4F0FB;
  --color-text: #1E1B3A;
  --color-on-primary: #FFFFFF;
  --color-on-accent: #1E1B3A;

  --material-surface: rgba(255, 255, 255, 0.72);
  --material-blur: blur(24px) saturate(180%);
  --material-border-top: rgba(255, 255, 255, 0.40);
  --material-border-bottom: rgba(0, 0, 0, 0.06);
  --elevation-1: 0 1px 2px rgba(15, 18, 30, 0.04);
  --elevation-2: 0 12px 40px rgba(15, 18, 30, 0.10);
  --elevation-3: 0 24px 64px rgba(15, 18, 30, 0.16), 0 2px 6px rgba(15, 18, 30, 0.06);
  --radius-card: 18px;
}

/* IMPORTANT (Glass의 함정 가드): Glass 카드는 평평한 BG 위에서 blur가 거의 안 보인다.
   body나 page wrapper에 반드시 gradient/photo/radial 같은 시각 변화가 있는 BG를 깔아라. */
body {
  background:
    linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%) fixed;
  color: var(--color-text);
  min-height: 100vh;
}

.glass-card {
  background: var(--material-surface);
  backdrop-filter: var(--material-blur);
  -webkit-backdrop-filter: var(--material-blur);
  border: 1px solid var(--material-border-top);
  box-shadow: inset 0 -1px 0 var(--material-border-bottom), var(--elevation-2);
  border-radius: var(--radius-card);
}
```

> **Glass 모드에서 body BG를 빠뜨리지 마라.** 위 `body` 블록을 빼면 `glass-card`는 그냥 반투명 패널이 된다 — backdrop-filter가 흐릴 게 없으니까. Flat/Soft 언어면 body는 `background: var(--color-bg)`로 둬도 된다.

> **운영 노트.** (해당 분야에 운영상 주의사항이 있을 때만.)

---

## 2. {팔레트 이름} — …
(동일 4단 구조: 컬러 + Material 토큰 + UI 가이드 + CSS)

---

## 3. {팔레트 이름} — …
(동일 4단 구조)

---

## 다음 단계
- 브라우저에서 `palette-preview.html`을 열어 세 팔레트를 직접 비교해보세요. Glass면 실제 backdrop-blur가, Cyber면 실제 glow가 적용된 카드를 볼 수 있어요.
- 마음에 드는 방향이 정해지면 알려주세요 — 같은 언어로 톤만 더 좁히거나, 다크모드 변주를 만들거나, shadcn/Tailwind 토큰으로 변환할 수 있어요.
```

## Palettes JSON schema

`render_preview.py`에 전달하는 JSON:

```jsonc
{
  "service": "한 줄 서비스 설명",
  "context": "이해한 컨텍스트 한 줄",
  "sample_type": "fitness",
  "palettes": [
    {
      "name": "Aurora Glass",
      "tagline": "프리미엄 AI 핀테크 톤",
      "mood": "차분하지만 깊이 있는, 빛이 통과하는 듯한 머티리얼",
      "target_fit": "20~30대 모바일 자산관리 사용자",
      "design_language": "glass",           // "flat" | "glass" | "soft" | "bold" | "cyber"
      "language_rationale": "Apple 같은 프리미엄·차세대 톤이라는 PRD 신호에 맞춰 backdrop-blur 머티리얼 적용",
      "harmony": "Split-complementary",
      "rationale": "딥 인디고 + 코랄 액센트로 트러스트와 활기를 분리.",
      "reference_brands": "Apple Wallet × Linear × Arc",
      "colors": [
        {"role": "Primary",    "name": "Deep Indigo",   "hex": "#4F46E5", "usage": "CTA"},
        {"role": "Accent",     "name": "Coral Spark",   "hex": "#F472B6", "usage": "알림, 배지"},
        {"role": "Background", "name": "Mist Lavender", "hex": "#F4F0FB", "usage": "페이지 배경"},
        {"role": "Surface",    "name": "Frost White",   "hex": "#FFFFFF", "usage": "카드 표면 베이스"},
        {"role": "Text",       "name": "Ink Black",     "hex": "#1E1B3A", "usage": "본문"}
      ],
      "material": {                          // 선택. 비우면 design_language 디폴트로 자동 채움
        "surface_alpha": 0.72,
        "blur": "24px",
        "saturate": "180%",
        "border_top": "rgba(255,255,255,0.40)",
        "border_bottom": "rgba(0,0,0,0.06)",
        "elevation": [
          "0 1px 2px rgba(15,18,30,0.04)",
          "0 12px 40px rgba(15,18,30,0.10)",
          "0 24px 64px rgba(15,18,30,0.16), 0 2px 6px rgba(15,18,30,0.06)"
        ],
        "background_treatment": "gradient",  // enum: keyword 하나만 — 자유 CSS 문자열 금지
        "radius": "18px"
      }
    }
  ]
}
```

**JSON 규칙:**
- `palettes` 배열은 정확히 3개.
- `colors` 배열은 **최소 3개(Primary/Background/Text), 최대 8개**.
- `design_language` 필드는 **모든 팔레트에 명시 필수** (없으면 스크립트가 `"flat"`으로 가정해서 평면 톤으로 떨어짐). 허용 값: `"flat"`, `"glass"`, `"soft"`, `"bold"`, `"cyber"`.
- `material` 객체는 선택. 비우면 `design_language`에 맞는 디폴트가 자동 적용. 부분만 명시도 가능 (나머지는 디폴트).
- **`material.background_treatment`는 enum 키워드 하나만** — 자유 CSS 문자열을 넣지 말 것. 허용 값:
  - `"solid"` — 단색 BG (Flat/Soft 일반)
  - `"gradient"` — 135° linear-gradient(Primary → Secondary → Accent). Glass 권장
  - `"soft-radial"` — Primary·Accent 각 코너에서 살짝 발하는 radial. Soft 권장
  - `"oled-vignette"` — OLED 블랙 + Primary glow at top. Cyber 권장
  - `"color-block"` — Primary 큰 블록 + BG 영역 분할. Bold 권장
  - 실제 CSS는 스크립트가 키워드에 맞춰 자동 생성하므로 `"linear-gradient(135deg, #4F46E5, #F472B6)"` 같은 raw CSS를 넣으면 안 됨.
- `language_rationale`은 PALETTES.md에 그대로 들어가므로 1문장으로 정직하게 작성.

**`sample_type` 필드** — 미리보기에 표시될 샘플 카드 콘텐츠. 가능한 값: `crypto`, `fintech`, `fitness`, `meditation`, `fnb`, `saas`, `edu`, `ecommerce`, `generic`. 생략하면 키워드로 자동 추론.

---

## Notes on design language pairing

- **PRD 신호가 강하게 한 언어를 가리키면, 3개 팔레트 모두 같은 언어로 가는 게 정직하다.** "Apple 같은 프리미엄 AI" PRD에 Flat을 끼워 넣으면 사용자는 그게 왜 거기 있는지 모른다.
- **PRD 신호가 모호하면 의도적으로 다른 언어를 섞어 비교축을 만든다.** "핀테크 컬러 추천해줘"만 받았으면 Glass 1개(모던) + Flat 1개(안전) + Cyber 1개(트레이딩 다크)로 펼치면 사용자가 방향 자체를 고를 수 있다.
- **언어와 다크/라이트는 직교다.** Glass는 라이트도 다크도 가능. Cyber는 거의 다크만. Soft는 라이트가 자연스러움.
- **Glass의 함정: BG가 평평하면 효과가 안 보인다.** Glass 모드면 background_treatment를 `solid` 말고 `gradient`나 `soft-radial`로 가야 한다. 단색 BG 위 Glass 카드는 그냥 반투명 패널일 뿐.

## Notes on good palettes

- **채도(S)는 leveled 분포가 디자이너 톤.** 한 팔레트 안에 채도 60%+ 색이 2개 이상 있으면 거의 항상 충돌감. 보통 *"비비드 1개 + muted 1개 + 무채 가까운 베이스"* 위계.
- **명도(L) 위계는 화면 위계의 핵심.** Primary와 Accent의 명도 차이가 15% 이상.
- **다 비비드하면 피곤하다.** 한 팔레트 안에서 비비드한 건 Primary 하나면 충분. (단, Cyber는 의도된 예외)
- **보색(hue 120°+)은 한쪽 채도를 풀어야 한다.**
- **Tailwind 디폴트 그대로면 "AI 느낌"이 즉시 읽힌다.** 같은 hue family 안에서 채도 ±5~8 또는 명도 ±3~5만 흔들어도 자기 톤이 된다.
- **Background가 순백(#FFFFFF)이면 차갑고 평평하다.** Glass에선 특히 치명적 — backdrop-blur가 안 보인다.
- **Text를 #000000으로 두면 너무 강하다.** 살짝 톤 들어간 어두운 색이 부드럽다.
- **억지로 색을 늘리지 마라.**

## Notes on dark-mode-first palettes

다크모드 우선 서비스(개발자 도구, 음악·영상, 게임, 거래소, 다크 SaaS, Cyber 언어 팔레트)는 라이트와 다른 사고법이 필요하다.

- **Background = 가장 어두운 톤.** 예: `#0B0D17`. 순흑(#000)은 깊이감이 없다 (Cyber 제외 — OLED 의도면 OK).
- **Surface = 한 단계 위 surface.** BG보다 명도 0.02~0.05 위, 거의 같은 색.
- **Primary = 발광하듯 채도 높은 색.**
- **Text = 살짝 톤 들어간 오프화이트.**

### 금융·트레이딩 다크모드 추가 가이드 (보통 Cyber 언어로 떨어짐)

- **시그널 컬러 정의** — 상승/하락을 brand color와 별도로. 한국은 상승=빨강, 하락=파랑. 글로벌은 반대.
- **brand color ≠ 시그널 컬러 색역.** Primary가 빨강이면 상승색은 다른 색역에서.

## When to consult references

- 분야 관습이 결과에 크게 영향을 주는 경우 → `references/domain-conventions.md`
- 사용자가 "이 색은 절대 피해줘", "경쟁사와 달라야 해" 같은 제약을 둔 경우, 도메인 표 안에서 회피색/관습색을 확인.
