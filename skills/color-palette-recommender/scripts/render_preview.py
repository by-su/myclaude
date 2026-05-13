#!/usr/bin/env python3
"""Render a side-by-side HTML preview of color palettes.

Input: a JSON file with the shape described in SKILL.md (#palettes-json-schema).
Output: a standalone HTML file (no external dependencies).

Usage:
    python3 render_preview.py --input palettes.json --output palette-preview.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------- WCAG helpers ----------

def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected 6-digit hex, got: {hex_color!r}")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * _srgb_to_linear(r)
        + 0.7152 * _srgb_to_linear(g)
        + 0.0722 * _srgb_to_linear(b)
    )


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG contrast ratio between two hex colors. Range: 1.0 ~ 21.0."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _adjust_lightness(hex_color: str, delta: float) -> str:
    """Adjust hex color's lightness by ±delta (in HSL space). Returns new #RRGGBB."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    L = (mx + mn) / 2
    if mx == mn:
        H = 0.0
        S = 0.0
    else:
        d = mx - mn
        S = d / (2 - mx - mn) if L > 0.5 else d / (mx + mn)
        if mx == r:
            H = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            H = (b - r) / d + 2
        else:
            H = (r - g) / d + 4
        H /= 6
    new_L = max(0.0, min(1.0, L + delta))

    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1 / 6: return p + (q - p) * 6 * t
        if t < 1 / 2: return q
        if t < 2 / 3: return p + (q - p) * (2 / 3 - t) * 6
        return p

    if S == 0:
        nr = ng = nb = new_L
    else:
        q = new_L * (1 + S) if new_L < 0.5 else new_L + S - new_L * S
        p = 2 * new_L - q
        nr = hue_to_rgb(p, q, H + 1 / 3)
        ng = hue_to_rgb(p, q, H)
        nb = hue_to_rgb(p, q, H - 1 / 3)
    return "#{:02X}{:02X}{:02X}".format(int(nr * 255), int(ng * 255), int(nb * 255))


def derive_surface(bg_hex: str) -> str:
    """Return an elevated-surface tone slightly above bg (dark mode lift)
    or slightly below (light mode press)."""
    lum = _relative_luminance(bg_hex)
    if lum < 0.5:
        return _adjust_lightness(bg_hex, +0.05)
    return _adjust_lightness(bg_hex, -0.04)


def wcag_label(ratio: float) -> tuple[str, str]:
    """Return (label, css_class) for a contrast ratio."""
    if ratio >= 7:
        return (f"{ratio:.1f}:1 AAA", "pass")
    if ratio >= 4.5:
        return (f"{ratio:.1f}:1 AA", "pass")
    if ratio >= 3:
        return (f"{ratio:.1f}:1 LargeOnly", "warn")
    return (f"{ratio:.1f}:1 Fail", "fail")


# ---------- HTML rendering ----------

_PALETTE_CARD = """
<article class="palette" style="--p-primary:{primary};--p-secondary:{secondary};--p-accent:{accent};--p-bg:{bg};--p-text:{text};--p-surface:{surface};--shell-fade:{shell_fade};">
  <header class="palette-head">
    <h2>{idx}. {name}</h2>
    <p class="tagline">{tagline}</p>
  </header>

  <dl class="meta">
    <div><dt>무드</dt><dd>{mood}</dd></div>
    <div><dt>타깃 핏</dt><dd>{target_fit}</dd></div>
    <div><dt>근거</dt><dd>{rationale}</dd></div>
  </dl>

  <ul class="swatches">
    {swatches}
  </ul>

  <section class="sample">
    {sample_card}
  </section>

  <section class="contrast">
    <h4>대비비 (Text → Background)</h4>
    <span class="badge badge-{contrast_class}">{contrast_label}</span>
  </section>

  <details class="snippet">
    <summary>Tailwind / CSS 변수</summary>
    <pre><code>{css_snippet}</code></pre>
  </details>
</article>
"""


_SWATCH = """
<li class="swatch">
  <div class="chip" style="background:{hex_};{extra_style}"></div>
  <div class="chip-meta">
    <div class="chip-role">{role}</div>
    <div class="chip-name">{name}</div>
    <code class="chip-hex">{hex_upper}</code>
    <div class="chip-usage">{usage}</div>
  </div>
</li>
"""


