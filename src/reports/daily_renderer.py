"""
Daily report renderer.

Outputs:
1. A themeable SVG poster suitable for article covers or image embeds.
2. A standalone interactive HTML widget for H5/article webviews.
"""
from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from PIL import Image, ImageDraw, ImageFont

from src.core.models import DailyLogEntry, MoodEmoji


@dataclass
class RenderedDailyReport:
    date: str
    theme: str
    title: str
    description: str
    author: str
    source_name: str
    poster_svg_path: Path
    poster_png_path: Path
    poster_html_path: Path
    widget_path: Path
    article_path: Path


@dataclass
class ThemePreviewBundle:
    theme: str
    name: str
    description: str
    poster_png_path: Path
    poster_html_path: Path
    widget_path: Path
    article_path: Path
    accent: str = ""
    accent_2: str = ""
    accent_3: str = ""


@dataclass
class DailyReportSummary:
    date: str
    theme: str
    title: str
    description: str
    author: str
    source_name: str
    source_statement: str
    user_note: str
    generated_at: str
    total_minutes: int
    total_entries: int
    skills: List[str]
    insights: List[str]
    problems: List[str]
    plans: List[str]
    mood: int | None
    highlights: List[str]
    entries: List[DailyLogEntry]




# ── Token mapping: ThemeManifest dotted tokens → flat dict keys ──
DAILY_TOKEN_MAP = {
    "color.bg_start": "bg_start",
    "color.bg_end": "bg_end",
    "color.panel": "panel",
    "color.panel_alt": "panel_alt",
    "color.accent": "accent",
    "color.accent_2": "accent_2",
    "color.accent_3": "accent_3",
    "color.text": "text",
    "color.muted": "muted",
    "color.glow": "glow",
    "font.family": "font",
    "branding.tagline": "tagline",
    "branding.eyebrow": "eyebrow",
}

# ── Lazy singleton registry reference ──
_REGISTRY: "TemplateRegistry | None" = None


def _get_registry() -> "TemplateRegistry":
    """Get or create the shared template registry singleton."""
    global _REGISTRY
    if _REGISTRY is None:
        from src.templates.registry import TemplateRegistry
        _REGISTRY = TemplateRegistry()
        _REGISTRY.load_all()
    return _REGISTRY


def _resolve_theme(theme_key: str) -> dict:
    """Resolve a theme key to a flat dict using the registry.

    Falls back to loading from YAML if registry not yet fully wired.
    """
    theme_manifest = _get_registry().get_theme("daily.report", theme_key)
    if theme_manifest is None:
        raise ValueError(f"Unknown daily report theme: {theme_key}")
    return theme_manifest.to_flat_dict(DAILY_TOKEN_MAP)


def _slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if not item:
            continue
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def summarize_daily_logs(
    logs: List[DailyLogEntry],
    *,
    date: str,
    theme: str,
    title: str,
    description: str,
    author: str,
    source_name: str,
    source_statement: str,
    user_note: str,
) -> DailyReportSummary:
    if not logs:
        raise ValueError(f"No daily logs found for {date}")

    skills = _dedupe(log.skill_name for log in logs)
    insights = _dedupe(item for log in logs for item in log.insights)
    problems = _dedupe(item for log in logs for item in log.problems)
    plans = _dedupe(item for log in logs for item in log.plans)
    total_minutes = sum(log.duration_minutes for log in logs)
    moods = [log.mood for log in logs if log.mood is not None]
    mood = round(sum(moods) / len(moods)) if moods else None
    highlights = _dedupe(
        [
            f"{total_minutes} 分钟专注投入",
            f"{len(skills)} 个核心技能持续推进",
            insights[0] if insights else "",
            plans[0] if plans else "",
        ]
    )[:4]

    return DailyReportSummary(
        date=date,
        theme=theme,
        title=title,
        description=description,
        author=author,
        source_name=source_name,
        source_statement=source_statement,
        user_note=user_note,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        total_minutes=total_minutes,
        total_entries=len(logs),
        skills=skills,
        insights=insights[:4],
        problems=problems[:4],
        plans=plans[:4],
        mood=mood,
        highlights=highlights,
        entries=logs,
    )


def _theme(theme_key: str) -> dict:
    return _resolve_theme(theme_key)


def list_themes() -> List[dict]:
    registry = _get_registry()
    themes = registry.list_theme_manifests("daily.report")
    return [
        {
            "key": t.id,
            "name": t.name,
            "description": t.description or "",
            "accent": t.tokens.get("color.accent", "#888"),
            "accent_2": t.tokens.get("color.accent_2", "#888"),
            "accent_3": t.tokens.get("color.accent_3", "#888"),
            "tagline": t.tokens.get("branding.tagline", ""),
        }
        for t in themes
    ]


