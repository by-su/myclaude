#!/usr/bin/env python3
"""Render a side-by-side HTML preview of color palettes.

Input: a JSON file with the shape described in SKILL.md (#palettes-json-schema).
Output: a standalone HTML file (no external dependencies).

The renderer is forgiving about palette size: only Primary, Background, Text are
required. Secondary, Accent, Surface, Muted, Border are all optional and auto-
derived where it makes sense. For every foreground/background pair that appears
in the rendered preview, we compute the WCAG contrast ratio and show it — so
users can see at a glance whether button text, badge text, muted text, etc. are
actually readable on the chosen surfaces.

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


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    )


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    L = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, L
    d = mx - mn
    S = d / (2 - mx - mn) if L > 0.5 else d / (mx + mn)
    if mx == r:
        H = (g - b) / d + (6 if g < b else 0)
    elif mx == g:
        H = (b - r) / d + 2
    else:
        H = (r - g) / d + 4
    return H / 6, S, L


def _hsl_to_rgb(H: float, S: float, L: float) -> tuple[int, int, int]:
    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1 / 6: return p + (q - p) * 6 * t
        if t < 1 / 2: return q
        if t < 2 / 3: return p + (q - p) * (2 / 3 - t) * 6
        return p

    if S == 0:
        r = g = b = L
    else:
        q = L * (1 + S) if L < 0.5 else L + S - L * S
        p = 2 * L - q
        r = hue_to_rgb(p, q, H + 1 / 3)
        g = hue_to_rgb(p, q, H)
        b = hue_to_rgb(p, q, H - 1 / 3)
    return int(r * 255), int(g * 255), int(b * 255)


def _adjust_lightness(hex_color: str, delta: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    H, S, L = _rgb_to_hsl(r, g, b)
    return _rgb_to_hex(*_hsl_to_rgb(H, S, max(0.0, min(1.0, L + delta))))


def _mix(hex_a: str, hex_b: str, t: float) -> str:
    """Linear mix in sRGB. t=0 → all a, t=1 → all b."""
    ar, ag, ab = _hex_to_rgb(hex_a)
    br, bg, bb = _hex_to_rgb(hex_b)
    return _rgb_to_hex(
        int(ar + (br - ar) * t),
        int(ag + (bg - ag) * t),
        int(ab + (bb - ab) * t),
    )


def derive_surface(bg_hex: str) -> str:
    """Return an elevated-surface tone slightly above bg (dark mode lift)
    or slightly below (light mode press)."""
    lum = _relative_luminance(bg_hex)
    if lum < 0.5:
        return _adjust_lightness(bg_hex, +0.05)
    return _adjust_lightness(bg_hex, -0.04)


def derive_muted_text(text_hex: str, bg_hex: str) -> str:
    """Muted body text: mix text toward bg until it sits around 5:1 contrast.

    We target 5:1 (just above AA 4.5:1) so descriptions stay legible while
    feeling visibly less prominent than primary body text.
    """
    target = 5.0
    # bisect over the mix ratio
    lo, hi = 0.0, 0.9
    best = text_hex
    for _ in range(20):
        mid = (lo + hi) / 2
        candidate = _mix(text_hex, bg_hex, mid)
        if contrast_ratio(candidate, bg_hex) >= target:
            best = candidate
            lo = mid
        else:
            hi = mid
    return best


def derive_border(bg_hex: str, text_hex: str) -> str:
    """Border: low-contrast separator, mixed from text toward bg."""
    return _mix(text_hex, bg_hex, 0.82)


# ---------- Design language material defaults ----------

# 5 design languages. Each language has sensible defaults that go with its
# visual code. The model can override anything per palette via the "material"
# object; whatever it omits, we fill in from these defaults.

_DESIGN_LANGUAGES = {"flat", "glass", "soft", "bold", "cyber"}


def _language_defaults(language: str, primary_hex: str, bg_hex: str,
                       border_hex: str, surface_hex: str) -> dict:
    """Return the default material tokens for the given design language.

    Defaults are tuned against the resolved palette so that, e.g., Cyber
    glow uses the *actual* Primary, and Glass surface uses an alpha-blended
    version of the *actual* Surface. The model can override any field.
    """
    pr, pg, pb = _hex_to_rgb(primary_hex)
    sr, sg, sb = _hex_to_rgb(surface_hex)
    bg_lum = _relative_luminance(bg_hex)
    is_dark = bg_lum < 0.3

    if language == "flat":
        return {
            "surface_alpha": 1.0,
            "blur": "0px",
            "saturate": "100%",
            "border_top": border_hex,
            "border_bottom": border_hex,
            "elevation": [
                "0 1px 2px rgba(15,18,30,0.04)",
                "0 2px 8px rgba(15,18,30,0.06)",
                "0 8px 24px rgba(15,18,30,0.10)",
            ],
            "background_treatment": "solid",
            "radius": "12px",
        }

    if language == "glass":
        # Light glass = brighter surface tint (white-ish), dark glass = surface stays close to its own tone
        if is_dark:
            return {
                "surface_alpha": 0.52,
                "blur": "28px",
                "saturate": "180%",
                "border_top": "rgba(255,255,255,0.14)",
                "border_bottom": "rgba(0,0,0,0.32)",
                "elevation": [
                    "0 1px 2px rgba(0,0,0,0.30)",
                    "0 12px 40px rgba(0,0,0,0.40)",
                    "0 24px 64px rgba(0,0,0,0.50), 0 2px 6px rgba(0,0,0,0.30)",
                ],
                "background_treatment": "gradient",
                "radius": "18px",
            }
        return {
            "surface_alpha": 0.72,
            "blur": "24px",
            "saturate": "180%",
            "border_top": "rgba(255,255,255,0.45)",
            "border_bottom": "rgba(0,0,0,0.06)",
            "elevation": [
                "0 1px 2px rgba(15,18,30,0.04)",
                "0 12px 40px rgba(15,18,30,0.12)",
                "0 24px 64px rgba(15,18,30,0.18), 0 2px 6px rgba(15,18,30,0.08)",
            ],
            "background_treatment": "gradient",
            "radius": "18px",
        }

    if language == "soft":
        return {
            "surface_alpha": 1.0,
            "blur": "0px",
            "saturate": "100%",
            "border_top": "rgba(0,0,0,0.03)",
            "border_bottom": "rgba(0,0,0,0.02)",
            "elevation": [
                "0 2px 8px rgba(15,18,30,0.04)",
                "0 12px 32px rgba(15,18,30,0.06)",
                "0 24px 56px rgba(15,18,30,0.08)",
            ],
            "background_treatment": "soft-radial",
            "radius": "24px",
        }

    if language == "bold":
        return {
            "surface_alpha": 1.0,
            "blur": "0px",
            "saturate": "100%",
            "border_top": "transparent",
            "border_bottom": "transparent",
            "elevation": [
                "4px 4px 0 rgba(0,0,0,0.08)",
                "8px 8px 0 rgba(0,0,0,0.12)",
                "12px 12px 0 rgba(0,0,0,0.18)",
            ],
            "background_treatment": "color-block",
            "radius": "4px",
        }

    if language == "cyber":
        return {
            "surface_alpha": 1.0,
            "blur": "0px",
            "saturate": "100%",
            "border_top": f"rgba({pr},{pg},{pb},0.42)",
            "border_bottom": f"rgba({pr},{pg},{pb},0.18)",
            "elevation": [
                f"0 0 16px rgba({pr},{pg},{pb},0.22), 0 2px 8px rgba(0,0,0,0.30)",
                f"0 0 32px rgba({pr},{pg},{pb},0.32), 0 4px 16px rgba(0,0,0,0.40)",
                f"0 0 48px rgba({pr},{pg},{pb},0.42), 0 8px 24px rgba(0,0,0,0.50)",
            ],
            "background_treatment": "oled-vignette",
            "radius": "8px",
        }

    # Unknown language → fall back to flat
    return _language_defaults("flat", primary_hex, bg_hex, border_hex, surface_hex)


def resolve_material(palette: dict, resolved: dict) -> dict:
    """Resolve material tokens for a palette. Reads design_language and the
    optional `material` object; fills in defaults for anything the user did
    not specify.
    """
    language = (palette.get("design_language") or "flat").lower()
    if language not in _DESIGN_LANGUAGES:
        language = "flat"

    defaults = _language_defaults(
        language,
        resolved["primary"],
        resolved["background"],
        resolved["border"],
        resolved["surface"],
    )
    user = dict(palette.get("material") or {})

    # Merge: user overrides defaults
    merged = {**defaults, **{k: v for k, v in user.items() if v is not None}}
    merged["language"] = language

    # Compute the effective surface color the user *sees* — i.e. the surface
    # color alpha-blended against the background. This matters for Glass: real
    # contrast for text on a glass card is text vs this effective surface,
    # not text vs the abstract surface hex.
    alpha = float(merged.get("surface_alpha", 1.0))
    merged["effective_surface"] = _mix(resolved["background"], resolved["surface"], alpha)

    return merged


def pick_on_color(chip_hex: str, text_hex: str, bg_hex: str) -> tuple[str, float]:
    """Pick the best foreground color to place text on top of `chip_hex`.

    Tries (in order): the palette's Text, the palette's Background, pure light,
    pure dark — and returns whichever gives the best contrast. We try the
    palette's own colors first to keep the tinted feel consistent; only fall
    back to pure white/black if neither palette token reaches AA (4.5:1).
    """
    candidates = [
        ("text", text_hex),
        ("bg", bg_hex),
        ("light", "#F8F8F9"),
        ("dark", "#0E0F12"),
    ]
    # Prefer the first candidate that meets AA. If none does, return the best.
    best = candidates[0][1]
    best_ratio = contrast_ratio(best, chip_hex)
    for _, hex_ in candidates:
        r = contrast_ratio(hex_, chip_hex)
        if r >= 4.5:
            return hex_, r
        if r > best_ratio:
            best = hex_
            best_ratio = r
    return best, best_ratio


def wcag_label(ratio: float) -> tuple[str, str]:
    """Return (label, css_class) for a contrast ratio."""
    if ratio >= 7:
        return (f"{ratio:.1f}:1 AAA", "pass")
    if ratio >= 4.5:
        return (f"{ratio:.1f}:1 AA", "pass")
    if ratio >= 3:
        return (f"{ratio:.1f}:1 Large", "warn")
    return (f"{ratio:.1f}:1 Fail", "fail")


# ---------- Role resolution ----------

def _color_by_role(colors: list[dict], role: str) -> dict | None:
    for c in colors:
        if c.get("role", "").lower() == role.lower():
            return c
    return None


def resolve_palette(palette: dict) -> dict:
    """Resolve a palette's color roles, deriving anything missing.

    Returns a dict of {role_name: hex} for: primary, secondary, accent,
    surface, background, text, muted, border, on_primary, on_accent,
    on_surface. Roles that the user did not specify are derived sensibly.
    """
    colors = palette.get("colors", [])
    bg = _color_by_role(colors, "Background")
    text = _color_by_role(colors, "Text")
    primary = _color_by_role(colors, "Primary")
    if not (bg and text and primary):
        missing = [r for r, c in (("Background", bg), ("Text", text), ("Primary", primary)) if not c]
        raise ValueError(
            f"팔레트 '{palette.get('name', '?')}'에 필수 역할이 없습니다: {missing}. "
            "Primary, Background, Text는 반드시 있어야 합니다."
        )

    bg_hex = bg["hex"]
    text_hex = text["hex"]
    primary_hex = primary["hex"]

    secondary = _color_by_role(colors, "Secondary")
    accent = _color_by_role(colors, "Accent")
    surface = _color_by_role(colors, "Surface")
    muted = _color_by_role(colors, "Muted")
    border = _color_by_role(colors, "Border")

    surface_hex = surface["hex"] if surface else derive_surface(bg_hex)
    muted_hex = muted["hex"] if muted else derive_muted_text(text_hex, bg_hex)
    border_hex = border["hex"] if border else derive_border(bg_hex, text_hex)

    # secondary/accent are *optional* — fall back to primary so CSS never breaks
    secondary_hex = secondary["hex"] if secondary else primary_hex
    accent_hex = accent["hex"] if accent else primary_hex

    on_primary_hex, _ = pick_on_color(primary_hex, text_hex, bg_hex)
    on_accent_hex, _ = pick_on_color(accent_hex, text_hex, bg_hex)
    on_surface_hex = text_hex  # surface is close to bg, so palette text works

    return {
        "primary": primary_hex,
        "secondary": secondary_hex,
        "accent": accent_hex,
        "surface": surface_hex,
        "background": bg_hex,
        "text": text_hex,
        "muted": muted_hex,
        "border": border_hex,
        "on_primary": on_primary_hex,
        "on_accent": on_accent_hex,
        "on_surface": on_surface_hex,
        # Track which roles were derived (vs. explicit)
        "_derived": {
            "secondary": secondary is None,
            "accent": accent is None,
            "surface": surface is None,
            "muted": muted is None,
            "border": border is None,
        },
    }


def build_contrast_report(r: dict, m: dict | None = None) -> list[dict]:
    """Compute the contrast pairs that actually appear in the rendered preview.

    Each row is shown in the UI so the user knows whether real text is
    readable. When `m` (resolved material) is provided and the surface is
    translucent (Glass), we additionally check `Text → Effective Surface` —
    the actual blended surface the user sees, which is what matters for
    real-world readability on glass cards.
    """
    pairs = [
        ("Text → Background",      r["text"],       r["background"]),
        ("Text → Surface",         r["text"],       r["surface"]),
        ("On-Primary → Primary",   r["on_primary"], r["primary"]),
        ("Muted → Background",     r["muted"],      r["background"]),
    ]
    if m is not None and float(m.get("surface_alpha", 1.0)) < 0.95:
        pairs.append(("Text → Effective Surface (glass)", r["text"], m["effective_surface"]))
    # Only show accent row if accent is meaningfully different from primary
    if r["accent"].lower() != r["primary"].lower():
        pairs.append(("On-Accent → Accent", r["on_accent"], r["accent"]))

    rows = []
    for label, fg, bg in pairs:
        ratio = contrast_ratio(fg, bg)
        text, css_class = wcag_label(ratio)
        rows.append({"pair": label, "fg": fg, "bg": bg, "text": text, "class": css_class})
    return rows


# ---------- HTML rendering ----------

_PALETTE_CARD = """
<article class="palette" data-language="{language}" style="
  --p-primary:{primary};
  --p-secondary:{secondary};
  --p-accent:{accent};
  --p-surface:{surface};
  --p-bg:{bg};
  --p-text:{text};
  --p-muted:{muted};
  --p-border:{border};
  --p-on-primary:{on_primary};
  --p-on-accent:{on_accent};
  --p-on-surface:{on_surface};
  --p-surface-rgba:{surface_rgba};
  --p-blur:{blur};
  --p-saturate:{saturate};
  --p-border-top:{border_top};
  --p-border-bottom:{border_bottom};
  --p-elev-1:{elev_1};
  --p-elev-2:{elev_2};
  --p-elev-3:{elev_3};
  --p-radius:{radius};
  --p-stage-bg:{stage_bg};
  --shell-fade:{shell_fade};