_HTML = """<!doctype html>
<html lang="ko" data-shell="{shell_mode}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{service} · 컬러 팔레트 추천</title>
<style>
  :root[data-shell="light"] {{
    --shell-bg: #F6F6F8;
    --shell-fg: #1A1A1D;
    --shell-muted: #6B6B72;
    --shell-card: #FFFFFF;
    --shell-border: #E6E6EA;
    --signal-up: #F04452;
    --signal-down: #2E7CF6;
  }}
  :root[data-shell="dark"] {{
    --shell-bg: #0B0C10;
    --shell-fg: #ECEDEE;
    --shell-muted: #9CA3AF;
    --shell-card: #14161B;
    --shell-border: #232730;
    --signal-up: #F04452;
    --signal-down: #2E7CF6;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Inter", "Segoe UI", system-ui, sans-serif;
    background: var(--shell-bg);
    color: var(--shell-fg);
    line-height: 1.55;
    padding: 48px 24px 96px;
  }}
  .page {{
    max-width: 1280px;
    margin: 0 auto;
  }}
  .page-head {{
    margin-bottom: 32px;
  }}
  .page-head h1 {{
    margin: 0 0 8px;
    font-size: 28px;
    letter-spacing: -0.01em;
  }}
  .page-head p {{
    margin: 0;
    color: var(--shell-muted);
    font-size: 14px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
    gap: 24px;
  }}
  .palette {{
    background: var(--shell-card);
    border: 1px solid var(--shell-border);
    border-radius: 16px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}
  .palette-head h2 {{
    margin: 0 0 4px;
    font-size: 20px;
    letter-spacing: -0.01em;
  }}
  .palette-head .tagline {{
    margin: 0;
    color: var(--shell-muted);
    font-size: 13px;
  }}
  .meta {{
    margin: 0;
    display: grid;
    gap: 10px;
    font-size: 13px;
  }}
  .meta div {{ display: grid; grid-template-columns: 64px 1fr; gap: 12px; }}
  .meta dt {{ color: var(--shell-muted); margin: 0; }}
  .meta dd {{ margin: 0; }}
  .swatches {{ margin: 0; padding: 0; list-style: none; display: grid; gap: 10px; }}
  .swatch {{
    display: grid;
    grid-template-columns: 56px 1fr;
    gap: 12px;
    align-items: center;
  }}
  .chip {{
    width: 56px; height: 56px;
    border-radius: 10px;
    border: 1px solid rgba(0,0,0,0.06);
  }}
  .chip-meta {{ display: grid; gap: 2px; font-size: 12px; }}
  .chip-role {{ font-weight: 600; }}
  .chip-name {{ color: var(--shell-muted); }}
  .chip-hex {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 11px; }}
  .chip-usage {{ color: var(--shell-muted); font-size: 11px; }}

  .sample {{ border-radius: 12px; padding: 0; }}
  .sample-card {{
    position: relative;
    background: var(--p-bg);
    color: var(--p-text);
    border-radius: 14px;
    padding: 22px 22px 20px;
    border: 1px solid rgba(0,0,0,0.05);
    min-height: 220px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .sample-pill {{
    display: inline-block;
    align-self: flex-start;
    background: var(--p-primary);
    color: var(--p-bg);
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 999px;
    margin-bottom: 4px;
  }}
  .sample-card h3 {{ margin: 0; font-size: 13px; opacity: 0.7; font-weight: 500; }}
  .sample-amount {{ margin: 2px 0 0; font-size: 28px; font-weight: 700; letter-spacing: -0.01em; }}
  .sample-sub {{ margin: 0; font-size: 12px; color: var(--p-secondary); }}
  .sample-actions {{ margin-top: auto; display: flex; gap: 8px; }}
  .btn-primary {{
    background: var(--p-primary);
    color: var(--p-bg);
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    flex: 1;
  }}
  .btn-secondary {{
    background: transparent;
    color: var(--p-text);
    border: 1px solid var(--p-secondary);
    padding: 9px 16px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    flex: 1;
  }}
  .btn-danger {{
    background: var(--p-accent);
    color: var(--p-bg);
    border: none;
    padding: 10px 16px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    flex: 1;
  }}
  .sample-badge {{
    position: absolute;
    top: 18px; right: 18px;
    background: var(--p-accent);
    color: var(--p-bg);
    font-size: 10px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
    letter-spacing: 0.08em;
  }}
  .ticker-row {{ display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }}
  .ticker-symbol {{ font-size: 11px; opacity: 0.6; font-weight: 600; letter-spacing: 0.06em; }}
  .ticker-change {{ font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .ticker-change.up {{ color: var(--signal-up); }}
  .ticker-change.down {{ color: var(--signal-down); }}
  .crypto-card .mini-chart {{ margin-top: 10px; }}
  .orderbook {{
    margin-top: 12px;
    background: var(--p-surface);
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    color: var(--p-text);
  }}
  .ob-row {{ display: flex; justify-content: space-between; padding: 2px 0; }}
  .ob-row.sell .ob-px {{ color: var(--signal-down); }}
  .ob-row.buy  .ob-px {{ color: var(--signal-up); }}
  .ob-amt {{ opacity: 0.65; }}
  .ob-spread {{
    text-align: center;
    padding: 4px 0;
    margin: 2px -10px;
    font-size: 10px;
    opacity: 0.55;
    border-top: 1px solid var(--shell-fade);
    border-bottom: 1px solid var(--shell-fade);
  }}
  .btn-up {{
    background: var(--signal-up); color: #fff; border: none; padding: 10px 16px;
    border-radius: 10px; font-size: 13px; font-weight: 700; cursor: pointer; flex: 1;
  }}
  .btn-down {{
    background: var(--signal-down); color: #fff; border: none; padding: 10px 16px;
    border-radius: 10px; font-size: 13px; font-weight: 700; cursor: pointer; flex: 1;
  }}
  .mini-chart {{ width: 100%; height: 36px; margin: 4px 0 8px; }}
  .session-time {{ font-size: 11px; opacity: 0.6; }}
  .session-title {{ margin: 4px 0 2px; font-size: 18px; font-weight: 700; letter-spacing: -0.01em; }}
  .session-meta {{ display: flex; gap: 8px; font-size: 11px; opacity: 0.65; }}
  .session-meta span::before {{ content: "·"; margin-right: 6px; opacity: 0.5; }}
  .session-meta span:first-child::before {{ content: none; margin: 0; }}
  .menu-item {{ display: flex; justify-content: space-between; font-size: 12px; padding: 5px 0; border-bottom: 1px dashed rgba(0,0,0,0.08); }}
  .menu-item:last-child {{ border-bottom: none; }}
  .menu-item .price {{ opacity: 0.7; font-variant-numeric: tabular-nums; }}
  .metric-label {{ font-size: 12px; opacity: 0.6; }}
  .metric-value {{ font-size: 24px; font-weight: 700; letter-spacing: -0.01em; margin: 2px 0 0; }}
  .product-img {{ width: 100%; height: 70px; border-radius: 8px; background: linear-gradient(135deg, var(--p-secondary), var(--p-primary)); opacity: 0.4; margin-bottom: 6px; }}

  .contrast h4 {{ margin: 0 0 8px; font-size: 12px; color: var(--shell-muted); font-weight: 500; }}
  .badge {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-weight: 600;
  }}
  .badge-pass {{ background: #E5F6EA; color: #137333; }}
  .badge-warn {{ background: #FEF3C7; color: #92400E; }}
  .badge-fail {{ background: #FDE2E2; color: #B42318; }}

  .snippet summary {{
    cursor: pointer;
    font-size: 12px;
    color: var(--shell-muted);
    margin-bottom: 8px;
  }}
  .snippet pre {{
    margin: 0;
    background: #0F1115;
    color: #E6E8EE;
    padding: 12px 14px;
    border-radius: 10px;
    font-size: 11px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    overflow-x: auto;
  }}
</style>
</head>
<body>
<div class="page">
  <header class="page-head">
    <h1>🎨 컬러 팔레트 추천 — {service}</h1>
    <p>{context}</p>
  </header>
  <main class="grid">
    {cards}
  </main>
</div>
</body>
</html>
"""


