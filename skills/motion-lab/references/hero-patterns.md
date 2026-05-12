# 히어로 섹션 레시피

랜딩페이지 첫 화면. 1-2초 안에 "와, 잘 만들었네"라는 인상을 줘야 한다. 욕심내지 말고 한 가지 강한 효과 + 작은 보조 모션 조합이 보통 정답.

## 0. 히어로 구성 공식

대부분의 좋은 히어로는 다음 4개 요소가 단계적으로 등장:

1. **Eyebrow** (작은 라벨) — `delay: 0, y: 10, duration: 0.6`
2. **Title** (큰 헤드라인) — `delay: 0.1, 단어/줄 단위 stagger`
3. **Subtitle** (설명 한 줄) — `delay: 0.5, y: 20, duration: 0.7`
4. **CTA** (버튼 1-2개) — `delay: 0.7, opacity + scale`

배경 요소(이미지, gradient, particles)는 가장 먼저 또는 마지막에 페이드인.

## 1. Word-by-word split text (Framer Motion만으로)

GSAP SplitText 없이도 가능:

```jsx
function SplitWords({ text, delay = 0, stagger = 0.06 }) {
  const words = text.split(" ");
  return (
    <span aria-label={text}>
      {words.map((word, i) => (
        <span key={i} className="inline-block overflow-hidden mr-[0.25em] last:mr-0">
          <motion.span
            className="inline-block"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            transition={{
              duration: 0.8,
              ease: [0.22, 1, 0.36, 1],
              delay: delay + i * stagger
            }}
          >
            {word}
          </motion.span>
        </span>
      ))}
    </span>
  );
}

// 사용:
<h1 className="text-7xl font-display tracking-tight">
  <SplitWords text="Make beautiful interfaces" />
</h1>
```

- 각 단어를 `overflow-hidden` 컨테이너로 감싸고 안에서 위로 올라옴 = "마스크 reveal"
- 단어 단위 stagger 50-80ms가 자연스러움
- `mr-[0.25em]`로 단어 간격 보존

## 2. Character-by-character split text

더 정밀하게 글자 단위:

```jsx
function SplitChars({ text, delay = 0 }) {
  return (
    <span aria-label={text}>
      {text.split("").map((ch, i) => (
        <span key={i} className="inline-block overflow-hidden">
          <motion.span
            className="inline-block"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            transition={{
              duration: 0.6,
              ease: [0.22, 1, 0.36, 1],
              delay: delay + i * 0.025
            }}
          >
            {ch === " " ? " " : ch}
          </motion.span>
        </span>
      ))}
    </span>
  );
}
```

글자 단위는 30ms 이하 stagger가 좋다. 너무 느리면 답답함.

## 3. Multi-line slide reveal

여러 줄의 헤드라인:

```jsx
const lines = ["Design with code.", "Ship with confidence.", "Move with grace."];

<h1 className="text-7xl font-display leading-[1.05] tracking-tight">
  {lines.map((line, i) => (
    <span key={i} className="block overflow-hidden">
      <motion.span
        className="block"
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 + i * 0.1 }}
      >
        {line}
      </motion.span>
    </span>
  ))}
</h1>
```

각 줄을 마스크. 줄 간 100ms stagger.

## 4. Mouse-follow gradient blob (배경)

```jsx
function GradientBlob() {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 50, damping: 20 });
  const sy = useSpring(y, { stiffness: 50, damping: 20 });

  useEffect(() => {
    const onMove = (e) => { x.set(e.clientX); y.set(e.clientY); };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  return (
    <motion.div
      style={{ x: sx, y: sy, translateX: "-50%", translateY: "-50%" }}
      className="fixed top-0 left-0 w-[600px] h-[600px] rounded-full pointer-events-none -z-10"
    >
      <div className="w-full h-full rounded-full bg-gradient-to-br from-purple-500/40 via-pink-500/30 to-orange-400/40 blur-[120px]" />
    </motion.div>
  );
}
```

큰 spring lag(stiffness 50)으로 부드럽게 따라옴. blur가 핵심 — 없으면 그냥 원이 따라옴.

## 5. Animated gradient mesh (CSS만)

가장 가볍고 강한 배경:

```jsx
<div className="absolute inset-0 -z-10 overflow-hidden">
  <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-purple-600/40 blur-[120px] animate-blob" />
  <div className="absolute top-40 -right-40 w-[600px] h-[600px] rounded-full bg-pink-500/40 blur-[120px] animate-blob animation-delay-2000" />
  <div className="absolute -bottom-40 left-40 w-[600px] h-[600px] rounded-full bg-orange-400/40 blur-[120px] animate-blob animation-delay-4000" />
</div>

<style>{`
  @keyframes blob {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33%      { transform: translate(40px, -50px) scale(1.1); }
    66%      { transform: translate(-30px, 30px) scale(0.95); }
  }
  .animate-blob { animation: blob 14s ease-in-out infinite; }
  .animation-delay-2000 { animation-delay: 2s; }
  .animation-delay-4000 { animation-delay: 4s; }
`}</style>
```

3개 blob이 다른 phase로 움직이며 부드러운 mesh. blur가 무겁지만 GPU compositing이라 괜찮음.

## 6. 컨텐츠가 진입하는 동시 BG가 살짝 줌아웃

```jsx
<motion.div
  initial={{ scale: 1.1 }}
  animate={{ scale: 1 }}
  transition={{ duration: 1.5, ease: [0.22, 1, 0.36, 1] }}
  className="absolute inset-0 -z-10"
>
  <img src="..." className="w-full h-full object-cover" />
  <div className="absolute inset-0 bg-black/40" />
</motion.div>
```