def render_daily_report(
    logs: List[DailyLogEntry],
    *,
    date: str,
    theme: str,
    title: str,
    description: str,
    author: str,
    source_name: str,
    source_statement: str,
    user_note: str = "",
    output_dir: str = "data/reports",
) -> RenderedDailyReport:
    summary = summarize_daily_logs(
        logs,
        date=date,
        theme=theme,
        title=title,
        description=description,
        author=author,
        source_name=source_name,
        source_statement=source_statement,
        user_note=user_note,
    )
    theme_spec = _theme(theme)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"daily-{date}-{_slugify(theme)}"

    poster_svg_path = out_dir / f"{base_name}-poster.svg"
    poster_png_path = out_dir / f"{base_name}-poster.png"
    poster_html_path = out_dir / f"{base_name}-poster.html"
    widget_path = out_dir / f"{base_name}-widget.html"
    article_path = out_dir / f"{base_name}-article.html"

    poster_svg_path.write_text(_build_poster_svg(summary, theme_spec), encoding="utf-8")
    _build_poster_png(summary, theme_spec, poster_png_path)
    poster_html_path.write_text(_build_poster_html(summary, theme_spec, poster_png_path.name), encoding="utf-8")
    widget_path.write_text(_build_widget_html(summary, theme_spec), encoding="utf-8")
    article_path.write_text(
        _build_article_html(summary, theme_spec, poster_svg_path.name, poster_png_path.name, widget_path.name),
        encoding="utf-8",
    )

    return RenderedDailyReport(
        date=date,
        theme=theme,
        title=title,
        description=description,
        author=author,
        source_name=source_name,
        poster_svg_path=poster_svg_path,
        poster_png_path=poster_png_path,
        poster_html_path=poster_html_path,
        widget_path=widget_path,
        article_path=article_path,
    )


def render_theme_preview_gallery(
    logs: List[DailyLogEntry],
    *,
    date: str,
    title: str,
    description: str,
    author: str,
    source_name: str,
    source_statement: str,
    user_note: str = "",
    output_dir: str = "data/reports",
) -> tuple[Path, List[ThemePreviewBundle]]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bundles: List[ThemePreviewBundle] = []
    registry = _get_registry()
    themes = registry.list_theme_manifests("daily.report")
    for theme_manifest in themes:
        theme_key = theme_manifest.id
        rendered = render_daily_report(
            logs,
            date=date,
            theme=theme_key,
            title=title,
            description=description,
            author=author,
            source_name=source_name,
            source_statement=source_statement,
            user_note=user_note,
            output_dir=output_dir,
        )
        bundles.append(
            ThemePreviewBundle(
                theme=theme_key,
                name=theme_manifest.name,
                description=theme_manifest.description or "",
                accent=theme_manifest.tokens.get("color.accent", "#888"),
                accent_2=theme_manifest.tokens.get("color.accent_2", "#888"),
                accent_3=theme_manifest.tokens.get("color.accent_3", "#888"),
                poster_png_path=rendered.poster_png_path,
                poster_html_path=rendered.poster_html_path,
                widget_path=rendered.widget_path,
                article_path=rendered.article_path,
            )
        )

    gallery_path = out_dir / f"daily-{date}-theme-gallery.html"
    gallery_path.write_text(_build_theme_gallery_html(date, bundles), encoding="utf-8")
    return gallery_path, bundles


