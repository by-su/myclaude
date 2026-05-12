# GSAP 레퍼런스

`gsap@3.12.5`. ScrollTrigger와 Flip 플러그인은 importmap에 이미 등록되어 있다.

## 사용 전 setup (React)

```js
import gsap from "skills/motion-lab/references/gsap";
import ScrollTrigger from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);
```

React에서는 `useLayoutEffect` 안에서 setup, cleanup에서 모두 kill.

```jsx
useLayoutEffect(() => {
  const ctx = gsap.context(() => {
    gsap.to(".box", { x: 100, duration: 1, ease: "power3.out" });
  }, scopeRef);
  return () => ctx.revert();   // 매우 중요 - 메모리 누수/중복 트리거 방지
}, []);
```

`gsap.context()`로 스코프 지정. `ctx.revert()`로 한꺼번에 cleanup. ScrollTrigger도 자동으로 정리됨.

## 기본 tween

```js
gsap.to(target, { x: 200, opacity: 1, duration: 1, ease: "power3.out" });
gsap.from(target, { y: 30, opacity: 0, duration: 0.8 });    // 이 상태에서 출발 → 현재로
gsap.fromTo(target, { y: 30, opacity: 0 }, { y: 0, opacity: 1 });
gsap.set(target, { x: 100 });    // 즉시 (애니메이션 없음)
```

target은 selector string, DOM node, ref.current, 노드 배열 모두 OK.

## Easing

- `power1.out` (약함) → `power2.out` → `power3.out` (자주 씀) → `power4.out` (강함)
- `expo.out` — 매우 강한 감속, 임팩트 있음
- `back.out(1.7)` — 약간 튕김 (괄호 숫자가 강도)
- `elastic.out(1, 0.3)` — 통통 튐
- `circ.out`, `sine.inOut` — 부드러움

기본 `power3.out`이 가장 자주 쓴다. `none`(linear)은 ScrollTrigger scrub 외엔 쓰지 않는다.

## Stagger

```js
gsap.from(".item", {
  y: 30, opacity: 0, duration: 0.7, ease: "power3.out",
  stagger: 0.08                  // 자식 간 80ms
});

// 그리드 기반:
gsap.from(".cell", {
  scale: 0, opacity: 0,
  stagger: { amount: 1, grid: [5, 5], from: "center" }
});
```

`from`: `"start"` | `"end"` | `"center"` | `"random"` | `"edges"` | `[x, y]`.

## Timeline

```js
const tl = gsap.timeline({ defaults: { duration: 0.7, ease: "power3.out" } });
tl.from(".title", { y: 30, opacity: 0 })
  .from(".subtitle", { y: 20, opacity: 0 }, "-=0.5")     // 0.5초 겹쳐 시작
  .from(".cta", { scale: 0.9, opacity: 0 }, "<")          // 직전 시작과 같이
  .from(".image", { x: 50, opacity: 0 }, "+=0.1");        // 직전 끝에서 0.1초 후
```

position 파라미터:
- `"<"` 직전 트윈의 시작
- `">"` 직전 트윈의 끝
- `"-=0.5"` 직전 끝에서 0.5초 빼서 (즉 겹침)
- `"+=0.2"` 직전 끝에서 0.2초 후
- `"label"` 라벨

```js
tl.addLabel("middle")
  .to(".x", { x: 100 }, "middle")
  .to(".y", { y: 100 }, "middle");
```

## ScrollTrigger 기본

```js
gsap.to(".bg", {
  yPercent: -50,
  ease: "none",
  scrollTrigger: {
    trigger: ".section",
    start: "top top",       // trigger top이 viewport top에 닿을 때 시작
    end: "bottom top",      // trigger bottom이 viewport top에 닿을 때 끝
    scrub: true             // 스크롤 진행에 따라 진행
  }
});
```

### start / end 문자열

`"<trigger-edge> <viewport-edge>"` 형식.

- `"top top"`, `"top center"`, `"top bottom"` — trigger 상단 vs 뷰포트 어딘가
- `"top 80%"` — trigger top이 뷰포트 80% 위치에 올 때
- `"bottom bottom-=100"` — trigger 하단이 뷰포트 하단보다 100px 위에 올 때
- `"+=500"` (end에서) — start로부터 500px 스크롤 후

### 자주 쓰는 옵션

