# 마이크로 인터랙션 레시피

작고 자주 마주치는 UI에 "잘 만들어졌다"는 인상을 주는 인터랙션. 라이브러리는 Framer Motion 위주, Tailwind/CSS만으로 충분한 것도 표시.

## 0. 핵심 원칙

마이크로 인터랙션의 시간은 짧다 (150-300ms). 시각적 변화는 명확하되 과하지 않게. spring을 쓸 때는 `stiffness: 400, damping: 17` 같은 빠른 응답이 잘 어울린다.

---

## 버튼

### 1. 기본 호버 + 탭 (모든 버튼의 default)

```jsx
<motion.button
  whileHover={{ scale: 1.04 }}
  whileTap={{ scale: 0.96 }}
  transition={{ type: "spring", stiffness: 400, damping: 17 }}
  className="px-6 py-3 rounded-full bg-white text-black font-medium"
>
  Click me
</motion.button>
```

scale 변화량 1.03-1.06이 적당. 너무 크면 부담스럽고, 너무 작으면 변화가 안 느껴진다.

### 2. Magnetic button — 마우스 따라 살짝 끌림

```jsx
function MagneticButton({ children, strength = 0.3 }) {
  const ref = useRef(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 300, damping: 25 });
  const sy = useSpring(y, { stiffness: 300, damping: 25 });

  const onMove = (e) => {
    const r = ref.current.getBoundingClientRect();
    x.set((e.clientX - r.left - r.width / 2) * strength);
    y.set((e.clientY - r.top - r.height / 2) * strength);
  };
  const onLeave = () => { x.set(0); y.set(0); };

  return (
    <motion.button
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{ x: sx, y: sy }}
      whileTap={{ scale: 0.95 }}
      className="px-8 py-4 rounded-full bg-white text-black font-medium"
    >
      {children}
    </motion.button>
  );
}
```

`strength`를 0.2-0.4로 두면 자연스럽다. 텍스트도 같이 끌리고 싶으면 내부에 `<motion.span style={{ x: sx2, y: sy2 }}>`로 더 약한 strength로 한 번 더 적용.

### 3. Click ripple

```jsx
function RippleButton({ children, ...props }) {
  const [ripples, setRipples] = useState([]);
  const onClick = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const id = Date.now();
    setRipples(rs => [...rs, { id, x: e.clientX - r.left, y: e.clientY - r.top }]);
    setTimeout(() => setRipples(rs => rs.filter(r => r.id !== id)), 700);
  };
  return (
    <button {...props} onClick={onClick} className="relative overflow-hidden px-6 py-3 rounded-full bg-zinc-800">
      {children}
      <AnimatePresence>
        {ripples.map(r => (
          <motion.span
            key={r.id}
            initial={{ scale: 0, opacity: 0.4 }}
            animate={{ scale: 8, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            style={{ left: r.x, top: r.y }}
            className="absolute -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-white pointer-events-none"
          />
        ))}
      </AnimatePresence>
    </button>
  );
}
```

Material 풍 클릭 피드백.

### 4. Loading state 토글

```jsx
<motion.button
  layout
  disabled={loading}
  transition={{ type: "spring", stiffness: 300, damping: 30 }}
  className="px-6 py-3 rounded-full bg-white text-black font-medium overflow-hidden"
>
  <AnimatePresence mode="wait" initial={false}>
    {loading ? (
      <motion.span key="spinner" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
        <Spinner />
      </motion.span>
    ) : (
      <motion.span key="label" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
        Submit
      </motion.span>
    )}
  </AnimatePresence>
</motion.button>
```

`layout`이 핵심 — width가 부드럽게 줄어듬.

---

## 폼

### 5. Floating label input

```jsx
function FloatingInput({ label, ...props }) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const active = focused || value.length > 0;
  return (
    <div className="relative">
      <input
        {...props}
        value={value}
        onChange={e => setValue(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="w-full px-4 pt-6 pb-2 bg-zinc-900 border border-zinc-800 rounded-lg text-white focus:border-white outline-none transition-colors"
      />
      <motion.label
        animate={{
          y: active ? -10 : 0,
          scale: active ? 0.8 : 1,
          color: focused ? "#fff" : "#71717a"
        }}
        transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
        style={{ originX: 0 }}
        className="absolute left-4 top-4 pointer-events-none text-zinc-500"
      >
        {label}
      </motion.label>
    </div>
  );
}
```

### 6. Form success checkmark