def _build_poster_svg(summary: DailyReportSummary, theme: dict) -> str:
    skills = " · ".join(summary.skills[:3]) or "General"
    insight_lines = summary.insights[:2] or ["暂无心得，等待下一次记录刷新。"]
    plan_lines = summary.plans[:2] or ["继续推进核心任务。"]
    mood_text = MoodEmoji.from_int(summary.mood) if summary.mood else "·"
    highlight_blocks = "".join(
        f"""
        <g transform="translate({40 + index * 220}, 370)">
          <rect width="190" height="88" rx="18" fill="{theme['panel_alt']}" opacity="0.96" />
          <text x="18" y="32" fill="{theme['accent']}" font-size="13" font-family="{theme['font']}">HIGHLIGHT {index + 1}</text>
          <text x="18" y="58" fill="{theme['text']}" font-size="18" font-family="{theme['font']}">{html.escape(text)}</text>
        </g>
        """
        for index, text in enumerate(summary.highlights[:3])
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1600" viewBox="0 0 1200 1600">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{theme['bg_start']}" />
      <stop offset="100%" stop-color="{theme['bg_end']}" />
    </linearGradient>
    <radialGradient id="halo" cx="50%" cy="30%" r="60%">
      <stop offset="0%" stop-color="{theme['glow']}" stop-opacity="0.55" />
      <stop offset="100%" stop-color="{theme['glow']}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="1200" height="1600" fill="url(#bg)" />
  <circle cx="860" cy="240" r="320" fill="url(#halo)" />
  <circle cx="250" cy="1280" r="260" fill="url(#halo)" opacity="0.6" />
  <rect x="40" y="40" width="1120" height="1520" rx="36" fill="{theme['panel']}" fill-opacity="0.72" stroke="{theme['accent_2']}" stroke-opacity="0.38" />
  <text x="70" y="110" fill="{theme['accent']}" font-size="20" font-family="{theme['font']}">{theme['tagline']}</text>
  <text x="70" y="200" fill="{theme['text']}" font-size="72" font-family="{theme['font']}" font-weight="700">{html.escape(summary.title)}</text>
  <text x="70" y="250" fill="{theme['muted']}" font-size="30" font-family="{theme['font']}">{html.escape(summary.description)}</text>
  <text x="70" y="310" fill="{theme['muted']}" font-size="24" font-family="{theme['font']}">{summary.date}  ·  {html.escape(skills)}  ·  心情 {mood_text}</text>

  <g transform="translate(70, 350)">
    <rect width="300" height="180" rx="28" fill="{theme['panel_alt']}" />
    <text x="28" y="42" fill="{theme['muted']}" font-size="18" font-family="{theme['font']}">FOCUS TIME</text>
    <text x="28" y="112" fill="{theme['text']}" font-size="64" font-family="{theme['font']}" font-weight="700">{summary.total_minutes}</text>
    <text x="28" y="148" fill="{theme['accent']}" font-size="24" font-family="{theme['font']}">分钟</text>
  </g>

  <g transform="translate(400, 350)">
    <rect width="300" height="180" rx="28" fill="{theme['panel_alt']}" />
    <text x="28" y="42" fill="{theme['muted']}" font-size="18" font-family="{theme['font']}">ENTRY COUNT</text>
    <text x="28" y="112" fill="{theme['text']}" font-size="64" font-family="{theme['font']}" font-weight="700">{summary.total_entries}</text>
    <text x="28" y="148" fill="{theme['accent']}" font-size="24" font-family="{theme['font']}">条记录</text>
  </g>

  <g transform="translate(730, 350)">
    <rect width="390" height="180" rx="28" fill="{theme['panel_alt']}" />
    <text x="28" y="42" fill="{theme['muted']}" font-size="18" font-family="{theme['font']}">KEY SKILLS</text>
    <text x="28" y="92" fill="{theme['text']}" font-size="32" font-family="{theme['font']}" font-weight="700">{html.escape(" / ".join(summary.skills[:2]))}</text>
    <text x="28" y="132" fill="{theme['muted']}" font-size="24" font-family="{theme['font']}">{html.escape(" / ".join(summary.skills[2:4]))}</text>
  </g>

  {highlight_blocks}

  <g transform="translate(70, 520)">
    <rect width="510" height="420" rx="28" fill="{theme['panel_alt']}" />
    <text x="28" y="48" fill="{theme['text']}" font-size="30" font-family="{theme['font']}" font-weight="700">今日洞察</text>
    <text x="28" y="102" fill="{theme['muted']}" font-size="24" font-family="{theme['font']}">1. {html.escape(insight_lines[0])}</text>
    <text x="28" y="148" fill="{theme['muted']}" font-size="24" font-family="{theme['font']}">2. {html.escape(insight_lines[1] if len(insight_lines) > 1 else insight_lines[0])}</text>
  </g>

  <g transform="translate(620, 520)">
    <rect width="500" height="420" rx="28" fill="{theme['panel_alt']}" />
    <text x="28" y="48" fill="{theme['text']}" font-size="30" font-family="{theme['font']}" font-weight="700">下一步计划</text>
    <text x="28" y="102" fill="{theme['muted']}" font-size="24" font-family="{theme['font']}">1. {html.escape(plan_lines[0])}</text>
    <text x="28" y="148" fill="{theme['muted']}" font-size="24" font-family="{theme['font']}">2. {html.escape(plan_lines[1] if len(plan_lines) > 1 else plan_lines[0])}</text>
  </g>

  <g transform="translate(70, 980)">
    <rect width="1050" height="510" rx="28" fill="{theme['panel_alt']}" />
    <text x="28" y="52" fill="{theme['text']}" font-size="30" font-family="{theme['font']}" font-weight="700">活动时间线</text>
    {"".join(_build_timeline_svg(summary.entries, theme))}
  </g>
</svg>
"""


def _build_timeline_svg(entries: List[DailyLogEntry], theme: dict) -> List[str]:
    blocks = []
    for index, entry in enumerate(entries[:4]):
        y = 96 + index * 100
        blocks.append(
            f"""
    <circle cx="42" cy="{y - 8}" r="8" fill="{theme['accent']}" />
    <line x1="42" y1="{y}" x2="42" y2="{y + 72}" stroke="{theme['accent_2']}" stroke-width="2" opacity="0.6" />
    <text x="70" y="{y}" fill="{theme['text']}" font-size="24" font-family="{theme['font']}" font-weight="700">{html.escape(entry.skill_name)} · {entry.duration_minutes} 分钟</text>
    <text x="70" y="{y + 34}" fill="{theme['muted']}" font-size="22" font-family="{theme['font']}">{html.escape(entry.learning_content)}</text>
            """
        )
    return blocks


def _build_widget_html(summary: DailyReportSummary, theme: dict) -> str:
    payload = {
        "date": summary.date,
        "title": summary.title,
        "description": summary.description,
        "minutes": summary.total_minutes,
        "skills": summary.skills,
        "insights": summary.insights,
        "plans": summary.plans,
        "problems": summary.problems,
        "highlights": summary.highlights,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(summary.title)} - Interactive Widget</title>
  <style>
    :root {{
      --bg-start: {theme['bg_start']};
      --bg-end: {theme['bg_end']};
      --panel: {theme['panel']};
      --panel-alt: {theme['panel_alt']};
      --accent: {theme['accent']};
      --accent-2: {theme['accent_2']};
      --accent-3: {theme['accent_3']};
      --text: {theme['text']};
      --muted: {theme['muted']};
      --font: {theme['font']};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: var(--font);
      color: var(--text);
      background:
        radial-gradient(circle at top right, rgba(212,160,23,.18), transparent 28%),
        radial-gradient(circle at bottom left, rgba(85,124,62,.18), transparent 26%),
        linear-gradient(135deg, var(--bg-start), var(--bg-end));
      display: grid;
      place-items: center;
      padding: 24px;
    }}
    .widget {{
      width: min(100%, 980px);
      background: color-mix(in srgb, var(--panel) 94%, white 6%);
      border: 1px solid color-mix(in srgb, var(--accent) 36%, white 64%);
      border-radius: 28px;
      overflow: hidden;
      box-shadow: 0 24px 70px rgba(34, 20, 14, .18);
    }}
    .hero {{
      padding: 34px 34px 28px;
      border-bottom: 1px solid color-mix(in srgb, var(--accent-2) 24%, white 76%);
      background:
        linear-gradient(135deg, color-mix(in srgb, var(--panel-alt) 86%, white 14%), color-mix(in srgb, var(--panel) 92%, white 8%));
    }}
    .eyebrow {{
      color: var(--accent);
      letter-spacing: .14em;
      font-size: 12px;
      font-weight: 700;
    }}
    h1 {{
      margin: 14px 0 10px;
      font-size: clamp(34px, 4vw, 54px);
      line-height: 1.08;
    }}
    .desc {{
      color: var(--muted);
      font-size: 17px;
      line-height: 1.7;
      max-width: 60ch;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 20px;
    }}
    .chip {{
      padding: 10px 14px;
      background: color-mix(in srgb, var(--accent-2) 14%, white 86%);
      border: 1px solid color-mix(in srgb, var(--accent-2) 30%, white 70%);
      border-radius: 999px;
      color: var(--text);
      font-size: 14px;
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, .65fr);
      gap: 18px;
      align-items: start;
      margin-top: 24px;
    }}
    .hero-panel {{
      background: color-mix(in srgb, var(--panel) 90%, white 10%);
      border: 1px solid color-mix(in srgb, var(--accent) 18%, white 82%);
      border-radius: 20px;
      padding: 18px;
    }}
    .hero-panel h2 {{
      margin: 0 0 10px;
      font-size: 15px;
      color: var(--accent);
      letter-spacing: .08em;
    }}
    .hero-panel p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
      padding: 26px 34px 34px;
    }}
    .card {{
      background: color-mix(in srgb, var(--panel-alt) 82%, white 18%);
      border: 1px solid color-mix(in srgb, var(--accent-2) 18%, white 82%);
      border-radius: 20px;
      padding: 20px;
    }}
    .card h2 {{
      margin: 0 0 14px;
      font-size: 19px;
    }}
    .list {{
      display: grid;
      gap: 12px;
      color: var(--muted);
      line-height: 1.7;
    }}
    .timeline button {{
      width: 100%;
      text-align: left;
      background: color-mix(in srgb, var(--panel) 88%, white 12%);
      color: inherit;
      border: 1px solid color-mix(in srgb, var(--accent-3) 18%, white 82%);
      border-radius: 16px;
      padding: 14px 16px;
      margin-bottom: 12px;
      cursor: pointer;
    }}
    .timeline button.active {{
      background: color-mix(in srgb, var(--accent-3) 14%, white 86%);
      border-color: color-mix(in srgb, var(--accent-3) 48%, white 52%);
    }}
    .detail {{
      margin-top: 12px;
      padding: 16px;
      border-radius: 16px;
      background: color-mix(in srgb, var(--panel) 86%, white 14%);
      color: var(--muted);
      min-height: 116px;
      line-height: 1.7;
    }}
    .footer {{
      padding: 0 34px 30px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
    }}
    .footer strong {{
      color: var(--text);
    }}
    @media (max-width: 640px) {{
      body {{ padding: 12px; }}
      .hero, .grid, .footer {{ padding-left: 16px; padding-right: 16px; }}
      .hero-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <article class="widget">
    <section class="hero">
      <div class="eyebrow">{html.escape(theme['eyebrow'])}</div>
      <h1>{html.escape(summary.title)}</h1>
      <p class="desc">{html.escape(summary.description)}</p>
      <div class="meta">
        <span class="chip">业务日期 {summary.date}</span>
        <span class="chip">生成时间 {summary.generated_at}</span>
        <span class="chip">作者 {html.escape(summary.author)}</span>
        <span class="chip">来源 {html.escape(summary.source_name)}</span>
        <span class="chip">{summary.total_minutes} 分钟</span>
        <span class="chip">{len(summary.skills)} 个技能</span>
      </div>
      <div class="hero-grid">
        <section class="hero-panel">
          <h2>来源声明</h2>
          <p>{html.escape(summary.source_statement)}</p>
        </section>
        <section class="hero-panel">
          <h2>快照摘要</h2>
          <p>{html.escape("；".join(summary.highlights[:3]))}</p>
        </section>
      </div>
      {f'<div class="hero-panel" style="margin-top:18px;"><h2>用户备注</h2><p>{html.escape(summary.user_note)}</p></div>' if summary.user_note else ''}
    </section>
    <section class="grid">
      <div class="card">
        <h2>动态亮点</h2>
        <div class="list" id="highlights"></div>
      </div>
      <div class="card timeline">
        <h2>交互时间线</h2>
        <div id="timeline"></div>
        <div class="detail" id="detail">点击上方时间线卡片查看详情。</div>
      </div>
      <div class="card">
        <h2>明日动作</h2>
        <div class="list" id="plans"></div>
      </div>
    </section>
    <footer class="footer">
      <strong>作者</strong> {html.escape(summary.author)} · <strong>来源</strong> {html.escape(summary.source_name)}<br>
      {html.escape(summary.source_statement)}
    </footer>
  </article>
  <script>
    const data = {payload_json};
    const highlightRoot = document.getElementById("highlights");
    const timelineRoot = document.getElementById("timeline");
    const detailRoot = document.getElementById("detail");
    const planRoot = document.getElementById("plans");

    data.highlights.forEach((item) => {{
      const el = document.createElement("div");
      el.textContent = item;
      highlightRoot.appendChild(el);
    }});

    data.plans.forEach((item) => {{
      const el = document.createElement("div");
      el.textContent = item;
      planRoot.appendChild(el);
    }});

    data.skills.forEach((skill, index) => {{
      const button = document.createElement("button");
      button.innerHTML = `<strong>${{skill}}</strong><br><span>${{data.insights[index] || data.description}}</span>`;
      button.addEventListener("click", () => {{
        timelineRoot.querySelectorAll("button").forEach((btn) => btn.classList.remove("active"));
        button.classList.add("active");
        detailRoot.innerHTML = `
          <strong>${{skill}}</strong><br>
          今日洞察: ${{data.insights[index] || "继续提炼中"}}<br>
          阻塞问题: ${{data.problems[index] || "无显著阻塞"}}<br>
          下一步: ${{data.plans[index] || "继续推进"}}
        `;
      }});
      if (index === 0) {{
        button.classList.add("active");
        detailRoot.innerHTML = `
          <strong>${{skill}}</strong><br>
          今日洞察: ${{data.insights[index] || "继续提炼中"}}<br>
          阻塞问题: ${{data.problems[index] || "无显著阻塞"}}<br>
          下一步: ${{data.plans[index] || "继续推进"}}
        `;
      }}
      timelineRoot.appendChild(button);
    }});
  </script>
</body>
</html>
"""


def _build_poster_html(summary: DailyReportSummary, theme: dict, poster_png_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(summary.title)} - Poster Template</title>
  <style>
    :root {{
      --bg-start: {theme['bg_start']};
      --bg-end: {theme['bg_end']};
      --paper: {theme['panel']};
      --panel: {theme['panel_alt']};
      --maple: {theme['accent']};
      --gold: {theme['accent_2']};
      --green: {theme['accent_3']};
      --text: {theme['text']};
      --muted: {theme['muted']};
      --font: {theme['font']};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 28px;
      font-family: var(--font);
      background:
        radial-gradient(circle at top right, color-mix(in srgb, var(--gold) 24%, transparent) 0, transparent 38%),
        radial-gradient(circle at bottom left, color-mix(in srgb, var(--green) 18%, transparent) 0, transparent 34%),
        linear-gradient(140deg, var(--bg-start), var(--bg-end));
    }}
    .poster {{
      width: min(100%, 1120px);
      min-height: 1480px;
      background: linear-gradient(180deg, color-mix(in srgb, var(--paper) 96%, white 4%), color-mix(in srgb, var(--panel) 92%, white 8%));
      color: var(--text);
      border-radius: 32px;
      overflow: hidden;
      box-shadow: 0 34px 90px rgba(34, 20, 14, .22);
      border: 1px solid color-mix(in srgb, var(--maple) 24%, white 76%);
      display: grid;
      grid-template-rows: auto auto 1fr auto;
    }}
    .header {{
      padding: 36px 42px 24px;
      background:
        linear-gradient(135deg, color-mix(in srgb, var(--maple) 16%, var(--paper) 84%), color-mix(in srgb, var(--gold) 16%, var(--paper) 84%));
    }}
    .eyebrow {{
      font-size: 13px;
      letter-spacing: .16em;
      color: var(--maple);
      font-weight: 700;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 14px 0 10px;
      font-size: 66px;
      line-height: 1.05;
    }}
    .subtitle {{
      font-size: 22px;
      line-height: 1.7;
      color: var(--muted);
      max-width: 52ch;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 20px;
    }}
    .badge {{
      border-radius: 999px;
      padding: 10px 14px;
      background: rgba(255,255,255,.58);
      border: 1px solid rgba(164,54,40,.16);
      font-size: 14px;
    }}
    .overview {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
      padding: 24px 42px 0;
    }}
    .stat {{
      background: rgba(255,255,255,.74);
      border: 1px solid rgba(212,160,23,.18);
      border-radius: 22px;
      padding: 22px;
    }}
    .stat-label {{
      font-size: 14px;
      letter-spacing: .08em;
      color: var(--muted);
    }}
    .stat-value {{
      margin-top: 12px;
      font-size: 52px;
      font-weight: 700;
    }}
    .content {{
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 18px;
      padding: 18px 42px 28px;
    }}
    .panel {{
      background: rgba(255,255,255,.74);
      border: 1px solid rgba(164,54,40,.14);
      border-radius: 24px;
      padding: 22px;
    }}
    .panel h2 {{
      margin: 0 0 14px;
      color: var(--maple);
      font-size: 22px;
    }}
    .list {{
      display: grid;
      gap: 12px;
      line-height: 1.7;
      color: var(--muted);
      font-size: 18px;
    }}
    .footer {{
      padding: 0 42px 36px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.8;
    }}
    .preview {{
      margin-top: 16px;
      border-radius: 18px;
      overflow: hidden;
      border: 1px solid rgba(164,54,40,.12);
    }}
    .preview img {{
      display: block;
      width: 100%;
    }}
    @media (max-width: 960px) {{
      .overview, .content {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 48px; }}
    }}
  </style>