배경이 1.5초 동안 1.1 → 1.0으로 천천히 줄어드는 동안 텍스트가 위에서 등장. 영화적인 도입.

## 7. Big kinetic number

```jsx
<motion.h2
  initial={{ scale: 0.6, opacity: 0 }}
  animate={{ scale: 1, opacity: 1 }}
  transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
  className="text-[20rem] font-display leading-none tracking-tighter"
>
  2026
</motion.h2>
```

거대한 디스플레이 폰트. `EASE_EXPO_OUT`이 임팩트 살림.

## 8. Marquee (가로 흐르는 텍스트)

```jsx
function Marquee({ children, speed = 30 }) {
  return (
    <div className="overflow-hidden whitespace-nowrap">
      <motion.div
        className="inline-block"
        animate={{ x: ["0%", "-50%"] }}
        transition={{ duration: speed, ease: "linear", repeat: Infinity }}
      >
        <span className="inline-block">{children}</span>
        <span className="inline-block">{children}</span>
      </motion.div>
    </div>
  );
}

// 사용:
<Marquee speed={40}>
  <span className="text-7xl font-display mx-8 opacity-50">DESIGN · CODE · MOTION · </span>
</Marquee>
```

내용을 2번 렌더해서 끊김 없이 무한 반복. linear easing 필수.

## 9. 마우스 follow 글자 spotlight

```jsx
function SpotlightText({ text }) {
  const ref = useRef(null);
  const [pos, setPos] = useState({ x: -1000, y: -1000 });
  return (
    <div
      ref={ref}
      onMouseMove={(e) => {
        const r = ref.current.getBoundingClientRect();
        setPos({ x: e.clientX - r.left, y: e.clientY - r.top });
      }}
      onMouseLeave={() => setPos({ x: -1000, y: -1000 })}
      className="relative text-7xl font-display tracking-tight"
    >
      <div className="text-zinc-700">{text}</div>
      <div
        className="absolute inset-0 text-white"
        style={{
          WebkitMaskImage: `radial-gradient(circle 150px at ${pos.x}px ${pos.y}px, black 0%, transparent 100%)`,
          maskImage: `radial-gradient(circle 150px at ${pos.x}px ${pos.y}px, black 0%, transparent 100%)`,
          transition: "mask-image 0.1s"
        }}
      >
        {text}
      </div>
    </div>
  );
}
```

회색 텍스트 위에 흰색 텍스트가 마우스 주변에서만 보이는 spotlight. `mask-image` radial-gradient가 핵심.

## 10. Image grid stagger entrance

```jsx
const container = {
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.3 } }
};
const cell = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] } }
};

<motion.div
  variants={container}
  initial="hidden"
  animate="show"
  className="grid grid-cols-3 gap-4"
>
  {images.map((src, i) => (
    <motion.div key={i} variants={cell} className="aspect-square rounded-2xl overflow-hidden bg-zinc-800">
      <img src={src} className="w-full h-full object-cover" />
    </motion.div>
  ))}
</motion.div>
```

stagger 70ms로 한 칸씩 등장. 6-9칸 그리드에 잘 어울림.

## 11. Noise/grain texture (정적인 깊이감)

```jsx
<div
  className="absolute inset-0 opacity-[0.04] pointer-events-none -z-10 mix-blend-screen"
  style={{
    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`
  }}
/>
```

미세한 노이즈 텍스처. blur 배경과 함께 쓰면 깊이감 큼.

## 12. 종합 — 풀 히어로 예시

여러 패턴을 결합한 templated 히어로:

```jsx
function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col justify-center px-8 lg:px-16 overflow-hidden">
      {/* 1. 배경 blob */}
      <GradientBlob />

      {/* 2. Eyebrow */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="text-sm text-zinc-400 mb-6 tracking-wider uppercase"
      >
        New · v2.0 out now
      </motion.div>

      {/* 3. Title (split words) */}
      <h1 className="text-7xl lg:text-9xl font-display tracking-tight leading-[1.05] mb-8">
        <SplitWords text="Design that" delay={0.1} />
        <br />
        <SplitWords text="moves with you." delay={0.4} />
      </h1>

      {/* 4. Subtitle */}
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 1.0 }}
        className="text-xl text-zinc-400 max-w-xl mb-12"
      >
        A motion library that gets out of your way.
      </motion.p>

      {/* 5. CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 1.2 }}
        className="flex gap-3"
      >
        <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} className="px-7 py-3.5 rounded-full bg-white text-black font-medium">
          Get started
        </motion.button>
        <motion.button whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }} className="px-7 py-3.5 rounded-full border border-zinc-700 font-medium">
          Watch demo
        </motion.button>
      </motion.div>
    </section>
  );
}
```

이 구조를 변형해서 거의 모든 히어로에 적용 가능.

## 안티패턴

- 히어로 진입 애니메이션이 3초 이상 — 사용자가 답답해 함
- 모든 단어가 통통 튀어옴 (spring with bounce) — 과함. exit-style ease가 점잖음.
- 배경 비디오 자동재생 무음 빠뜨림 — 모바일 안 됨
- text-shadow 깊은 그림자 — 90년대 느낌. 깔끔한 단색이 모던.
- 동시에 모든 게 페이드인 — stagger를 항상 줄 것
- gradient blob 너무 채도 높음 — 채도 살짝 낮춰서 (`from-purple-500/40` 정도)
- noise texture opacity가 0.1 이상 — TV 화면 됨. 0.04 정도.