# ---------- Builders ----------

def _color_by_role(colors: list[dict], role: str) -> dict | None:
    for c in colors:
        if c.get("role", "").lower() == role.lower():
            return c
    return None


def _css_snippet(palette: dict) -> str:
    role_to_var = {
        "Primary": "--color-primary",
        "Secondary": "--color-secondary",
        "Accent": "--color-accent",
        "Background": "--color-bg",
        "Text": "--color-text",
    }
    lines = []
    for role, var in role_to_var.items():
        c = _color_by_role(palette["colors"], role)
        if c:
            lines.append(f"{var}: {c['hex'].upper()};")
    return "\n".join(lines)


def _render_swatches(palette: dict) -> str:
    pieces = []
    bg = _color_by_role(palette["colors"], "Background")
    bg_hex = bg["hex"] if bg else "#FFFFFF"
    for c in palette["colors"]:
        # for the Text swatch, paint a thin border so very-dark chips don't disappear
        extra = ""
        if c["role"].lower() == "text":
            extra = "border:1px solid rgba(0,0,0,0.12);"
        pieces.append(_SWATCH.format(
            hex_=c["hex"],
            extra_style=extra,
            role=c["role"],
            name=c.get("name", ""),
            hex_upper=c["hex"].upper(),
            usage=c.get("usage", ""),
        ))
    return "\n".join(pieces)