</head>
<body>
  <main class="poster">
    <section class="header">
      <div class="eyebrow">{html.escape(theme['tagline'])}</div>
      <h1>{html.escape(summary.title)}</h1>
      <div class="subtitle">{html.escape(summary.description)}</div>
      <div class="meta">
        <span class="badge">业务日期 {summary.date}</span>
        <span class="badge">生成时间 {summary.generated_at}</span>
        <span class="badge">作者 {html.escape(summary.author)}</span>
        <span class="badge">来源 {html.escape(summary.source_name)}</span>
      </div>
    </section>
    <section class="overview">
      <article class="stat">
        <div class="stat-label">TOTAL MINUTES</div>
        <div class="stat-value">{summary.total_minutes}</div>
      </article>
      <article class="stat">
        <div class="stat-label">ENTRY COUNT</div>
        <div class="stat-value">{summary.total_entries}</div>
      </article>
      <article class="stat">
        <div class="stat-label">TOP SKILLS</div>
        <div class="stat-value" style="font-size:28px;">{html.escape(" / ".join(summary.skills[:2]))}</div>
      </article>
    </section>
    <section class="content">
      <article class="panel">
        <h2>今日重点</h2>
        <div class="list">{"".join(f"<div>{html.escape(item)}</div>" for item in summary.highlights[:4])}</div>
        <h2 style="margin-top:24px;">来源声明</h2>
        <div class="list"><div>{html.escape(summary.source_statement)}</div></div>
        {f'<h2 style="margin-top:24px;">用户备注</h2><div class="list"><div>{html.escape(summary.user_note)}</div></div>' if summary.user_note else ''}
      </article>
      <article class="panel">
        <h2>洞察与计划</h2>
        <div class="list">
          {"".join(f"<div>洞察：{html.escape(item)}</div>" for item in (summary.insights[:2] or ['暂无洞察']))}
          {"".join(f"<div>计划：{html.escape(item)}</div>" for item in (summary.plans[:2] or ['继续推进']))}
        </div>
        <div class="preview">
          <img src="{html.escape(poster_png_name)}" alt="{html.escape(summary.title)} PNG 预览" />
        </div>
      </article>
    </section>
    <footer class="footer">
      作者：{html.escape(summary.author)} · 来源：{html.escape(summary.source_name)}<br>
      {html.escape(summary.source_statement)}
    </footer>
  </main>
