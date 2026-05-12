# 복잡한 UI 모션 레시피

drag, layoutId, gesture, multi-step interaction. 보통 Framer Motion이 압도적으로 강하다.

## 1. Drag to reorder (Reorder API)

```jsx
import {Reorder} from "skills/motion-lab/references/framer-motion";

function ReorderList() {
    const [items, setItems] = useState(["Drinks", "Snacks", "Mains", "Desserts"]);
    return (
        <Reorder.Group axis="y" values={items} onReorder={setItems} className="space-y-2">
            {items.map(item => (
                <Reorder.Item
                    key={item}
                    value={item}
                    whileDrag={{scale: 1.03, boxShadow: "0 20px 40px -10px rgba(0,0,0,0.5)"}}
                    transition={{duration: 0.3}}
                    className="bg-zinc-800 rounded-xl p-4 cursor-grab active:cursor-grabbing select-none"
                >
                    {item}
                </Reorder.Item>
            ))}
        </Reorder.Group>
    );
}
```

`Reorder.Group` + `Reorder.Item`만 쓰면 알아서 layout 애니메이션. 핸들이 따로 필요하면 `dragListener={false} dragControls={controls}`.

## 2. Shared element transition (layoutId)

작은 카드를 클릭하면 풀스크린으로 확장:

```jsx
function GalleryExpand() {
  const [selected, setSelected] = useState(null);
  const photos = [
    { id: "a", src: "...", title: "Aurora" },
    { id: "b", src: "...", title: "Boulder" },
    { id: "c", src: "...", title: "Crater" }
  ];

  return (
    <>
      <div className="grid grid-cols-3 gap-4">
        {photos.map(p => (
          <motion.button
            key={p.id}
            layoutId={`photo-${p.id}`}
            onClick={() => setSelected(p)}
            className="aspect-square rounded-2xl overflow-hidden"
          >
            <motion.img layoutId={`img-${p.id}`} src={p.src} className="w-full h-full object-cover" />
            <motion.h3 layoutId={`title-${p.id}`} className="absolute bottom-4 left-4 text-white">{p.title}</motion.h3>
          </motion.button>
        ))}
      </div>

      <AnimatePresence>
        {selected && (
          <motion.div
            className="fixed inset-0 z-50 bg-black/80 grid place-items-center p-8"
            onClick={() => setSelected(null)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              layoutId={`photo-${selected.id}`}
              className="w-full max-w-3xl rounded-3xl overflow-hidden"
            >
              <motion.img layoutId={`img-${selected.id}`} src={selected.src} className="w-full" />
              <motion.h3 layoutId={`title-${selected.id}`} className="text-3xl p-6">{selected.title}</motion.h3>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
```

핵심: `layoutId`가 같은 컴포넌트 사이에 자동 트랜지션. 부모뿐 아니라 이미지, 텍스트도 각각 layoutId를 주면 모두 부드럽게 모핑.

## 3. Tab indicator (sliding pill)

```jsx
function Tabs() {
  const [active, setActive] = useState("home");
  const tabs = ["home", "about", "work", "contact"];
  return (
    <LayoutGroup>
      <div className="inline-flex bg-zinc-900 rounded-full p-1">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setActive(t)}
            className="relative px-5 py-2 text-sm capitalize"
          >
            <span className={`relative z-10 ${active === t ? "text-black" : "text-zinc-400"}`}>{t}</span>
            {active === t && (
              <motion.span
                layoutId="tab-pill"
                className="absolute inset-0 bg-white rounded-full"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
          </button>
        ))}
      </div>
    </LayoutGroup>
  );
}
```

`layoutId="tab-pill"`로 흰 알약이 탭 사이를 자연스럽게 이동.

## 4. Card stack — drag dismiss (Tinder 스타일)