_SAMPLE_TEMPLATES = {
    "crypto": """<div class="sample-card crypto-card">
  <div class="ticker-row">
    <div>
      <div class="ticker-symbol">BTC / KRW</div>
      <p class="sample-amount" style="margin-top:2px;">₩ 87,420,000</p>
    </div>
    <div style="text-align:right;">
      <div class="ticker-change up">▲ 2,140,000</div>
      <div class="ticker-change up" style="font-size:11px;opacity:0.85;">+2.43%</div>
    </div>
  </div>
  <svg class="mini-chart" viewBox="0 0 200 44" preserveAspectRatio="none" style="height:44px;">
    <defs>
      <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="var(--signal-up)" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="var(--signal-up)" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path d="M0,34 L20,30 L40,32 L60,22 L80,24 L100,16 L120,18 L140,10 L160,14 L180,6 L200,8 L200,44 L0,44 Z" fill="url(#chartFill)"/>
    <polyline fill="none" stroke="var(--signal-up)" stroke-width="2"
      points="0,34 20,30 40,32 60,22 80,24 100,16 120,18 140,10 160,14 180,6 200,8"/>
  </svg>
  <div class="orderbook">
    <div class="ob-row sell"><span class="ob-px">87,460,000</span><span class="ob-amt">0.1284</span></div>
    <div class="ob-row sell"><span class="ob-px">87,440,000</span><span class="ob-amt">0.5731</span></div>
    <div class="ob-spread">스프레드 20,000</div>
    <div class="ob-row buy"><span class="ob-px">87,420,000</span><span class="ob-amt">0.8120</span></div>
    <div class="ob-row buy"><span class="ob-px">87,400,000</span><span class="ob-amt">0.3492</span></div>
  </div>
  <div class="sample-actions">
    <button class="btn-up">매수</button>
    <button class="btn-down">매도</button>
  </div>
</div>""",
    "fintech": """<div class="sample-card">
  <div class="sample-pill">내 자산</div>
  <h3>총 보유 자산</h3>
  <p class="sample-amount">₩ 12,480,000</p>
  <p class="sample-sub">전월 대비 +3.2%</p>
  <div class="sample-actions">
    <button class="btn-primary">송금하기</button>
    <button class="btn-secondary">자세히</button>
  </div>
  <span class="sample-badge">NEW</span>
</div>""",
    "meditation": """<div class="sample-card">
  <div class="sample-pill">오늘의 명상</div>
  <p class="session-time">5분 · 호흡</p>
  <h2 class="session-title">출근길 마음 가다듬기</h2>
  <div class="session-meta"><span>레벨 1</span><span>3,128명 함께</span></div>
  <p class="sample-sub" style="margin-top:10px;opacity:0.7;">"지금 이 순간에 머무르세요"</p>
  <div class="sample-actions">
    <button class="btn-primary">▶ 시작하기</button>
    <button class="btn-secondary">나중에</button>
  </div>
</div>""",
    "fnb": """<div class="sample-card">
  <div class="sample-pill">오늘의 도시락</div>
  <h2 class="session-title" style="font-size:16px;">정갈한 한식 한 상</h2>
  <div class="menu-item"><span>제육볶음 · 잡곡밥</span><span class="price">+ 메인</span></div>
  <div class="menu-item"><span>시금치나물 · 콩나물</span><span class="price">+ 반찬 3종</span></div>
  <div class="menu-item"><span>된장국</span><span class="price">+ 국물</span></div>
  <p class="sample-amount" style="font-size:18px;margin-top:6px;">₩ 8,900</p>
  <div class="sample-actions">
    <button class="btn-primary">주문하기</button>
    <button class="btn-secondary">장바구니</button>
  </div>
</div>""",
    "saas": """<div class="sample-card">
  <div class="sample-pill">이번 주 활성 사용자</div>
  <p class="metric-label">지난 7일</p>
  <p class="metric-value">8,247명</p>
  <p class="sample-sub">전주 대비 +12.4%</p>
  <svg class="mini-chart" viewBox="0 0 200 36" preserveAspectRatio="none">
    <polyline fill="none" stroke="var(--p-primary)" stroke-width="2"
      points="0,30 25,26 50,28 75,20 100,22 125,16 150,18 175,10 200,6" />
  </svg>
  <div class="sample-actions">
    <button class="btn-primary">대시보드 열기</button>
    <button class="btn-secondary">리포트</button>
  </div>
</div>""",
    "edu": """<div class="sample-card">
  <div class="sample-pill">진행 중인 강의</div>
  <h2 class="session-title" style="font-size:17px;">자료구조와 알고리즘</h2>
  <p class="sample-sub">Chapter 5. 그래프 탐색</p>
  <div style="height:6px;background:rgba(0,0,0,0.08);border-radius:3px;margin:8px 0 4px;">
    <div style="height:100%;width:62%;background:var(--p-primary);border-radius:3px;"></div>
  </div>
  <p class="sample-sub">62% 완료 · 다음 강의 8분</p>
  <div class="sample-actions">
    <button class="btn-primary">이어 학습</button>
    <button class="btn-secondary">노트</button>
  </div>
</div>""",
    "ecommerce": """<div class="sample-card">
  <div class="product-img"></div>
  <h2 class="session-title" style="font-size:15px;">에코백 · 미디엄 사이즈</h2>
  <p class="sample-sub">자연 면 100% · 캔버스</p>
  <p class="sample-amount" style="font-size:20px;">₩ 28,000</p>
  <div class="sample-actions">
    <button class="btn-primary">구매하기</button>
    <button class="btn-secondary">♡ 찜</button>
  </div>
  <span class="sample-badge">BEST</span>
</div>""",
    "generic": """<div class="sample-card">
  <div class="sample-pill">미리보기</div>
  <h2 class="session-title">{service_title}</h2>
  <p class="sample-sub">버튼·배경·텍스트가 함께 어떻게 보이는지 확인하세요.</p>
  <p class="sample-sub" style="margin-top:12px;">본문 텍스트 예시입니다. 가독성과 위계, 톤이 자연스러운지 살펴보세요.</p>
  <div class="sample-actions">
    <button class="btn-primary">{cta_label}</button>
    <button class="btn-secondary">자세히</button>
  </div>
  <span class="sample-badge">NEW</span>
</div>""",
}