</body>
</html>
"""


def _build_article_html(summary: DailyReportSummary, theme: dict, poster_svg_name: str, poster_png_name: str, widget_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(summary.title)} - Article Embed</title>
  <style>
    body {{
      margin: 0;
      font-family: {theme['font']};
      background:
        radial-gradient(circle at top right, color-mix(in srgb, {theme['accent_2']} 20%, transparent) 0, transparent 36%),
        linear-gradient(180deg, #fbf6ef, #f3ede4);
      color: {theme['text']};
      padding: 28px;
    }}
    .article {{
      max-width: 860px;
      margin: 0 auto;
      background: rgba(255,255,255,.92);
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 24px 56px rgba(46, 24, 14, .12);
      border: 1px solid rgba(164,54,40,.12);
    }}
    .cover {{
      width: 100%;
      display: block;
      background: linear-gradient(135deg, {theme['bg_start']}, {theme['bg_end']});
    }}
    .body {{
      padding: 32px;
      line-height: 1.75;
    }}
    .eyebrow {{
      color: {theme['accent']};
      font-size: 12px;
      letter-spacing: .14em;
      text-transform: uppercase;
      font-weight: 700;
    }}
    h1 {{
      margin: 12px 0;
      font-size: clamp(36px, 4vw, 52px);
      line-height: 1.1;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 18px 0 20px;
    }}
    .chip {{
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(212,160,23,.12);
      border: 1px solid rgba(212,160,23,.24);
      font-size: 14px;
      color: {theme['text']};
    }}
    .note {{
      margin: 18px 0;
      padding: 16px 18px;
      border-left: 4px solid {theme['accent_2']};
      background: rgba(255,241,220,.76);
      border-radius: 10px;
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 18px;
      margin-top: 22px;
    }}
    .panel {{
      background: rgba(248,239,223,.68);
      border: 1px solid rgba(164,54,40,.1);
      border-radius: 18px;
      padding: 18px;
    }}
    .panel h2 {{
      margin: 0 0 10px;
      color: {theme['accent']};
      font-size: 18px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 20px;
    }}
    .button {{
      text-decoration: none;
      padding: 12px 18px;
      border-radius: 999px;
      color: white;
      background: linear-gradient(135deg, {theme['accent']}, {theme['accent_2']});
    }}
    code {{
      background: #eef3f9;
      padding: 2px 6px;
      border-radius: 6px;
    }}
    .footer {{
      margin-top: 22px;
      padding-top: 18px;
      border-top: 1px solid rgba(164,54,40,.12);
      color: {theme['muted']};
      font-size: 14px;
      line-height: 1.8;
    }}
    @media (max-width: 860px) {{
      .split {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <article class="article">
    <img class="cover" src="{html.escape(poster_png_name)}" alt="{html.escape(summary.title)} 海报" />
    <div class="body">
      <div class="eyebrow">{html.escape(theme['eyebrow'])}</div>
      <h1>{html.escape(summary.title)}</h1>
      <p>{html.escape(summary.description)}</p>
      <div class="meta">
        <span class="chip">业务日期 {summary.date}</span>
        <span class="chip">生成时间 {summary.generated_at}</span>
        <span class="chip">作者 {html.escape(summary.author)}</span>
        <span class="chip">来源 {html.escape(summary.source_name)}</span>
      </div>
      <div class="note">
        形式一：图片版日报。适合公众号正文直接插图、封面配图、朋友圈长图。
      </div>
      <div class="note">
        形式二：交互版日报。适合 H5 页面、公众号原文链接跳转页、企业内部知识库嵌入。
      </div>
      <div class="split">
        <section class="panel">
          <h2>核心摘要</h2>
          <p>{html.escape("；".join(summary.highlights[:4]))}</p>
          <h2 style="margin-top:18px;">来源声明</h2>
          <p>{html.escape(summary.source_statement)}</p>
          {f'<h2 style="margin-top:18px;">用户备注</h2><p>{html.escape(summary.user_note)}</p>' if summary.user_note else ''}
        </section>
        <section class="panel">
          <h2>嵌入建议</h2>
          <p>公众号正文不支持任意前端脚本直接运行，稳妥做法是正文里放 PNG 图片版，再通过按钮或阅读原文跳转到交互版页面。</p>
          <p>如果投放在企业知识库、官网文章页、H5 容器，则优先嵌入交互版组件。</p>
        </section>
      </div>
      <div class="actions">
        <a class="button" href="{html.escape(widget_name)}">打开交互版日报</a>
        <a class="button" href="{html.escape(poster_png_name)}">查看 PNG 日报</a>
        <a class="button" href="{html.escape(poster_svg_name)}">查看 SVG 日报</a>
      </div>
      <div class="footer">
        作者：{html.escape(summary.author)} · 来源：{html.escape(summary.source_name)}<br>
        {html.escape(summary.source_statement)}<br>
        交互组件路径：<code>{html.escape(widget_name)}</code>
      </div>
    </div>
  </article>
</body>
</html>
"""


