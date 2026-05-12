# Framer Motion 레퍼런스

데모는 `framer-motion@11.18.2`를 import한다. 이 문서는 자주 쓰는 API를 카탈로그한다.

## 핵심: motion 컴포넌트

```jsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -20 }}
  transition={{ duration: 0.6, ease: EASE_OUT_QUART }}
/>
```

- `initial`: mount 시작 상태
- `animate`: 도달할 상태 (state 따라 바뀌면 자동 트랜지션)
- `exit`: AnimatePresence 안에서만 동작
- `transition`: duration(s), ease, delay, type:"spring"

`initial={false}`로 첫 마운트 애니메이션을 끌 수 있다 (이미 그 상태로 시작).

## Variants — 부모가 자식 stagger 컨트롤

```jsx
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.2 }
  }
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE_OUT_QUART } }
};

<motion.ul variants={container} initial="hidden" animate="show">
  {items.map(i => <motion.li key={i.id} variants={item}>{i.name}</motion.li>)}
</motion.ul>
```

stagger 60-100ms가 자연스러운 범위.

## AnimatePresence — exit 애니메이션

```jsx
<AnimatePresence mode="wait">
  {open && (
    <motion.div
      key="panel"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
    />
  )}
</AnimatePresence>
```

- `mode="wait"`: 이전 요소 exit 끝나야 새 요소 enter
- `mode="popLayout"`: 리스트에서 요소 제거 시 형제들이 부드럽게 자리 이동
- `mode="sync"` (default): 동시에 진행

리스트의 추가/제거에는 `mode="popLayout"` + `layout` prop을 같이 쓴다.

## Layout 애니메이션 — FLIP

```jsx
<motion.div layout transition={{ duration: 0.4, ease: EASE_OUT_QUART }} />
```

크기/위치가 바뀌면 자동으로 부드럽게 트랜지션. `layout` prop이 켜진 자식은 부모 grid/flex 재배치도 따라간다.

### layoutId — shared element transition

```jsx
{items.map(i => (
  <motion.div key={i.id} layoutId={`card-${i.id}`} onClick={() => setActive(i)} />
))}

<AnimatePresence>
  {active && (
    <motion.div layoutId={`card-${active.id}`} className="fixed inset-0 ..." />
  )}
</AnimatePresence>
```

작은 카드 → 풀스크린 모달 같은 "같은 것의 다른 모습" 전환. Apple Photos 같은 효과.

### LayoutGroup — 탭 인디케이터

```jsx
<LayoutGroup>
  {tabs.map(t => (
    <button key={t} onClick={() => setActive(t)} className="relative px-4 py-2">
      {t}
      {active === t && (
        <motion.div
          layoutId="active-tab"
          className="absolute inset-0 bg-white/10 rounded-md -z-10"
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
        />
      )}
    </button>
  ))}
</LayoutGroup>
```

탭 사이를 sliding pill로 자연스럽게 이동.

## Gestures

```jsx
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  whileFocus={{ scale: 1.05 }}
  transition={{ type: "spring", stiffness: 400, damping: 17 }}
/>
```

`whileHover`, `whileTap`, `whileFocus`, `whileDrag`, `whileInView`는 모두 같은 패턴.

### Drag

```jsx
<motion.div
  drag                          // 모든 방향
  drag="x"                      // X축만
  dragConstraints={{ left: -100, right: 100 }}
  dragElastic={0.2}             // 경계 밖 탄성
  dragSnapToOrigin              // 놓으면 제자리로
  onDragEnd={(e, info) => {
    if (Math.abs(info.offset.x) > 100) handleDismiss();
  }}
/>
```

### useDragControls — 핸들 분리

```jsx
const controls = useDragControls();
<motion.div drag dragListener={false} dragControls={controls}>
  <div onPointerDown={(e) => controls.start(e)}>≡ handle</div>
  {/* content */}
</motion.div>
```

## Scroll

### useScroll

```jsx
const { scrollY, scrollYProgress } = useScroll();              // window
const { scrollYProgress } = useScroll({ target: ref });        // 요소 기준
const { scrollYProgress } = useScroll({
  target: ref,
  offset: ["start end", "end start"]                            // 진입~퇴장
});
```

`offset`은 `[target-edge, viewport-edge]` 쌍. `"start end"` = 타깃 시작이 뷰포트 끝에 닿을 때 (즉 막 보이기 시작).

### useTransform — 값 매핑

```jsx
const { scrollYProgress } = useScroll();
const opacity = useTransform(scrollYProgress, [0, 0.5, 1], [0, 1, 0]);
const y = useTransform(scrollYProgress, [0, 1], [0, -200]);

<motion.div style={{ opacity, y }} />
```

스크롤 진행 0→1에 따라 다른 값으로 매핑. parallax, fade-in/out, color shift 등 만능.

### useSpring으로 부드럽게

```jsx
const smoothProgress = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });
```

스크롤이 너무 빡빡하면 spring으로 한 번 감싸기. 부드러운 lag 효과.

### useInView — 한 번 보이면 트리거

```jsx
const ref = useRef(null);
const inView = useInView(ref, { once: true, margin: "-100px" });

<motion.div
  ref={ref}
  initial={{ opacity: 0, y: 30 }}
  animate={inView ? { opacity: 1, y: 0 } : {}}
  transition={{ duration: 0.7, ease: EASE_OUT_QUART }}
/>
```

스크롤 reveal의 가장 간단한 형태. `once: true`로 한 번만.

대안: `whileInView`

```jsx
<motion.div
  initial={{ opacity: 0, y: 30 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, margin: "-100px" }}
/>
```

ref 안 쓰고 더 간결.

## MotionValue — 직접 다루기

```jsx
const x = useMotionValue(0);
const rotate = useTransform(x, [-100, 100], [-15, 15]);

<motion.div style={{ x, rotate }} drag="x" />
```

state 트리거 없이 매 프레임 업데이트. 마우스 follow, gesture 기반 변형에 유용.

### useMotionValueEvent

```jsx
useMotionValueEvent(scrollY, "change", (latest) => {
  setHideNav(latest > prev);
});
```

MotionValue 변화에 reactive callback.

## Transition 옵션 정리

```jsx
transition={{
  duration: 0.6,
  ease: [0.22, 1, 0.36, 1],   // cubic-bezier 또는 "easeOut"
  delay: 0.1,
  repeat: Infinity,            // 무한 루프
  repeatType: "reverse",       // yoyo
  type: "spring",
  stiffness: 260,
  damping: 26,
  mass: 1,
  // 속성별로 다르게:
  opacity: { duration: 0.3 },
  y: { type: "spring", stiffness: 300 }
}}
```

## MotionConfig — 전역 default

```jsx
<MotionConfig reducedMotion="user" transition={{ duration: 0.6, ease: EASE_OUT_QUART }}>
  <App />
</MotionConfig>
```

- `reducedMotion="user"`: OS 설정 따라 자동 단축
- 모든 자식 motion 컴포넌트의 default transition

템플릿에 이미 들어있다. 그대로 유지.

## 자주 쓰는 import 줄

```js
import {
    motion, AnimatePresence, MotionConfig, LayoutGroup, Reorder,
    useScroll, useTransform, useSpring, useMotionValue,
    useMotionValueEvent, useInView
} from "skills/motion-lab/references/framer-motion";
```

템플릿에 이미 모두 import되어 있다.