">
  <header class="palette-head">
    <h2>{idx}. {name}</h2>
    <p class="tagline">{tagline}</p>
    <div class="language-pill">
      <span class="lang-dot lang-dot--{language}"></span>
      <span class="lang-label">{language_label}</span>
    </div>
  </header>

  <dl class="meta">
    <div><dt>무드</dt><dd>{mood}</dd></div>
    <div><dt>언어 근거</dt><dd>{language_rationale}</dd></div>
    <div><dt>근거</dt><dd>{rationale}</dd></div>
  </dl>

  <ul class="swatches">
    {swatches}
  </ul>

  <section class="stage" data-treatment="{treatment}">
    <div class="stage-surface">
      {sample_card}
    </div>
  </section>

  <details class="material" open>
    <summary>Material 토큰 ({language_label})</summary>
    <ul class="material-list">
      {material_rows}
    </ul>
  </details>

  <details class="ui-map">
    <summary>UI 요소 적용 가이드</summary>
    <ul class="ui-map-list">
      {ui_map_rows}
    </ul>
  </details>

  <section class="contrast">
    <h4>대비비 (미리보기에 실제로 나타나는 FG/BG 쌍)</h4>
    <ul class="contrast-list">
      {contrast_rows}
    </ul>
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
    <div class="chip-role">{role}{derived_tag}</div>
    <div class="chip-name">{name}</div>
    <code class="chip-hex">{hex_upper}</code>
    <div class="chip-usage">{usage}</div>
  </div>
