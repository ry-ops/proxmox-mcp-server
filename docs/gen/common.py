"""Shared bits for the README animations: palette, base styles, keyframe helpers."""

from __future__ import annotations

BG, PANEL, CARD, LINE = "#0f1420", "#161d2b", "#1d2536", "#2c3750"
TEXT, MUTED = "#e6ebf5", "#8b96ad"
ORANGE, ORANGE_T, BLUE, BLUE_T = "#ff8a1f", "#ffc48a", "#3ec7ff", "#a8e4ff"
GREEN, GREEN_T, RED, RED_T, PURPLE, PURPLE_T, AMBER = (
    "#3ddc84",
    "#9ff0c4",
    "#ff5c6e",
    "#ff9aa5",
    "#b58cff",
    "#d9c6ff",
    "#ffb02e",
)


class Anim:
    """Collects CSS keyframes for one SVG with a fixed loop length (seconds)."""

    def __init__(self, dur: float):
        self.dur = dur
        self.rules: list[str] = []
        self.n = 0

    def pct(self, t: float) -> str:
        return f"{max(0.0, min(100.0, 100 * t / self.dur)):.2f}%"

    def fade(
        self, t_in: float, t_out: float | None = None, rise: float = 6, ease: float = 0.35
    ) -> str:
        """Class that fades (and rises) in at t_in and out at t_out (default: loop end)."""
        self.n += 1
        c = f"a{self.n}"
        end = t_out if t_out is not None else self.dur - 0.5
        self.rules.append(
            f"@keyframes {c} {{ 0%,{self.pct(t_in)} {{ opacity: 0; transform: translateY({rise}px); }} "
            f"{self.pct(t_in + ease)},{self.pct(end)} {{ opacity: 1; transform: translateY(0); }} "
            f"{self.pct(end + ease)},100% {{ opacity: 0; transform: translateY(0); }} }} "
            f".{c} {{ animation: {c} {self.dur}s infinite; }}"
        )
        return c

    def grow(self, t0: float, t1: float, width: float, t_out: float | None = None) -> str:
        """Class that grows a rect's width from 0 to `width` between t0 and t1."""
        self.n += 1
        c = f"a{self.n}"
        end = t_out if t_out is not None else self.dur - 0.5
        self.rules.append(
            f"@keyframes {c} {{ 0%,{self.pct(t0)} {{ width: 0; }} {self.pct(t1)},{self.pct(end)} {{ width: {width}px; }} "
            f"{self.pct(end + 0.35)},100% {{ width: 0; }} }} .{c} {{ animation: {c} {self.dur}s infinite; }}"
        )
        return c

    def move(self, t0: float, t1: float, dx: float, dy: float = 0, hide_after: float = 0.3) -> str:
        """Class for a dot that travels (dx, dy) between t0 and t1, then vanishes."""
        self.n += 1
        c = f"a{self.n}"
        self.rules.append(
            f"@keyframes {c} {{ 0%,{self.pct(t0)} {{ transform: translate(0,0); opacity: 0; }} "
            f"{self.pct(t0 + 0.1)} {{ opacity: 1; }} {self.pct(t1)} {{ transform: translate({dx}px,{dy}px); opacity: 1; }} "
            f"{self.pct(t1 + hide_after)},100% {{ transform: translate({dx}px,{dy}px); opacity: 0; }} }} "
            f".{c} {{ animation: {c} {self.dur}s infinite; }}"
        )
        return c

    def pulse(self, t: float, prop: str = "stroke-width", lo: str = "2", hi: str = "5") -> str:
        self.n += 1
        c = f"a{self.n}"
        self.rules.append(
            f"@keyframes {c} {{ 0%,{self.pct(t - 0.2)},{self.pct(t + 0.6)},100% {{ {prop}: {lo}; }} {self.pct(t + 0.15)} {{ {prop}: {hi}; }} }} "
            f".{c} {{ animation: {c} {self.dur}s infinite; }}"
        )
        return c

    def style(self, extra: str = "") -> str:
        rules = "\n    ".join(self.rules)
        return f"""<style>
    text {{ font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; fill: {TEXT}; }}
    .muted {{ fill: {MUTED}; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    {rules}
    {extra}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>"""


def svg(w: int, h: int, title: str, desc: str, style: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">
  <title id="t">{title}</title>
  <desc id="d">{desc}</desc>
  {style}

  <rect width="{w}" height="{h}" rx="20" fill="{BG}"/>
{body}
</svg>
"""