```jsx
function CardStack({ cards: initial }) {
  const [cards, setCards] = useState(initial);

  return (
    <div className="relative w-80 h-96">
      <AnimatePresence>
        {cards.slice(0, 3).map((card, i) => (
          <motion.div
            key={card.id}
            className="absolute inset-0 rounded-3xl bg-zinc-800 p-6 cursor-grab active:cursor-grabbing"
            style={{ zIndex: cards.length - i }}
            initial={{ scale: 1 - i * 0.05, y: i * 8, opacity: 1 }}
            animate={{ scale: 1 - i * 0.05, y: i * 8, opacity: 1 }}
            exit={{ x: 300, opacity: 0, rotate: 20, transition: { duration: 0.3 } }}
            drag={i === 0 ? "x" : false}
            dragConstraints={{ left: 0, right: 0 }}
            onDragEnd={(_, info) => {
              if (Math.abs(info.offset.x) > 100) {
                setCards(c => c.slice(1));
              }
            }}
          >
            <h3 className="text-2xl">{card.title}</h3>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
```

뒷 카드는 살짝 작고 아래로(`scale: 1 - i * 0.05, y: i * 8`). 첫 카드만 drag 가능. 100px 이상 드래그하면 제거 + `exit`로 날라감.

## 5. Bottom sheet — drag to close

```jsx
function BottomSheet({ open, onClose, children }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/60 z-40"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed bottom-0 inset-x-0 z-50 bg-zinc-900 rounded-t-3xl p-6 pb-12"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            drag="y"
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.5 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > 100 || info.velocity.y > 500) onClose();
            }}
          >
            <div className="w-12 h-1 bg-zinc-700 rounded-full mx-auto mb-6" />
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

위로는 못 끌고 아래로만 탄성으로 끌림. 100px 이상 또는 빠른 속도면 close. iOS-feel.

## 6. Modal with backdrop blur

```jsx
<AnimatePresence>
  {open && (
    <motion.div
      initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
      animate={{ opacity: 1, backdropFilter: "blur(8px)" }}
      exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
      transition={{ duration: 0.3 }}
      className="fixed inset-0 bg-black/40 z-50 grid place-items-center p-8"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0, y: 16 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.92, opacity: 0, y: 16 }}
        transition={{ type: "spring", stiffness: 350, damping: 28 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-zinc-900 rounded-3xl p-8 max-w-md w-full"
      >
        {children}
      </motion.div>
    </motion.div>
  )}
