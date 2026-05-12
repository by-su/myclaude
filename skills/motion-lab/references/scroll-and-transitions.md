# 스크롤 & 페이지 전환 레시피

스크롤에 반응하는 모션과 화면/요소 전환. Framer Motion으로 충분한 경우, GSAP ScrollTrigger가 더 강한 경우를 구분한다.

## 선택 기준

| 상황 | 라이브러리 |
|---|---|
| 단순 reveal on scroll | Framer Motion `whileInView` |
| 가벼운 parallax | Framer Motion `useScroll` + `useTransform` |
| 긴 시퀀스 / pin / scrub | **GSAP ScrollTrigger** |
| 가로 스크롤 섹션 | **GSAP ScrollTrigger** |
| 라우트 전환 / mount-unmount | Framer Motion `AnimatePresence` |

## 1. Reveal on scroll (가장 흔함)

### 1-A. Framer Motion (간단)

```jsx
<motion.div
  initial={{ opacity: 0, y: 40 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, margin: "-100px" }}
  transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
>
  Content
</motion.div>
```

`margin: "-100px"`는 뷰포트 위쪽 100px 안쪽에 들어와야 트리거(= 화면 안에 좀 들어왔을 때). `once: true`로 한 번만.

### 1-B. 자식 stagger 있는 reveal

```jsx
const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } }
};
const item = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } }
};

<motion.ul
  variants={container}
  initial="hidden"
  whileInView="show"
  viewport={{ once: true, margin: "-80px" }}
>
  {items.map(i => <motion.li key={i.id} variants={item}>{i.name}</motion.li>)}
</motion.ul>
```

리스트나 그리드의 reveal 표준 패턴.

## 2. Parallax (Framer Motion)

```jsx
function ParallaxImage({ src }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"]
  });
  const y = useTransform(scrollYProgress, [0, 1], ["-15%", "15%"]);
  return (
    <div ref={ref} className="relative h-[60vh] overflow-hidden rounded-2xl">
      <motion.img src={src} style={{ y }} className="absolute inset-0 w-full h-[130%] object-cover" />
    </div>
  );
}
```

이미지가 컨테이너보다 크고(130%), 스크롤에 따라 ±15% 이동. `overflow-hidden`이 컨테이너에 필수.

## 3. Scrub 애니메이션 (GSAP)

요소가 화면을 지나가는 동안 진행도에 맞춰 변화:

```js
useLayoutEffect(() => {
  const ctx = gsap.context(() => {
    gsap.to(".scrub-target", {
      x: 200, rotate: 180, ease: "none",
      scrollTrigger: {
        trigger: ".scrub-target",
        start: "top bottom",
        end: "bottom top",
        scrub: 1                  // 1초 lag, 부드러움
      }
    });
  }, scope);
  return () => ctx.revert();
}, []);
```

`scrub: 1`은 부드러운 lag, `scrub: true`는 즉시 따라옴. UX는 lag 있는 쪽이 보통 더 좋음.

## 4. Pin 섹션 + 시퀀스 (GSAP, 매우 강력)

```jsx
function PinSequence() {
  const scope = useRef(null);
  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: ".pin-wrap",
          start: "top top",
          end: "+=3000",
          pin: true,
          scrub: 1
        }
      });
      tl.to(".step-1", { opacity: 0, scale: 0.9 })
        .fromTo(".step-2", { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1 }, "<0.2")
        .to(".step-2", { opacity: 0, scale: 0.9 })
        .fromTo(".step-3", { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1 }, "<0.2");
    }, scope);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={scope}>
      <div className="pin-wrap h-screen relative overflow-hidden">
        <div className="step-1 absolute inset-0 grid place-items-center text-6xl">Step 1</div>
        <div className="step-2 absolute inset-0 grid place-items-center text-6xl opacity-0">Step 2</div>
        <div className="step-3 absolute inset-0 grid place-items-center text-6xl opacity-0">Step 3</div>
      </div>
    </div>
  );
}
```

`pin: true` + `end: "+=3000"`로 3000px 스크롤 동안 섹션 고정. 그 안에서 timeline이 scrub로 재생. Apple 제품 페이지 패턴.

## 5. Sticky stack — 카드 위에 카드 (CSS sticky)

라이브러리 거의 없이 sticky로:

```jsx
<div className="relative">
  {cards.map((c, i) => (
    <div
      key={c.id}
      className="sticky top-24 h-[70vh] mb-4"
      style={{ marginTop: i === 0 ? 0 : "-20vh" }}
    >
      <div className="h-full rounded-3xl bg-zinc-900 p-12" style={{ transform: `scale(${1 - (cards.length - i) * 0.02})` }}>
        <h3 className="text-4xl">{c.title}</h3>
      </div>
    </div>
  ))}
</div>
```