```jsx
<motion.svg viewBox="0 0 24 24" className="w-12 h-12">
  <motion.circle
    cx="12" cy="12" r="11"
    fill="none" stroke="currentColor" strokeWidth="2"
    initial={{ pathLength: 0 }}
    animate={{ pathLength: 1 }}
    transition={{ duration: 0.6, ease: "easeOut" }}
  />
  <motion.path
    d="M7 12l3 3 7-7"
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    initial={{ pathLength: 0 }}
    animate={{ pathLength: 1 }}
    transition={{ duration: 0.4, ease: "easeOut", delay: 0.6 }}
  />
</motion.svg>
```

`pathLength`로 SVG를 "그리는" 효과. 원 → 체크 순서로 stagger.

### 7. Inline validation shake

```jsx
<motion.div
  animate={error ? { x: [0, -8, 8, -6, 6, 0] } : {}}
  transition={{ duration: 0.4 }}
>
  <input className={error ? "border-red-500" : ""} />
</motion.div>
```

키프레임 배열로 흔들기.

---

## 토글 / 스위치

### 8. iOS-style toggle

```jsx
function Toggle({ on, onChange }) {
  return (
    <button
      onClick={() => onChange(!on)}
      className={`w-14 h-8 rounded-full p-1 transition-colors ${on ? "bg-emerald-500" : "bg-zinc-700"}`}
    >
      <motion.div
        layout
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        className={`w-6 h-6 bg-white rounded-full ${on ? "ml-auto" : ""}`}
      />
    </button>
  );
}
```

`layout` + ml-auto 트릭으로 부드러운 슬라이드.

---

## 카드 hover

### 9. Lift on hover

```jsx
<motion.div
  whileHover={{ y: -4, boxShadow: "0 20px 40px -10px rgba(0,0,0,0.4)" }}
  transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
  className="bg-zinc-900 rounded-2xl p-6"
/>
```

y -2px ~ -6px가 적당. 그림자도 같이 키워야 "떠오른" 느낌이 산다.

### 10. 3D tilt — 마우스 따라 기울기

```jsx
function TiltCard({ children }) {
  const ref = useRef(null);
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const srx = useSpring(rx, { stiffness: 300, damping: 30 });
  const sry = useSpring(ry, { stiffness: 300, damping: 30 });

  const onMove = (e) => {
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    ry.set((px - 0.5) * 20);
    rx.set((py - 0.5) * -20);
  };
  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={() => { rx.set(0); ry.set(0); }}
      style={{ rotateX: srx, rotateY: sry, transformPerspective: 1000 }}
      className="w-72 h-96 rounded-2xl bg-gradient-to-br from-zinc-800 to-zinc-900 p-6"
    >
      {children}
    </motion.div>
  );
}
```

`transformPerspective: 1000`을 같이 주는 게 핵심 — 없으면 평평한 회전.

---

## 아이콘 모핑

### 11. 햄버거 ↔ X (CSS만)

```jsx
<button
  onClick={() => setOpen(o => !o)}
  className="relative w-8 h-8"
>
  <span className={`absolute left-1 right-1 h-0.5 bg-white transition-all duration-300 ${open ? "top-4 rotate-45" : "top-2.5"}`} />
  <span className={`absolute left-1 right-1 h-0.5 bg-white transition-opacity duration-200 top-4 ${open ? "opacity-0" : "opacity-100"}`} />
  <span className={`absolute left-1 right-1 h-0.5 bg-white transition-all duration-300 ${open ? "top-4 -rotate-45" : "top-5.5"}`} />
</button>
```

라이브러리 없이 깔끔.

### 12. Copy → Check 트랜지션

```jsx
<motion.button onClick={copy} className="relative w-9 h-9">
  <AnimatePresence mode="wait" initial={false}>
    {copied ? (
      <motion.span key="check"
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.5, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="absolute inset-0 grid place-items-center text-emerald-400"
      ><CheckIcon /></motion.span>
    ) : (
      <motion.span key="copy"
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.5, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="absolute inset-0 grid place-items-center"
      ><CopyIcon /></motion.span>
    )}
  </AnimatePresence>
</motion.button>
```

---

## 숫자 카운터

### 13. Animated counter

```jsx
function Counter({ to, duration = 1.5 }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, v => Math.round(v));
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const controls = animate(count, to, {
      duration,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: v => setDisplay(Math.round(v))
    });
    return () => controls.stop();
  }, [to]);

  return <span>{display.toLocaleString()}</span>;
}
```

`animate(motionValue, target, ...)`로 직접 트윈. 큰 숫자 reveal에 좋다.

---

## 안티패턴

- hover에 `transition-all` — 명시적으로 `transition-transform`, `transition-colors`로
- 버튼 호버 스케일이 1.1 이상 — 부담스러움
- 모든 카드에 ripple — 과함. 1개 액션 버튼에만.
- toggle에 spring을 안 쓰고 linear — 어색함
- 로딩 스피너에 `width` 변화 — `scale`로