def _build_theme_gallery_html(date: str, bundles: List[ThemePreviewBundle]) -> str:
    cards = []
    for bundle in bundles:
        cards.append(
            f"""
      <article class="card">
        <div class="card-meta">
          <div>
            <div class="eyebrow">{html.escape(bundle.theme)}</div>
            <h2>{html.escape(bundle.name)}</h2>
          </div>
          <div class="swatches">
            <span class="swatch" style="background:{bundle.accent}"></span>
            <span class="swatch" style="background:{bundle.accent_2}"></span>
            <span class="swatch" style="background:{bundle.accent_3}"></span>
          </div>
        </div>
        <p>{html.escape(bundle.description)}</p>
        <a class="preview" href="{html.escape(bundle.poster_html_path.name)}">
          <img src="{html.escape(bundle.poster_png_path.name)}" alt="{html.escape(bundle.name)} 预览" />
        </a>
        <div class="links">
          <a href="{html.escape(bundle.poster_html_path.name)}">截图底板</a>
          <a href="{html.escape(bundle.widget_path.name)}">交互版</a>
          <a href="{html.escape(bundle.article_path.name)}">文章页</a>
        </div>
      </article>
"""
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Daily Report Themes - {html.escape(date)}</title>
  <style>
    :root {{
      --bg: #f5efe7;
      --panel: rgba(255,255,255,.88);
      --text: #231815;
      --muted: #6f5849;
      --maple: #b63a2b;
      --gold: #d89b1d;
      --green: #557c3e;
      --line: rgba(182,58,43,.12);
      --font: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px;
      font-family: var(--font);
      color: var(--text);
      background:
        radial-gradient(circle at top right, rgba(216,155,29,.16), transparent 34%),
        radial-gradient(circle at bottom left, rgba(85,124,62,.12), transparent 28%),
        linear-gradient(180deg, #f7f1e7, #efe4d4);
    }}
    .shell {{
      max-width: 1320px;
      margin: 0 auto;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(182,58,43,.1), rgba(216,155,29,.12));
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px 30px;
      box-shadow: 0 20px 48px rgba(46, 24, 14, .08);
    }}
    .eyebrow {{
      color: var(--maple);
      font-size: 12px;
      letter-spacing: .14em;
      text-transform: uppercase;
      font-weight: 700;
    }}
    h1 {{
      margin: 10px 0 8px;
      font-size: clamp(34px, 4vw, 56px);
      line-height: 1.08;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.7;
      max-width: 64ch;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 18px;
      margin-top: 22px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 20px;
      box-shadow: 0 16px 40px rgba(46, 24, 14, .08);
    }}
    .card-meta {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 16px;
    }}
    .card h2 {{
      margin: 6px 0 0;
      font-size: 24px;
    }}
    .card p {{
      color: var(--muted);
      line-height: 1.7;
      min-height: 48px;
    }}
    .swatches {{
      display: flex;
      gap: 8px;
      padding-top: 6px;
    }}
    .swatch {{
      width: 16px;
      height: 16px;
      border-radius: 999px;
      border: 1px solid rgba(0,0,0,.08);
    }}
    .preview {{
      display: block;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid var(--line);
      background: white;
    }}
    .preview img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .links a {{
      text-decoration: none;
      color: white;
      background: linear-gradient(135deg, var(--maple), var(--gold));
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Theme Gallery</div>
      <h1>日报主题预览</h1>
      <p>业务日期 {html.escape(date)}。每个主题都包含海报截图底板、交互版组件和文章页，点击卡片可直接打开对应预览。</p>
    </section>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    if not text:
        return [""]
    lines: List[str] = []
    current = ""
    for char in text:
        candidate = current + char
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_text_block(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, *, font, fill, max_width: int, line_gap: int = 10) -> int:
    lines = _wrap_text(text, font, max_width, draw)
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += draw.textbbox((x, cursor), line, font=font)[3] - draw.textbbox((x, cursor), line, font=font)[1] + line_gap
    return cursor


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _build_gradient(size: tuple[int, int], start: str, end: str) -> Image.Image:
    width, height = size
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    gradient = Image.new("RGB", size, start_rgb)
    draw = ImageDraw.Draw(gradient)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(start_rgb[i] * (1 - ratio) + end_rgb[i] * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    return gradient


def _build_poster_png(summary: DailyReportSummary, theme: dict, output_path: Path) -> None:
    width, height = 1200, 1600
    image = _build_gradient((width, height), theme["bg_start"], theme["bg_end"]).convert("RGBA")
    draw = ImageDraw.Draw(image)

    panel = _hex_to_rgb(theme["panel"]) + (225,)
    panel_alt = _hex_to_rgb(theme["panel_alt"]) + (245,)
    accent = _hex_to_rgb(theme["accent"])
    accent_2 = _hex_to_rgb(theme["accent_2"])
    text = _hex_to_rgb(theme["text"])
    muted = _hex_to_rgb(theme["muted"])

    # Ambient shapes
    draw.ellipse((700, 40, 1160, 500), fill=accent_2 + (35,))
    draw.ellipse((40, 1020, 420, 1400), fill=accent + (24,))

    draw.rounded_rectangle((40, 40, 1160, 1560), radius=36, fill=panel, outline=accent_2 + (120,), width=2)

    eyebrow_font = _load_font(24, bold=True)
    title_font = _load_font(72, bold=True)
    body_font = _load_font(30)
    meta_font = _load_font(24)
    stat_font = _load_font(64, bold=True)
    card_title_font = _load_font(30, bold=True)
    line_font = _load_font(24)
    small_font = _load_font(18)

    draw.text((70, 86), theme["tagline"], font=eyebrow_font, fill=accent)
    draw.text((70, 165), summary.title, font=title_font, fill=text)
    _draw_text_block(draw, summary.description, 70, 250, font=body_font, fill=muted, max_width=980, line_gap=8)

    meta_text = f"{summary.date}  ·  {' / '.join(summary.skills[:3])}  ·  心情 {MoodEmoji.from_int(summary.mood) if summary.mood else '·'}"
    draw.text((70, 322), meta_text, font=meta_font, fill=muted)

    stat_boxes = [
        ((70, 350, 370, 530), "FOCUS TIME", str(summary.total_minutes), "分钟"),
        ((400, 350, 700, 530), "ENTRY COUNT", str(summary.total_entries), "条记录"),
        ((730, 350, 1120, 530), "KEY SKILLS", " / ".join(summary.skills[:2]) or "General", " / ".join(summary.skills[2:4])),
    ]
    for left, label, value, suffix in stat_boxes:
        draw.rounded_rectangle(left, radius=28, fill=panel_alt)
        draw.text((left[0] + 28, left[1] + 24), label, font=small_font, fill=muted)
        draw.text((left[0] + 28, left[1] + 78), value, font=stat_font if label != "KEY SKILLS" else _load_font(34, bold=True), fill=text)
        draw.text((left[0] + 28, left[1] + 136), suffix, font=meta_font, fill=accent)

    for index, text_value in enumerate(summary.highlights[:3]):
        x = 40 + index * 220
        draw.rounded_rectangle((x, 590, x + 190, 678), radius=18, fill=panel_alt)
        draw.text((x + 18, 610), f"HIGHLIGHT {index + 1}", font=small_font, fill=accent)
        _draw_text_block(draw, text_value, x + 18, 634, font=_load_font(18), fill=text, max_width=150, line_gap=4)

    draw.rounded_rectangle((70, 720, 580, 1140), radius=28, fill=panel_alt)
    draw.text((98, 748), "今日洞察", font=card_title_font, fill=text)
    for idx, line in enumerate((summary.insights[:2] or ["暂无心得，等待下一次记录刷新。"])):
        _draw_text_block(draw, f"{idx + 1}. {line}", 98, 810 + idx * 86, font=line_font, fill=muted, max_width=430, line_gap=6)

    draw.rounded_rectangle((620, 720, 1120, 1140), radius=28, fill=panel_alt)
    draw.text((648, 748), "下一步计划", font=card_title_font, fill=text)
    for idx, line in enumerate((summary.plans[:2] or ["继续推进核心任务。"])):
        _draw_text_block(draw, f"{idx + 1}. {line}", 648, 810 + idx * 86, font=line_font, fill=muted, max_width=430, line_gap=6)

    draw.rounded_rectangle((70, 1180, 1120, 1490), radius=28, fill=panel_alt)
    draw.text((98, 1208), "活动时间线", font=card_title_font, fill=text)
    for idx, entry in enumerate(summary.entries[:4]):
        y = 1280 + idx * 58
        draw.ellipse((100, y - 7, 114, y + 7), fill=accent)
        draw.line((107, y + 10, 107, y + 48), fill=accent_2, width=3)
        draw.text((136, y - 18), f"{entry.skill_name} · {entry.duration_minutes} 分钟", font=line_font, fill=text)
        _draw_text_block(draw, entry.learning_content, 136, y + 12, font=_load_font(20), fill=muted, max_width=900, line_gap=4)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


# ── Registry adapter ──

def register_daily_adapter(registry) -> None:
    """Register the daily report renderer with the template registry.

    This adapter bridges the registry's generic renderer interface with
    the existing daily_renderer module functions.
    """
    from src.templates.registry import RenderResult

    def _daily_adapter(
        manifest,
        input_data: dict,
        theme,
        output_dir: str,
    ) -> "RenderResult":
        """Adapter: registry → daily_renderer."""
        from src.storage.factory import StorageBackend

        # Get logs for the given date from storage
        date = input_data.get("date", "")
        storage = StorageBackend()
        logs = storage.daily_log_storage().get_all()
        selected_logs = [log for log in logs if log.date == date]

        rendered = render_daily_report(
            selected_logs,
            date=date,
            theme=theme.id,
            title=input_data.get("title", ""),
            description=input_data.get("description", ""),
            author=input_data.get("author", ""),
            source_name=input_data.get("source_name", ""),
            source_statement=input_data.get("source_statement", ""),
            user_note=input_data.get("user_note", ""),
            output_dir=output_dir,
        )
        return RenderResult(
            template_id=manifest.id,
            theme_id=theme.id,
            output_dir=output_dir,
            artifacts={
                "poster_png": str(rendered.poster_png_path),
                "poster_html": str(rendered.poster_html_path),
                "widget": str(rendered.widget_path),
                "article": str(rendered.article_path),
            },
        )

    registry.register_renderer("daily_renderer", _daily_adapter)