각 카드가 top에 sticky. 다음 카드가 올라와 덮음. CSS만으로 deck 효과.

더 정교하게 하려면 Framer Motion `useScroll` per-card:

```jsx
function StackCard({ index, total, card }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "start start"] });
  const scale = useTransform(scrollYProgress, [0, 1], [1, 1 - (total - index) * 0.04]);
  return (
    <div ref={ref} className="sticky top-24 h-[70vh]">
      <motion.div style={{ scale }} className="h-full rounded-3xl bg-zinc-900 p-12">
        {card.content}
      </motion.div>
    </div>
  );
}
```

## 6. 가로 스크롤 섹션 (GSAP)

```jsx
function HorizontalScroll() {
  const scope = useRef(null);
  const track = useRef(null);
  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const sections = gsap.utils.toArray(".h-slide");
      gsap.to(sections, {
        xPercent: -100 * (sections.length - 1),
        ease: "none",
        scrollTrigger: {
          trigger: track.current,
          pin: true,
          scrub: 1,
          end: () => "+=" + (track.current.scrollWidth - window.innerWidth)
        }
      });
    }, scope);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={scope}>
      <div ref={track} className="h-screen relative overflow-hidden">
        <div className="flex h-full w-[400vw]">
          {[1,2,3,4].map(n => (
            <div key={n} className="h--slide w-screen h-full grid place-items-center text-7xl">
              {n}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

수직 스크롤 → 수평 이동. 4섹션이면 wrapper width를 400vw로.

## 7. Scroll-linked progress bar

```jsx
function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });
  return (
    <motion.div
      style={{ scaleX, originX: 0 }}
      className="fixed top-0 left-0 right-0 h-1 bg-white z-50"
    />
  );
}
```

상단에 진행 bar. `originX: 0`이 핵심.

## 8. Hide-on-scroll nav

```jsx
function StickyNav() {
  const [hidden, setHidden] = useState(false);
  const { scrollY } = useScroll();
  useMotionValueEvent(scrollY, "change", (latest) => {
    const prev = scrollY.getPrevious();
    setHidden(latest > prev && latest > 100);
  });
  return (
    <motion.nav
      animate={{ y: hidden ? -100 : 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="fixed top-0 inset-x-0 h-16 bg-zinc-950/80 backdrop-blur-md z-50"
    >
      ...
    </motion.nav>
  );
}
```

아래로 스크롤할 때 숨고, 위로 스크롤하면 다시 나옴.

## 9. 페이지 / 라우트 전환

라우터 없는 단일 페이지에서는 view state로 전환:

```jsx
const [view, setView] = useState("home");

<AnimatePresence mode="wait">
  <motion.div
    key={view}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
  >
    {view === "home" ? <Home /> : <About />}
  </motion.div>
</AnimatePresence>
```

`mode="wait"`로 이전 페이지가 나간 후 새 페이지가 들어옴. `key={view}` 필수.

## 10. Section divider — 다음 섹션이 위로 슬라이드

```jsx
function SectionLift({ children, bg = "bg-zinc-900" }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "start start"] });
  const y = useTransform(scrollYProgress, [0, 1], [80, 0]);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [0, 1]);
  return (
    <motion.section
      ref={ref}
      style={{ y, opacity }}
      className={`min-h-screen ${bg} rounded-t-[40px]`}
    >
      {children}
    </motion.section>
  );
}
```

위로 살짝 떠오르며 등장하는 섹션. 둥근 윗 모서리로 "다른 시트가 올라오는" 느낌.

## 11. 텍스트 reveal on scroll (한 줄씩)

```jsx
function RevealLines({ lines }) {
  return (
    <div className="space-y-2">
      {lines.map((line, i) => (
        <div key={i} className="overflow-hidden">
          <motion.div
            initial={{ y: "100%" }}
            whileInView={{ y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: i * 0.08 }}
          >
            {line}
          </motion.div>
        </div>
      ))}
    </div>
  );
}
```

각 줄을 `overflow-hidden` 컨테이너로 감싸고 그 안에서 위로 올라오게. 줄 단위 텍스트 reveal 표준.

## 안티패턴

- 모든 요소에 scroll-linked motion — CPU 낭비, 화면이 부산함
- parallax 강도가 너무 셈 (50% 이상) — 어지러움
- `whileInView` + `once: false` 무한 트리거 — 보였다 안 보였다 반복하면 거슬림. `once: true`가 default여야 함.
- pin 섹션이 너무 길어서 (5000px+) 사용자가 답답함
- scrub에 `ease: "power2.out"` — scrub은 항상 `ease: "none"`
- horizontal scroll을 모바일에서 강제 — 터치 UX 깨짐. `min-width: 768px`에서만 적용 권장.