def _infer_sample_type(service: str, context: str) -> str:
    hint = (service + " " + context).lower()
    # crypto comes before generic fintech so the gold/ticker reading wins
    if any(k in hint for k in ["가상자산", "코인", "크립토", "비트코인", "거래소", "crypto", "bitcoin", "exchange", "web3", "nft"]):
        return "crypto"
    if any(k in hint for k in ["명상", "마음챙김", "meditation", "mindful", "수면", "휴식", "웰니스", "wellness"]):
        return "meditation"
    if any(k in hint for k in ["배달", "도시락", "푸드", "음식", "맛집", "주문", "food", "delivery", "restaurant", "f&b", "fnb"]):
        return "fnb"
    if any(k in hint for k in ["대시보드", "saas", "협업", "워크스페이스", "생산성", "dashboard", "analytics", "b2b", "내부 툴"]):
        return "saas"
    if any(k in hint for k in ["강의", "학습", "교육", "edtech", "코딩 교육", "수업", "lesson", "course"]):
        return "edu"
    if any(k in hint for k in ["커머스", "쇼핑", "이커머스", "마켓", "스토어", "shopping", "ecommerce", "shop"]):
        return "ecommerce"
    if any(k in hint for k in ["핀테크", "은행", "투자", "자산", "금융", "결제", "송금", "fintech", "bank", "wallet"]):
        return "fintech"
    return "generic"