```js
scrollTrigger: {
  trigger: ".section",
  start: "top top",
  end: "+=2000",          // start로부터 2000px 동안
  scrub: 1,               // 1초 lag (부드러움). true는 즉시.
  pin: true,              // trigger를 뷰포트에 고정
  pinSpacing: true,       // pin 동안 다음 콘텐츠를 밀어냄 (기본 true)
  anticipatePin: 1,
  snap: { snapTo: "labels", duration: 0.3 },
  markers: true,          // 개발 시각화 (배포 전에 꼭 제거)
  toggleActions: "play none none reverse",   // onEnter onLeave onEnterBack onLeaveBack
  onUpdate: (self) => console.log(self.progress)
}
```

`scrub: true`는 스크롤 = 애니메이션 진행. `toggleActions`는 트리거 진입 시 한 번 재생.

### Pin 패턴 — 섹션 고정 + 시퀀스

```js
const tl = gsap.timeline({
  scrollTrigger: {
    trigger: ".pin-section",
    start: "top top",
    end: "+=3000",
    pin: true,
    scrub: 1
  }
});
tl.to(".step-1", { opacity: 0 })
  .to(".step-2", { opacity: 1 }, "<")
  .to(".step-2", { opacity: 0 })
  .to(".step-3", { opacity: 1 }, "<");
```

스크롤 길이만큼 섹션이 고정되고 그 안에서 시퀀스가 재생된다. Apple의 product 페이지 패턴.

### 가로 스크롤 (horizontal scroll)

```js
const sections = gsap.utils.toArray(".horizontal-section");
gsap.to(sections, {
  xPercent: -100 * (sections.length - 1),
  ease: "none",
  scrollTrigger: {
    trigger: ".horizontal-wrapper",
    pin: true,
    scrub: 1,
    end: () => "+=" + document.querySelector(".horizontal-wrapper").offsetWidth
  }
});
```

수직 스크롤 → 수평 이동.

### Reveal on scroll (간단)

```js
gsap.utils.toArray(".reveal").forEach(el => {
  gsap.from(el, {
    y: 40, opacity: 0, duration: 0.9, ease: "power3.out",
    scrollTrigger: { trigger: el, start: "top 80%", toggleActions: "play none none reverse" }
  });
});
```

각 요소가 뷰포트 80% 지점에 도달하면 페이드인.

## 자주 쓰는 유틸

```js
gsap.utils.toArray(selector)        // 항상 배열로
gsap.utils.random(0, 100)
gsap.utils.shuffle(array)
gsap.utils.clamp(0, 1, value)
gsap.utils.mapRange(0, 100, 0, 1, 50)   // = 0.5
```

## Flip 플러그인 — layout transition

GSAP의 FLIP. Framer Motion의 `layout`과 비슷하지만 imperative.

```js
import Flip from "gsap/Flip";
gsap.registerPlugin(Flip);

const state = Flip.getState(".items");
// DOM 변경 (reorder, add, remove)
Flip.from(state, { duration: 0.6, ease: "power3.out", absolute: true });
```

React에서는 Framer Motion `layout`을 쓰는 게 보통 더 자연스럽다. Flip은 vanilla나 정밀 제어가 필요할 때.

## React + GSAP 보일러플레이트

```jsx
function Demo() {
  const scope = useRef(null);
  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from(".fade-up", {
        y: 30, opacity: 0, duration: 0.9, ease: "power3.out",
        stagger: 0.08,
        scrollTrigger: { trigger: scope.current, start: "top 70%" }
      });
    }, scope);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={scope}>
      <h1 className="fade-up">Title</h1>
      <p className="fade-up">Body</p>
    </div>
  );
}
```

`useLayoutEffect` + `gsap.context(..., scopeRef)` + `ctx.revert()` 패턴을 항상 유지. React StrictMode에서 중복 트리거 없이 안전.

## 안티패턴

- `markers: true` 남기고 사용자에게 전달 — 데모에 빨간 라벨 보임. 항상 제거.
- `useLayoutEffect` 없이 `useEffect`로 ScrollTrigger 등록 — 깜빡임 발생
- `ctx.revert()` 빠뜨림 — 중복 트리거, 메모리 누수
- `none` easing을 scrub 아닌 곳에 사용 — 답답하고 어색
- `pin: true` 인데 `end`가 너무 짧음 — 의미 없는 짧은 고정