</li>
"""


_CONTRAST_ROW = """
<li class="contrast-row">
  <div class="contrast-swatches">
    <span class="contrast-chip" style="background:{bg};color:{fg};">Aa</span>
  </div>
  <div class="contrast-label">{pair}</div>
  <span class="badge badge-{cls}">{text}</span>
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
  .chip-derived {{
    display: inline-block;
    margin-left: 6px;
    padding: 1px 6px;
    border-radius: 4px;
    background: var(--shell-border);
    color: var(--shell-muted);
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.04em;
    vertical-align: middle;
  }}
  .chip-name {{ color: var(--shell-muted); }}
  .chip-hex {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 11px; }}
  .chip-usage {{ color: var(--shell-muted); font-size: 11px; }}

  /* ---- Language pill on palette head ---- */
  .language-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--shell-border);
    font-size: 11px;
    font-weight: 600;
    color: var(--shell-fg);
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}
  .lang-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--shell-fg);
  }}
  .lang-dot--flat   {{ background: #94A3B8; }}
  .lang-dot--glass  {{ background: linear-gradient(135deg, #A5B4FC, #F0ABFC); }}
  .lang-dot--soft   {{ background: #FDE68A; }}
  .lang-dot--bold   {{ background: #F97316; }}
  .lang-dot--cyber  {{ background: radial-gradient(circle, #67E8F9 0%, #06B6D4 60%, #0E7490 100%); box-shadow: 0 0 6px rgba(103,232,249,0.7); }}

  /* ---- Stage: the language-aware preview area ----
     This is the BG that the sample card sits on. Glass needs a non-flat BG
     for the blur to be visible; Cyber needs an OLED vignette; Soft needs a
     subtle radial; Flat/Bold can stay solid. */
  .stage {{
    position: relative;
    border-radius: 16px;
    padding: 28px;
    overflow: hidden;
    isolation: isolate;
    background: var(--p-bg);
  }}
  .stage[data-treatment="solid"] {{ background: var(--p-bg); }}
  .stage[data-treatment="gradient"] {{
    background: var(--p-stage-bg);
  }}
  .stage[data-treatment="soft-radial"] {{
    background:
      radial-gradient(circle at 18% 12%, color-mix(in srgb, var(--p-primary) 34%, var(--p-bg)) 0%, transparent 55%),
      radial-gradient(circle at 88% 78%, color-mix(in srgb, var(--p-accent) 28%, var(--p-bg)) 0%, transparent 50%),
      var(--p-bg);
  }}
  .stage[data-treatment="oled-vignette"] {{
    background:
      radial-gradient(ellipse at top, color-mix(in srgb, var(--p-primary) 22%, #000) 0%, #050608 60%, #000 100%),
      #000;
  }}
  .stage[data-treatment="color-block"] {{
    background:
      linear-gradient(135deg, var(--p-primary) 0%, var(--p-primary) 38%, var(--p-bg) 38%, var(--p-bg) 100%);
  }}
  /* Subtle noise/dither so gradients don't band */
  .stage::before {{
    content: ""; position: absolute; inset: 0; pointer-events: none;
    background:
      repeating-radial-gradient(circle at 0 0, rgba(255,255,255,0.015) 0, rgba(255,255,255,0.015) 1px, transparent 1px, transparent 3px);
    z-index: 0;
  }}
  .stage-surface {{ position: relative; z-index: 1; }}

  /* ---- Sample card defaults (Flat) ---- */
  .sample {{ border-radius: 12px; padding: 0; }}
  .sample-card {{
    position: relative;
    background: var(--p-bg);
    color: var(--p-text);
    border-radius: var(--p-radius);
    padding: 22px 22px 20px;
    border: 1px solid var(--p-border-top);
    box-shadow: var(--p-elev-2);
    min-height: 220px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  /* ---- Per-language sample-card treatment ---- */
  .palette[data-language="glass"] .sample-card {{
    background: var(--p-surface-rgba);
    -webkit-backdrop-filter: blur(var(--p-blur)) saturate(var(--p-saturate));
    backdrop-filter: blur(var(--p-blur)) saturate(var(--p-saturate));
    border: 1px solid var(--p-border-top);
    box-shadow:
      inset 0 -1px 0 var(--p-border-bottom),
      inset 0 1px 0 var(--p-border-top),
      var(--p-elev-2);
  }}
  .palette[data-language="soft"] .sample-card {{
    background: var(--p-surface);
    border: 1px solid var(--p-border-top);
    box-shadow: var(--p-elev-2);
  }}
  .palette[data-language="bold"] .sample-card {{
    background: var(--p-surface);
    border: none;
    box-shadow: var(--p-elev-2);
  }}
  .palette[data-language="cyber"] .sample-card {{
    background: var(--p-surface);
    border: 1px solid var(--p-border-top);
    box-shadow:
      inset 0 1px 0 var(--p-border-top),
      var(--p-elev-2);
  }}
  .sample-pill {{
    display: inline-block;
    align-self: flex-start;
    background: var(--p-primary);
    color: var(--p-on-primary);
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 999px;
    margin-bottom: 4px;
    font-weight: 600;
  }}
  .sample-card h3 {{ margin: 0; font-size: 13px; color: var(--p-muted); font-weight: 500; }}
  .sample-amount {{ margin: 2px 0 0; font-size: 28px; font-weight: 700; letter-spacing: -0.01em; color: var(--p-text); }}
  .sample-sub {{ margin: 0; font-size: 12px; color: var(--p-muted); }}
  .sample-actions {{ margin-top: auto; display: flex; gap: 8px; }}
  .btn-primary {{
    background: var(--p-primary);
    color: var(--p-on-primary);
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
    border: 1px solid var(--p-border);
    padding: 9px 16px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    flex: 1;
  }}
  .btn-danger {{
    background: var(--p-accent);
    color: var(--p-on-accent);
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
    color: var(--p-on-accent);
    font-size: 10px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
    letter-spacing: 0.08em;
  }}
  .ticker-row {{ display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }}
  .ticker-symbol {{ font-size: 11px; color: var(--p-muted); font-weight: 600; letter-spacing: 0.06em; }}
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
    color: var(--p-on-surface);
  }}
  .ob-row {{ display: flex; justify-content: space-between; padding: 2px 0; }}
  .ob-row.sell .ob-px {{ color: var(--signal-down); }}
  .ob-row.buy  .ob-px {{ color: var(--signal-up); }}
  .ob-amt {{ color: var(--p-muted); }}
  .ob-spread {{
    text-align: center;
    padding: 4px 0;
    margin: 2px -10px;
    font-size: 10px;
    color: var(--p-muted);
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
  .session-time {{ font-size: 11px; color: var(--p-muted); }}
  .session-title {{ margin: 4px 0 2px; font-size: 18px; font-weight: 700; letter-spacing: -0.01em; color: var(--p-text); }}
  .session-meta {{ display: flex; gap: 8px; font-size: 11px; color: var(--p-muted); }}
  .session-meta span::before {{ content: "·"; margin-right: 6px; opacity: 0.5; }}
  .session-meta span:first-child::before {{ content: none; margin: 0; }}
  .menu-item {{ display: flex; justify-content: space-between; font-size: 12px; padding: 5px 0; border-bottom: 1px dashed var(--p-border); color: var(--p-text); }}
  .menu-item:last-child {{ border-bottom: none; }}
  .menu-item .price {{ color: var(--p-muted); font-variant-numeric: tabular-nums; }}
  .metric-label {{ font-size: 12px; color: var(--p-muted); }}
  .metric-value {{ font-size: 24px; font-weight: 700; letter-spacing: -0.01em; margin: 2px 0 0; color: var(--p-text); }}
  .product-img {{ width: 100%; height: 70px; border-radius: 8px; background: linear-gradient(135deg, var(--p-secondary), var(--p-primary)); opacity: 0.4; margin-bottom: 6px; }}
  .progress-track {{ height: 6px; background: var(--p-surface); border-radius: 3px; margin: 8px 0 4px; overflow: hidden; }}
  .progress-fill {{ height: 100%; background: var(--p-primary); border-radius: 3px; }}

  /* ---- Material tokens + UI map sections ---- */
  details.material, details.ui-map {{
    border: 1px solid var(--shell-border);
    border-radius: 12px;
    padding: 12px 14px;
  }}
  details.material > summary, details.ui-map > summary {{
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    color: var(--shell-fg);
  }}
  .material-list, .ui-map-list {{
    margin: 12px 0 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 6px;
    font-size: 11.5px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}
  .material-row, .ui-map-row {{
    display: grid;
    grid-template-columns: minmax(110px, 0.4fr) 1fr;
    gap: 10px;
    align-items: start;
  }}
  .material-row .k, .ui-map-row .k {{
    color: var(--shell-muted);
  }}
  .material-row .v, .ui-map-row .v {{
    color: var(--shell-fg);
    word-break: break-word;
  }}
  .ui-map-list {{ font-family: -apple-system, "Pretendard", system-ui, sans-serif; font-size: 12px; }}
  .ui-map-row .v code {{
    background: var(--shell-bg);
    padding: 1px 5px;
    border-radius: 4px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 11px;
  }}

  .contrast h4 {{ margin: 0 0 10px; font-size: 12px; color: var(--shell-muted); font-weight: 500; }}
  .contrast-list {{ margin: 0; padding: 0; list-style: none; display: grid; gap: 6px; }}
  .contrast-row {{
    display: grid;
    grid-template-columns: 32px 1fr auto;
    align-items: center;
    gap: 10px;
    font-size: 12px;
  }}
  .contrast-chip {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 24px;
    border-radius: 6px;
    border: 1px solid var(--shell-border);
    font-size: 11px;
    font-weight: 700;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}
  .contrast-label {{ color: var(--shell-fg); }}
  .badge {{
    display: inline-block;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-weight: 700;
    white-space: nowrap;
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

_CSS_VAR_ORDER = [
    ("primary",   "--color-primary"),
    ("secondary", "--color-secondary"),
    ("accent",    "--color-accent"),
    ("surface",   "--color-surface"),
    ("background","--color-bg"),
    ("text",      "--color-text"),
    ("muted",     "--color-muted"),
    ("border",    "--color-border"),
]


def _css_snippet(resolved: dict, original_colors: list[dict], material: dict | None = None) -> str:
    """Emit CSS variables for every role present in the user's palette plus
    the resolved material tokens. Material tokens are emitted regardless of
    design language — they're useful for the dev even on Flat (just with
    surface_alpha=1 and blur=0)."""
    explicit_roles = {c["role"].lower() for c in original_colors}
    lines = []
    for key, var in _CSS_VAR_ORDER:
        if key in explicit_roles or key in ("primary", "background", "text"):
            lines.append(f"{var}: {resolved[key].upper()};")
    lines.append(f"--color-on-primary: {resolved['on_primary'].upper()};")
    if resolved["accent"].lower() != resolved["primary"].lower():
        lines.append(f"--color-on-accent: {resolved['on_accent'].upper()};")

    if material is not None:
        sr, sg, sb = _hex_to_rgb(resolved["surface"])
        lines.append("")
        lines.append(f"/* Material — design_language: {material['language']} */")
        lines.append(f"--material-surface: rgba({sr}, {sg}, {sb}, {material['surface_alpha']});")
        lines.append(f"--material-blur: blur({material['blur']}) saturate({material['saturate']});")
        lines.append(f"--material-border-top: {material['border_top']};")
        lines.append(f"--material-border-bottom: {material['border_bottom']};")
        lines.append(f"--elevation-1: {material['elevation'][0]};")
        lines.append(f"--elevation-2: {material['elevation'][1]};")
        lines.append(f"--elevation-3: {material['elevation'][2]};")
        lines.append(f"--radius-card: {material['radius']};")
    return "\n".join(lines)


def _render_swatches(palette: dict) -> str:
    pieces = []
    for c in palette["colors"]:
        # for the Text swatch, paint a thin border so very-dark chips don't disappear
        extra = ""
        if c["role"].lower() == "text":
            extra = "border:1px solid rgba(0,0,0,0.12);"
        pieces.append(_SWATCH.format(
            hex_=c["hex"],
            extra_style=extra,
            role=c["role"],
            derived_tag="",
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
  <p class="sample-sub" style="margin-top:10px;">"지금 이 순간에 머무르세요"</p>
  <div class="sample-actions">
    <button class="btn-primary">▶ 시작하기</button>
    <button class="btn-secondary">나중에</button>
  </div>
</div>""",
    "fitness": """<div class="sample-card">
  <div class="sample-pill">오늘의 운동</div>
  <p class="session-time">42분 · 상체 + 코어</p>
  <h2 class="session-title">Push Day · Upper Power</h2>
  <div class="session-meta"><span>난이도 중상</span><span>520 kcal</span><span>8개 동작</span></div>
  <div class="progress-track"><div class="progress-fill" style="width:34%;"></div></div>
  <p class="sample-sub">이번 주 4회 중 2회 완료 · 스트릭 12일 🔥</p>
  <div class="sample-actions">
    <button class="btn-primary">▶ 시작하기</button>
    <button class="btn-secondary">루틴 보기</button>
  </div>
  <span class="sample-badge">PR</span>
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
  <div class="progress-track"><div class="progress-fill" style="width:62%;"></div></div>
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
    if any(k in hint for k in ["피트니스", "운동", "헬스장", "워크아웃", "트레이닝", "근력", "유산소", "fitness", "workout", "gym", "training", "exercise"]):
        return "fitness"
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
    if any(k in hint for k in ["피트니스", "운동", "워크아웃", "트레이닝"]):
        return "운동 시작"
    if any(k in hint for k in ["헬스", "명상", "건강"]):
        return "시작하기"
    if any(k in hint for k in ["커머스", "쇼핑", "이커머스", "마켓"]):
        return "구매하기"
    if any(k in hint for k in ["배달", "푸드", "음식", "맛집"]):
        return "주문하기"
    return "시작하기"


# ---------- Material + UI map rendering helpers ----------

_LANGUAGE_LABEL = {
    "flat":  "Flat / Minimal",
    "glass": "Glass / Material",
    "soft":  "Soft / Pillowy",
    "bold":  "Bold / Editorial",
    "cyber": "Cyber / Neon Dark",
}


def _surface_rgba(surface_hex: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(surface_hex)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def _stage_gradient(language: str, resolved: dict, treatment: str) -> str:
    """Return a CSS background value for the stage area, based on treatment.

    The stage is what the sample card sits *on top of*. For Glass it must be
    visually rich (gradient) so backdrop-blur is visible; for others it can
    be the palette BG or a per-language treatment.
    """
    primary = resolved["primary"]
    secondary = resolved.get("secondary") or primary
    accent = resolved.get("accent") or primary
    bg = resolved["background"]

    if treatment == "gradient":
        # For Glass: a soft three-stop gradient between brand colors. We
        # bias toward the BG hue on the far edge so the card still feels
        # "on this palette" rather than "on a totally different page."
        return (
            f"linear-gradient(135deg, "
            f"{primary} 0%, "
            f"{secondary} 50%, "
            f"{accent} 100%)"
        )
    if treatment == "soft-radial":
        return bg  # actual radial is in CSS via color-mix
    if treatment == "oled-vignette":
        return "#000"  # actual radial vignette is in CSS
    if treatment == "color-block":
        return bg  # gradient is in CSS using the data-treatment selector
    return bg  # "solid" or unknown


def _build_material_rows(material: dict) -> str:
    """Render the Material tokens detail list."""
    rows = [
        ("design_language",   _LANGUAGE_LABEL.get(material["language"], material["language"])),
        ("surface_alpha",     f"{material['surface_alpha']}"),
        ("backdrop-blur",     str(material["blur"])),
        ("backdrop-saturate", str(material["saturate"])),
        ("border_top",        str(material["border_top"])),
        ("border_bottom",     str(material["border_bottom"])),
        ("elevation L1",      material["elevation"][0]),
        ("elevation L2",      material["elevation"][1]),
        ("elevation L3",      material["elevation"][2]),
        ("background_treatment", str(material["background_treatment"])),
        ("radius",            str(material["radius"])),
    ]
    out = []
    for k, v in rows:
        out.append(
            f'<li class="material-row"><span class="k">{k}</span>'
            f'<span class="v">{v}</span></li>'
        )
    return "\n".join(out)


def _build_ui_map_rows(material: dict, resolved: dict) -> str:
    """Render the UI element → token mapping list. This is the table that
    tells a designer/dev *exactly* how each color/token gets used.
    """
    lang = material["language"]
    bg = resolved["background"].upper()
    primary = resolved["primary"].upper()
    text = resolved["text"].upper()
    radius = material["radius"]

    if lang == "glass":
        surface_css = (
            f"<code>background: {material['effective_surface'].upper()}</code> "
            f"(<code>{_surface_rgba(resolved['surface'], material['surface_alpha'])}</code> "
            f"+ <code>backdrop-filter: blur({material['blur']}) saturate({material['saturate']})</code>)"
        )
        border_css = (
            f"<code>border: 1px solid {material['border_top']}</code> + "
            f"<code>box-shadow: inset 0 -1px 0 {material['border_bottom']}</code>"
        )
    elif lang == "cyber":
        surface_css = f"<code>background: {resolved['surface'].upper()}</code> (lifted OLED black)"
        border_css = f"<code>border: 1px solid {material['border_top']}</code> (Primary glow)"
    elif lang == "soft":
        surface_css = f"<code>background: {resolved['surface'].upper()}</code>"
        border_css = "거의 없음 — ambient shadow가 경계 역할"
    elif lang == "bold":
        surface_css = f"<code>background: {resolved['surface'].upper()}</code>"
        border_css = "없음 — 컬러 블록과 무거운 directional shadow로 구분"
    else:  # flat
        surface_css = f"<code>background: {resolved['surface'].upper()}</code>"
        border_css = f"<code>border: 1px solid {resolved['border'].upper()}</code>"

    treatment = material["background_treatment"]
    if treatment == "gradient":
        bg_css = f"<code>linear-gradient(135deg, {primary}, {resolved['accent'].upper()})</code> (Glass용 — blur가 살아나도록)"
    elif treatment == "soft-radial":
        bg_css = f"<code>radial-gradient(...{primary}, {bg})</code> + <code>{bg}</code> base"
    elif treatment == "oled-vignette":
        bg_css = f"OLED 블랙 + Primary 글로우 비네트"
    elif treatment == "color-block":
        bg_css = f"<code>{primary}</code> 큰 컬러 블록 + <code>{bg}</code> 영역 분할"
    else:
        bg_css = f"<code>background: {bg}</code> (단색)"

    shadow_css = f"<code>box-shadow: {material['elevation'][1]}</code> (L2 = card 기본)"

    rows = [
        ("전체 배경 (Body)", bg_css),
        ("카드 표면 (Surface)", surface_css),
        ("테두리 (Border)", border_css),
        ("공간감 그림자 (Shadow)", shadow_css),
        ("CTA 버튼", f"<code>background: {primary}; color: {resolved['on_primary'].upper()}; border-radius: {radius}</code>"),
        ("본문 텍스트", f"<code>color: {text}</code>"),
        ("보조 텍스트", f"<code>color: {resolved['muted'].upper()}</code>"),
    ]
    out = []
    for k, v in rows:
        out.append(
            f'<li class="ui-map-row"><span class="k">{k}</span>'
            f'<span class="v">{v}</span></li>'
        )
    return "\n".join(out)


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
    all_bg_dark = True
    for idx, p in enumerate(palettes, start=1):
        r = resolve_palette(p)
        m = resolve_material(p, r)
        bg_lum = _relative_luminance(r["background"])
        is_dark_bg = bg_lum < 0.2
        # Cyber always uses dark OLED stage, so count it as dark for shell mode
        if m["language"] == "cyber":
            is_dark_bg = True
        all_bg_dark = all_bg_dark and is_dark_bg
        shell_fade = "rgba(255,255,255,0.08)" if is_dark_bg else "rgba(0,0,0,0.08)"

        contrast_rows_html = "\n".join(
            _CONTRAST_ROW.format(
                pair=row["pair"], fg=row["fg"], bg=row["bg"],
                text=row["text"], cls=row["class"],
            ) for row in build_contrast_report(r, m)
        )

        treatment = m["background_treatment"]
        stage_bg = _stage_gradient(m["language"], r, treatment)
        surface_rgba = _surface_rgba(r["surface"], float(m["surface_alpha"]))

        cards.append(_PALETTE_CARD.format(
            idx=idx,
            name=p.get("name", f"Palette {idx}"),
            tagline=p.get("tagline", ""),
            mood=p.get("mood", ""),
            target_fit=p.get("target_fit", ""),
            rationale=p.get("rationale", ""),
            language=m["language"],
            language_label=_LANGUAGE_LABEL.get(m["language"], m["language"]),
            language_rationale=p.get("language_rationale", "(언어 선택 이유가 명시되지 않음 — 추천서에 1문장 추가하세요)"),
            swatches=_render_swatches(p),
            primary=r["primary"],
            secondary=r["secondary"],
            accent=r["accent"],
            surface=r["surface"],
            bg=r["background"],
            text=r["text"],
            muted=r["muted"],
            border=r["border"],
            on_primary=r["on_primary"],
            on_accent=r["on_accent"],
            on_surface=r["on_surface"],
            surface_rgba=surface_rgba,
            blur=m["blur"],
            saturate=m["saturate"],
            border_top=m["border_top"],
            border_bottom=m["border_bottom"],
            elev_1=m["elevation"][0],
            elev_2=m["elevation"][1],
            elev_3=m["elevation"][2],
            radius=m["radius"],
            stage_bg=stage_bg,
            treatment=treatment,
            shell_fade=shell_fade,
            sample_card=sample_card_html,
            material_rows=_build_material_rows(m),
            ui_map_rows=_build_ui_map_rows(m, r),
            contrast_rows=contrast_rows_html,
            css_snippet=_css_snippet(r, p.get("colors", []), m),
        ))

    shell_mode = "dark" if all_bg_dark else "light"

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

    palettes = data.get("palettes", [])
    print(f"✓ Generated {args.output} with {len(palettes)} palette(s).")
    has_fail = False
    for p in palettes:
        r = resolve_palette(p)
        m = resolve_material(p, r)
        lang = _LANGUAGE_LABEL.get(m["language"], m["language"])
        print(f"  · {p.get('name', '?')}  [{lang}]")
        if "design_language" not in p:
            print("      ⚠ design_language 미지정 → flat으로 가정. JSON에 명시하세요.")
        for row in build_contrast_report(r, m):
            marker = "✓" if row["class"] == "pass" else ("⚠" if row["class"] == "warn" else "✗")
            if row["class"] == "fail":
                has_fail = True
            print(f"      {marker} {row['pair']:<36} {row['text']}")
    if has_fail:
        print("\n⚠ 일부 FG/BG 쌍이 WCAG AA(4.5:1)에 미달합니다. 팔레트를 조정하거나 on-color 토큰을 명시하세요.")
        print("   (Glass의 경우 'Text → Effective Surface' 항목이 실제 사용자가 보는 카드 위 대비입니다.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