</AnimatePresence>
```

backdrop도 fade + blur 동시에. 내부는 spring으로 살짝 통통.

## 7. Drag to delete (스와이프)

```jsx
function SwipeItem({ children, onDelete }) {
  const x = useMotionValue(0);
  const opacity = useTransform(x, [-200, -50, 0], [0, 1, 1]);
  const deleteScale = useTransform(x, [-100, 0], [1, 0.5]);

  return (
    <motion.div
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={{ left: 0.7, right: 0 }}
      onDragEnd={(_, info) => {
        if (info.offset.x < -150) onDelete();
      }}
      style={{ x, opacity }}
      className="relative bg-zinc-800 rounded-xl p-4"
    >
      <motion.div
        style={{ scale: deleteScale }}
        className="absolute right-4 top-1/2 -translate-y-1/2 text-red-400 pointer-events-none"
      >
        Delete →
      </motion.div>
      {children}
    </motion.div>
  );
}
```

왼쪽 drag 시 delete 라벨이 나타나고 충분히 끌면 제거.

## 8. Multi-step form transition

```jsx
const variants = {
  enter: (dir) => ({ x: dir > 0 ? 300 : -300, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir) => ({ x: dir > 0 ? -300 : 300, opacity: 0 })
};

function MultiStep() {
  const [[step, dir], set] = useState([0, 0]);
  const next = () => set([step + 1, 1]);
  const prev = () => set([step - 1, -1]);

  return (
    <div className="relative h-96 overflow-hidden">
      <AnimatePresence mode="wait" custom={dir}>
        <motion.div
          key={step}
          custom={dir}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="absolute inset-0"
        >
          Step {step + 1}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
```

방향(`dir`)에 따라 진입/퇴장 방향이 바뀜. carousel/wizard 표준 패턴.

## 9. Carousel with snap

```jsx
function Carousel({ items }) {
  return (
    <div className="overflow-x-auto snap-x snap-mandatory scroll-smooth flex gap-4 -mx-8 px-8 pb-4 [&::-webkit-scrollbar]:hidden">
      {items.map((item, i) => (
        <motion.div
          key={i}
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.3 }}
          className="snap-start flex-shrink-0 w-72 h-96 rounded-3xl bg-zinc-800 p-6"
        >
          {item.content}
        </motion.div>
      ))}
    </div>
  );
}
```

CSS scroll-snap만으로 충분히 좋은 carousel. JS 불필요.

## 10. Accordion / Disclosure

```jsx
function Accordion({ items }) {
  const [open, setOpen] = useState(null);
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="border-b border-zinc-800">
          <button
            onClick={() => setOpen(open === i ? null : i)}
            className="w-full flex items-center justify-between py-4 text-left"
          >
            <span className="text-lg">{item.title}</span>
            <motion.span animate={{ rotate: open === i ? 45 : 0 }} transition={{ duration: 0.25 }}>+</motion.span>
          </button>
          <AnimatePresence initial={false}>
            {open === i && (
              <motion.div
                key="body"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden"
              >
                <p className="pb-4 text-zinc-400">{item.body}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </div>
  );
}
```

`height: "auto"` 애니메이션은 Framer Motion이 알아서 처리. `overflow-hidden` 필수. `+`가 45도 회전해 X로.

## 11. Notification stack

```jsx
function Notifications({ items }) {
  return (
    <div className="fixed bottom-4 right-4 space-y-2">
      <AnimatePresence>
        {items.map(n => (
          <motion.div
            key={n.id}
            layout
            initial={{ opacity: 0, x: 50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.9 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="bg-zinc-800 rounded-xl p-4 shadow-2xl w-72"
          >
            {n.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
```

`layout` prop으로 기존 알림들이 자리를 양보. 오른쪽에서 슬라이드인.

## 12. Floating mouse cursor (custom cursor)

```jsx
function CustomCursor() {
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const sx = useSpring(x, { stiffness: 500, damping: 40 });
  const sy = useSpring(y, { stiffness: 500, damping: 40 });
  const [hovering, setHovering] = useState(false);

  useEffect(() => {
    const onMove = (e) => { x.set(e.clientX); y.set(e.clientY); };
    const onOver = (e) => setHovering(!!e.target.closest("a, button"));
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseover", onOver);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseover", onOver);
    };
  }, []);

  return (
    <motion.div
      style={{ x: sx, y: sy, translateX: "-50%", translateY: "-50%" }}
      animate={{ scale: hovering ? 2.5 : 1 }}
      transition={{ duration: 0.2 }}
      className="fixed top-0 left-0 w-4 h-4 rounded-full bg-white mix-blend-difference pointer-events-none z-[100]"
    />
  );
}

// body에 cursor-none 추가
<body className="cursor-none">
```

`mix-blend-difference`로 배경 따라 반전. 링크/버튼에 호버 시 커집.

## 안티패턴

- `layoutId`를 같은 화면에 동시에 보이는 두 요소에 동시 적용 — 둘 사이 충돌. 하나는 mount, 하나는 unmount 상태여야 함.
- drag dismiss 임계값이 너무 낮음 (30px 이하) — 우연한 스와이프로 삭제
- modal에 `whileTap` — 클릭으로 닫을 때 스케일 변화가 거슬림
- drag constraints 없이 자유 drag — 카드가 영영 사라짐
- accordion에서 `height: "auto"` 대신 `maxHeight` 트릭 — 컨텐츠 크기 변하면 깨짐
- carousel을 JS로만 — 손가락 터치 UX 깨짐. CSS scroll-snap 우선.
- 모든 hover에 `mix-blend-difference` — 텍스트 가독성 나빠짐. 커서에만.