def _cta_label(domain_hint: str) -> str:
    hint = (domain_hint or "").lower()
    if any(k in hint for k in ["핀테크", "은행", "투자", "자산", "금융"]):
        return "송금하기"
    if any(k in hint for k in ["헬스", "명상", "운동", "건강"]):
        return "시작하기"
    if any(k in hint for k in ["커머스", "쇼핑", "이커머스", "마켓"]):
        return "구매하기"
    if any(k in hint for k in ["배달", "푸드", "음식", "맛집"]):
        return "주문하기"
    return "시작하기"


def _build_sample_card(sample_type: str, service: str, cta_label: str) -> str:
    tmpl = _SAMPLE_TEMPLATES.get(sample_type) or _SAMPLE_TEMPLATES["generic"]
    if sample_type == "generic":
        return tmpl.format(service_title=(service or "내 서비스"), cta_label=cta_label)
    return tmpl


def render(data: dict) -> str:
    palettes = data.get("palettes", [])
    if len(palettes) == 0:
        raise ValueError("palettes 배열이 비어 있습니다.")
    service = data.get("service", "서비스")
    context = data.get("context", "")
    sample_type = data.get("sample_type") or _infer_sample_type(service, context)
    cta = _cta_label(service + " " + context)
    sample_card_html = _build_sample_card(sample_type, service, cta)

    cards = []
    for idx, p in enumerate(palettes, start=1):
        bg = _color_by_role(p["colors"], "Background")
        text = _color_by_role(p["colors"], "Text")
        if not bg or not text:
            raise ValueError(
                f"팔레트 '{p.get('name', '?')}'에 Background 또는 Text 역할이 없습니다."
            )
        primary = _color_by_role(p["colors"], "Primary") or bg
        secondary = _color_by_role(p["colors"], "Secondary") or text
        accent = _color_by_role(p["colors"], "Accent") or primary

        ratio = contrast_ratio(text["hex"], bg["hex"])
        label, css_class = wcag_label(ratio)

        bg_lum = _relative_luminance(bg["hex"])
        is_dark_bg = bg_lum < 0.2
        shell_fade = "rgba(255,255,255,0.08)" if is_dark_bg else "rgba(0,0,0,0.08)"
        surface = derive_surface(bg["hex"])

        cards.append(_PALETTE_CARD.format(
            idx=idx,
            name=p.get("name", f"Palette {idx}"),
            tagline=p.get("tagline", ""),
            mood=p.get("mood", ""),
            target_fit=p.get("target_fit", ""),
            rationale=p.get("rationale", ""),
            swatches=_render_swatches(p),
            primary=primary["hex"],
            secondary=secondary["hex"],
            accent=accent["hex"],
            bg=bg["hex"],
            text=text["hex"],
            surface=surface,
            shell_fade=shell_fade,
            sample_card=sample_card_html,
            contrast_class=css_class,
            contrast_label=label,
            css_snippet=_css_snippet(p),
        ))

    # Determine shell mode: dark if all palette BGs are dark
    all_dark = all(_relative_luminance(_color_by_role(p["colors"], "Background")["hex"]) < 0.2 for p in palettes)
    shell_mode = "dark" if all_dark else "light"

    return _HTML.format(
        service=service,
        context=context,
        shell_mode=shell_mode,
        cards="\n".join(cards),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Render palette preview HTML")
    ap.add_argument("--input", required=True, help="palettes.json path")
    ap.add_argument("--output", required=True, help="output html path")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    html = render(data)
    Path(args.output).write_text(html, encoding="utf-8")
    # also print a small validation report
    palettes = data.get("palettes", [])
    print(f"✓ Generated {args.output} with {len(palettes)} palette(s).")
    for p in palettes:
        bg = _color_by_role(p["colors"], "Background")
        text = _color_by_role(p["colors"], "Text")
        if bg and text:
            r = contrast_ratio(text["hex"], bg["hex"])
            label, _ = wcag_label(r)
            print(f"  · {p.get('name', '?')}: Text/Background contrast = {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
