"""WeChat-style article template rendering."""

from __future__ import annotations

import html
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFilter, ImageFont


BlockType = Literal["paragraph", "image", "linked_image"]


@dataclass
class ArticleBlock:
    type: BlockType
    text: str = ""
    image_path: Path | None = None
    link: str | None = None


@dataclass
class ArticleDocument:
    title: str
    source_path: Path
    blocks: list[ArticleBlock]


@dataclass
class ArticleRenderMeta:
    summary: str
    author: str
    source_name: str
    source_statement: str
    publish_date: str


@dataclass
class WechatTheme:
    key: str
    name: str
    description: str
    shell_bg: str
    page_bg: str
    card_bg: str
    accent: str
    accent_soft: str
    text: str
    muted: str
    line: str
    shadow: str


@dataclass
class RenderedWechatArticle:
    title: str
    theme: str
    preview_html_path: Path
    wechat_html_path: Path
    wechat_body_path: Path
    wechat_paste_path: Path
    wechat_copyboard_path: Path
    cover_png_path: Path
    article_header_png_path: Path
    article_long_png_path: Path
    assets_dir: Path
    image_count: int



WECHAT_TOKEN_MAP = {
    "color.shell_bg": "shell_bg",
    "color.page_bg": "page_bg",
    "color.card_bg": "card_bg",
    "color.accent": "accent",
    "color.accent_soft": "accent_soft",
    "color.text": "text",
    "color.muted": "muted",
    "color.line": "line",
    "shadow.card": "shadow",
}

# ── Lazy singleton registry reference ──
_WECHAT_REGISTRY = None


def _get_wechat_registry():
    """Get or create the shared template registry singleton."""
    global _WECHAT_REGISTRY
    if _WECHAT_REGISTRY is None:
        from src.templates.registry import TemplateRegistry
        _WECHAT_REGISTRY = TemplateRegistry()
        _WECHAT_REGISTRY.load_all()
    return _WECHAT_REGISTRY


WECHAT_TEMPLATE_ID = "wechat.wallpaper.gallery"


def _resolve_wechat_theme(theme_key: str) -> "WechatTheme":
    """Resolve a theme key to a WechatTheme using the registry."""
    theme_manifest = _get_wechat_registry().get_theme(WECHAT_TEMPLATE_ID, theme_key)
    if theme_manifest is None:
        raise ValueError(f"Unknown wechat theme: {theme_key}")
    flat = theme_manifest.to_flat_dict(WECHAT_TOKEN_MAP)
    return WechatTheme(
        key=theme_key,
        name=flat.get("name", theme_key),
        description=flat.get("description", ""),
        shell_bg=flat.get("shell_bg", "#f7f4ef"),
        page_bg=flat.get("page_bg", "linear-gradient(180deg, #f8f5ef 0%, #efe7dc 100%)"),
        card_bg=flat.get("card_bg", "#ffffff"),
        accent=flat.get("accent", "#7d6f63"),
        accent_soft=flat.get("accent_soft", "#ece4d8"),
        text=flat.get("text", "#2e2722"),
        muted=flat.get("muted", "#8f8378"),
        line=flat.get("line", "#e5ddd1"),
        shadow=flat.get("shadow", "0 18px 42px rgba(48, 38, 30, 0.12)"),
    )

IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")
LINKED_IMAGE_RE = re.compile(r"\[!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\]\((?P<href>[^)]+)\)")
HEADING_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")


def list_wechat_themes() -> list[dict[str, str]]:
    registry = _get_wechat_registry()
    themes = registry.list_theme_manifests(WECHAT_TEMPLATE_ID)
    return [
        {
            "key": theme.id,
            "name": theme.name,
            "description": theme.description or "",
            "accent": theme.tokens.get("color.accent", "#888"),
        }
        for theme in themes
    ]


def render_wechat_article(
    markdown_path: str | Path,
    *,
    theme: str = "mist-gallery",
    output_dir: str = "data/wechat",
    summary: str | None = None,
    author: str | None = None,
    source_name: str | None = None,
    source_statement: str | None = None,
    publish_date: str | None = None,
) -> RenderedWechatArticle:
    source_path = Path(markdown_path).expanduser().resolve()
    document = parse_article_markdown(source_path)
    theme_spec = _theme(theme)
    render_meta = _build_render_meta(
        document,
        summary=summary,
        author=author,
        source_name=source_name,
        source_statement=source_statement,
        publish_date=publish_date,
    )

    slug = _slugify(source_path.stem or document.title or "wechat-article")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    article_dir = root / f"{slug}-{theme_spec.key}"
    article_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = article_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    image_mapping = _copy_images(document, assets_dir)
    preview_html = _build_preview_html(document, theme_spec, image_mapping, render_meta)
    wechat_body = _build_wechat_body(document, theme_spec, image_mapping, render_meta, paste_optimized=False)
    wechat_paste = _build_wechat_body(document, theme_spec, image_mapping, render_meta, paste_optimized=True)
    wechat_html = _wrap_html_document(document.title, theme_spec.page_bg, wechat_body)

    preview_html_path = article_dir / "preview.html"
    wechat_html_path = article_dir / "wechat-safe.html"
    wechat_body_path = article_dir / "wechat-body.html"
    wechat_paste_path = article_dir / "wechat-paste.html"
    wechat_copyboard_path = article_dir / "wechat-copyboard.html"
    cover_png_path = article_dir / "cover.png"
    article_header_png_path = article_dir / "article-header.png"
    article_long_png_path = article_dir / "article-long.png"

    preview_html_path.write_text(preview_html, encoding="utf-8")
    wechat_html_path.write_text(wechat_html, encoding="utf-8")
    wechat_body_path.write_text(wechat_body, encoding="utf-8")
    wechat_paste_path.write_text(wechat_paste, encoding="utf-8")
    wechat_copyboard_path.write_text(
        _build_copyboard_html(document.title, theme_spec, wechat_paste, render_meta),
        encoding="utf-8",
    )
    _build_cover_png(document, theme_spec, image_mapping, render_meta, cover_png_path)
    _build_article_header_png(document, theme_spec, image_mapping, render_meta, article_header_png_path)
    _build_article_long_png(document, theme_spec, image_mapping, render_meta, article_long_png_path)

    return RenderedWechatArticle(
        title=document.title,
        theme=theme_spec.key,
        preview_html_path=preview_html_path,
        wechat_html_path=wechat_html_path,
        wechat_body_path=wechat_body_path,
        wechat_paste_path=wechat_paste_path,
        wechat_copyboard_path=wechat_copyboard_path,
        cover_png_path=cover_png_path,
        article_header_png_path=article_header_png_path,
        article_long_png_path=article_long_png_path,
        assets_dir=assets_dir,
        image_count=len(image_mapping),
    )


def parse_article_markdown(markdown_path: str | Path) -> ArticleDocument:
    path = Path(markdown_path)
    text = _read_text_with_fallback(path)
    initial_title = _normalize_display_text(path.stem)
    title = initial_title
    body_lines: list[str] = []

    for line in text.splitlines():
        if not line.strip() and not body_lines:
            continue
        heading = HEADING_RE.match(line.strip())
        if heading and title == initial_title:
            title = _normalize_display_text(heading.group("title").strip())
            continue
        body_lines.append(line.rstrip())

    blocks: list[ArticleBlock] = []
    for raw_block in re.split(r"\n\s*\n", "\n".join(body_lines).strip()):
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
        if not lines:
            continue

        if len(lines) == 1:
            linked_image = LINKED_IMAGE_RE.fullmatch(lines[0])
            if linked_image:
                blocks.append(
                    ArticleBlock(
                        type="linked_image",
                        image_path=(path.parent / linked_image.group("src")).resolve(),
                        link=linked_image.group("href").strip(),
                    )
                )
                continue

            image = IMAGE_RE.fullmatch(lines[0])
            if image:
                blocks.append(
                    ArticleBlock(
                        type="image",
                        image_path=(path.parent / image.group("src")).resolve(),
                    )
                )
                continue

        blocks.append(ArticleBlock(type="paragraph", text=" ".join(lines).strip()))

    if not blocks:
        raise ValueError(f"No renderable blocks found in {path}")

    return ArticleDocument(title=title, source_path=path.resolve(), blocks=blocks)


def _build_render_meta(
    document: ArticleDocument,
    *,
    summary: str | None,
    author: str | None,
    source_name: str | None,
    source_statement: str | None,
    publish_date: str | None,
) -> ArticleRenderMeta:
    normalized_summary = _normalize_display_text(summary) if summary else _infer_summary(document)
    normalized_author = _normalize_display_text(author) if author else "Skills Workflow"
    normalized_source_name = _normalize_display_text(source_name) if source_name else "Skills Platform"
    normalized_publish_date = _normalize_display_text(publish_date) if publish_date else date.today().isoformat()
    normalized_source_statement = (
        _normalize_display_text(source_statement)
        if source_statement
        else f"内容整理自 {normalized_source_name}，由 {normalized_author} 于 {normalized_publish_date} 导出。"
    )
    return ArticleRenderMeta(
        summary=normalized_summary,
        author=normalized_author,
        source_name=normalized_source_name,
        source_statement=normalized_source_statement,
        publish_date=normalized_publish_date,
    )


def _theme(theme_key: str) -> WechatTheme:
    return _resolve_wechat_theme(theme_key)


def _read_text_with_fallback(path: Path) -> str:
    encodings = ("utf-8", "utf-8-sig", "gb18030")
    last_error: UnicodeDecodeError | None = None
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return path.read_text()


def _normalize_display_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "wechat-article"


def _copy_images(document: ArticleDocument, assets_dir: Path) -> dict[Path, str]:
    mapping: dict[Path, str] = {}
    used_names: set[str] = set()

    for block in document.blocks:
        if not block.image_path:
            continue
        source = block.image_path
        if not source.exists():
            raise FileNotFoundError(f"Image not found: {source}")

        stem = _slugify(source.stem) or "image"
        suffix = source.suffix.lower() or ".png"
        candidate = f"{stem}{suffix}"
        counter = 1
        while candidate in used_names:
            counter += 1
            candidate = f"{stem}-{counter}{suffix}"
        used_names.add(candidate)

        destination = assets_dir / candidate
        shutil.copy2(source, destination)
        mapping[source] = f"assets/{candidate}"

    return mapping


def _group_blocks(document: ArticleDocument) -> list[tuple[str, list[ArticleBlock]]]:
    groups: list[tuple[str, list[ArticleBlock]]] = []
    current_images: list[ArticleBlock] = []

    def flush_images() -> None:
        nonlocal current_images
        if current_images:
            groups.append(("gallery", current_images))
            current_images = []

    for block in document.blocks:
        if block.type == "image":
            current_images.append(block)
            continue

        flush_images()
        if block.type == "linked_image":
            groups.append(("cta", [block]))
        else:
            groups.append(("paragraph", [block]))

    flush_images()
    return groups


def _extract_quotes(text: str) -> list[str]:
    quotes = [item.strip() for item in re.findall(r"“([^”]+)”", text) if item.strip()]
    return quotes if len(quotes) >= 3 else []


def _infer_summary(document: ArticleDocument) -> str:
    for block in document.blocks:
        if block.type == "paragraph" and block.text.strip():
            text = _normalize_display_text(block.text)
            return text[:78] + "..." if len(text) > 78 else text
    return document.title


def _render_intro_panel(text: str, theme: WechatTheme) -> str:
    quotes = _extract_quotes(text)
    if quotes:
        items = "".join(
            f'<p style="margin:0 0 10px;color:{theme.muted};font-size:13px;line-height:2;">“{html.escape(item)}”</p>'
            for item in quotes
        )
        return (
            f'<section style="margin:0 0 18px;padding:22px 20px;background:{theme.card_bg};'
            f'border:1px solid {theme.line};border-radius:16px;box-shadow:{theme.shadow};">'
            f'<div style="margin:0 0 12px;color:{theme.accent};font-size:12px;letter-spacing:0.18em;'
            f'text-transform:uppercase;">Quote Selection</div>{items}</section>'
        )

    return (
        f'<section style="margin:0 0 18px;padding:22px 20px;background:{theme.card_bg};'
        f'border:1px solid {theme.line};border-radius:16px;box-shadow:{theme.shadow};">'
        f'<p style="margin:0;color:{theme.muted};font-size:14px;line-height:1.9;text-align:justify;">'
        f"{html.escape(text)}</p></section>"
    )


def _build_ambient_markup(theme: WechatTheme) -> str:
    shards = [
        {"top": "10%", "left": "6%", "width": "72px", "height": "72px", "--delay": "0s", "--duration": "15s", "--rotation": "-12deg"},
        {"top": "18%", "right": "8%", "width": "124px", "height": "46px", "--delay": "2.5s", "--duration": "18s", "--rotation": "14deg"},
        {"top": "42%", "left": "4%", "width": "92px", "height": "30px", "--delay": "1.2s", "--duration": "16s", "--rotation": "18deg"},
        {"top": "56%", "right": "6%", "width": "88px", "height": "88px", "--delay": "4s", "--duration": "20s", "--rotation": "-8deg"},
        {"bottom": "14%", "left": "12%", "width": "140px", "height": "34px", "--delay": "3.1s", "--duration": "19s", "--rotation": "-16deg"},
        {"bottom": "10%", "right": "14%", "width": "64px", "height": "64px", "--delay": "5.4s", "--duration": "17s", "--rotation": "10deg"},
    ]
    shard_html = "".join(
        '<span class="shard" style="'
        + ";".join(f"{key}:{value}" for key, value in shard.items())
        + f';border-color:{theme.line};background:{theme.card_bg};"></span>'
        for shard in shards
    )
    return (
        '<div class="ambient ambient-grid"></div>'
        '<div class="ambient ambient-beam"></div>'
        f'<div class="ambient ambient-shards">{shard_html}</div>'
    )


def _build_ambient_styles(*, include_canvas: bool = False) -> str:
    canvas_styles = """
    .canvas {
      position: relative;
      overflow: hidden;
    }
    .canvas::before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.18), transparent 28%, transparent 72%, rgba(255,255,255,0.12)),
        repeating-linear-gradient(90deg, rgba(125,111,99,0.03) 0 1px, transparent 1px 24px);
      animation: canvasShimmer 14s linear infinite;
      pointer-events: none;
    }
    .canvas > * {
      position: relative;
      z-index: 1;
    }
""" if include_canvas else ""

    shimmer_keyframes = """
    @keyframes canvasShimmer {
      0% { transform: translateX(-8%); opacity: 0.72; }
      50% { transform: translateX(6%); opacity: 1; }
      100% { transform: translateX(-8%); opacity: 0.72; }
    }
""" if include_canvas else ""

    return f"""
    .ambient {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
    }}
    .ambient-grid {{
      opacity: 0.42;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.22) 1px, transparent 1px) 0 0 / 64px 64px,
        linear-gradient(rgba(125,111,99,0.07) 1px, transparent 1px) 0 0 / 64px 64px,
        repeating-linear-gradient(120deg, rgba(255,255,255,0.06) 0 18px, transparent 18px 42px);
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.9), rgba(0,0,0,0.18));
      animation: gridDrift 26s linear infinite;
    }}
    .ambient-beam::before,
    .ambient-beam::after {{
      content: "";
      position: absolute;
      inset: -20vh auto auto -16vw;
      width: 42vw;
      height: 140vh;
      transform: rotate(16deg);
      background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.45), rgba(255,255,255,0));
      filter: blur(18px);
      opacity: 0.32;
      animation: beamSweep 18s ease-in-out infinite;
    }}
    .ambient-beam::after {{
      inset: -18vh -24vw auto auto;
      width: 34vw;
      transform: rotate(-14deg);
      opacity: 0.18;
      animation-duration: 22s;
      animation-direction: alternate-reverse;
    }}
    .ambient-shards .shard {{
      position: absolute;
      display: block;
      border: 1px solid;
      border-radius: 18px;
      opacity: 0.32;
      box-shadow: 0 18px 36px rgba(48, 38, 30, 0.08);
      animation: shardFloat var(--duration, 18s) ease-in-out infinite;
      animation-delay: var(--delay, 0s);
      transform: rotate(var(--rotation, 0deg));
      backdrop-filter: blur(6px);
    }}
    .shell {{
      position: relative;
      z-index: 1;
    }}
    {canvas_styles}
    @keyframes gridDrift {{
      0% {{ transform: translate3d(0, 0, 0); }}
      50% {{ transform: translate3d(-18px, -24px, 0); }}
      100% {{ transform: translate3d(-36px, -48px, 0); }}
    }}
    @keyframes beamSweep {{
      0% {{ transform: translate3d(-10vw, 0, 0) rotate(16deg); }}
      50% {{ transform: translate3d(20vw, -2vh, 0) rotate(12deg); }}
      100% {{ transform: translate3d(46vw, 1vh, 0) rotate(18deg); }}
    }}
    @keyframes shardFloat {{
      0% {{ transform: translate3d(0, 0, 0) rotate(var(--rotation, 0deg)); }}
      50% {{ transform: translate3d(0, -18px, 0) rotate(calc(var(--rotation, 0deg) + 6deg)); }}
      100% {{ transform: translate3d(0, 0, 0) rotate(var(--rotation, 0deg)); }}
    }}
    {shimmer_keyframes}
"""


def _build_preview_html(
    document: ArticleDocument,
    theme: WechatTheme,
    image_mapping: dict[Path, str],
    render_meta: ArticleRenderMeta,
) -> str:
    hero = _render_article_hero(document.title, theme, render_meta)
    sections = _render_content_sections(document, theme, image_mapping, paste_optimized=False)
    ambient_markup = _build_ambient_markup(theme)
    ambient_styles = _build_ambient_styles(include_canvas=False)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(document.title)} - WeChat Preview</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px 16px 48px;
      min-height: 100vh;
      position: relative;
      overflow-x: hidden;
      isolation: isolate;
      font-family: 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
      color: {theme.text};
      background: {theme.page_bg};
    }}
    .shell {{
      width: min(100%, 760px);
      margin: 0 auto;
      padding: 18px;
      border-radius: 24px;
      background: {theme.shell_bg};
      box-shadow: 0 30px 70px rgba(48, 38, 30, 0.12);
      border: 1px solid {theme.line};
    }}
    .footnote {{
      margin-top: 10px;
      color: {theme.muted};
      font-size: 12px;
      line-height: 1.8;
      text-align: center;
    }}
    {ambient_styles}
    @media (max-width: 720px) {{
      .shell {{ padding: 12px; border-radius: 18px; }}
    }}
  </style>
</head>
<body>
  {ambient_markup}
  <main class="shell">
    {hero}
    {sections}
    <p class="footnote">本页是本地预览版。若要发布到公众号，图片仍需在微信编辑器内上传或托管到可访问地址。</p>
  </main>
</body>
</html>
"""


def _build_wechat_body(
    document: ArticleDocument,
    theme: WechatTheme,
    image_mapping: dict[Path, str],
    render_meta: ArticleRenderMeta,
    *,
    paste_optimized: bool,
) -> str:
    outer_style = (
        "width:100%;max-width:720px;margin:0 auto;padding:0 12px;box-sizing:border-box;"
        if not paste_optimized
        else "width:100%;max-width:720px;margin:0 auto;box-sizing:border-box;"
    )
    hero = _render_article_hero(document.title, theme, render_meta, paste_optimized=paste_optimized)
    sections = _render_content_sections(document, theme, image_mapping, paste_optimized=paste_optimized)
    return f'<section style="{outer_style}">{hero}{sections}</section>'


def _wrap_html_document(title: str, page_bg: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)} - WeChat Safe</title>
</head>
<body style="margin:0;padding:24px 0;background:{page_bg};">
{body}
</body>
</html>
"""


def _build_copyboard_html(title: str, theme: WechatTheme, fragment: str, render_meta: ArticleRenderMeta) -> str:
    ambient_markup = _build_ambient_markup(theme)
    ambient_styles = _build_ambient_styles(include_canvas=True)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)} - Copyboard</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      min-height: 100vh;
      position: relative;
      overflow-x: hidden;
      isolation: isolate;
      font-family: 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
      background: {theme.page_bg};
      color: {theme.text};
    }}
    .shell {{
      max-width: 900px;
      margin: 0 auto;
    }}
    .panel {{
      background: rgba(255,255,255,.92);
      border: 1px solid {theme.line};
      border-radius: 20px;
      box-shadow: {theme.shadow};
      padding: 20px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 30px;
      line-height: 1.2;
    }}
    p {{
      color: {theme.muted};
      line-height: 1.8;
      margin: 0;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 16px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .field {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .field label {{
      color: {theme.muted};
      font-size: 12px;
      line-height: 1.4;
    }}
    .field input,
    .field textarea {{
      width: 100%;
      border: 1px solid {theme.line};
      border-radius: 14px;
      padding: 11px 13px;
      background: rgba(255,255,255,.92);
      color: {theme.text};
      font: inherit;
    }}
    .field textarea {{
      min-height: 84px;
      resize: vertical;
    }}
    .field.span-2 {{
      grid-column: span 2;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: {theme.accent};
      color: white;
      cursor: pointer;
      font-size: 14px;
    }}
    .ghost {{
      background: white;
      color: {theme.text};
      border: 1px solid {theme.line};
    }}
    .status {{
      margin-top: 12px;
      font-size: 13px;
      color: {theme.muted};
    }}
    .canvas {{
      background: rgba(255,255,255,.94);
      border: 1px dashed {theme.line};
      border-radius: 20px;
      padding: 18px;
    }}
    {ambient_styles}
    @media (max-width: 720px) {{
      .meta-grid {{
        grid-template-columns: 1fr;
      }}
      .field.span-2 {{
        grid-column: auto;
      }}
    }}
  </style>
</head>
<body>
  {ambient_markup}
  <main class="shell">
    <section class="panel">
      <h1>公众号复制发布板</h1>
      <p>这页不是给读者看的，是给你复制到公众号编辑器用的。先点“一键复制富文本”，如果浏览器拦截，就点“选中正文”后手动复制，再粘贴到公众号编辑器。</p>
      <div class="meta-grid">
        <div class="field">
          <label for="publish-date">发布日期</label>
          <input id="publish-date" value="{html.escape(render_meta.publish_date)}" />
        </div>
        <div class="field">
          <label for="author">作者</label>
          <input id="author" value="{html.escape(render_meta.author)}" />
        </div>
        <div class="field">
          <label for="source-name">来源</label>
          <input id="source-name" value="{html.escape(render_meta.source_name)}" />
        </div>
        <div class="field">
          <label for="title-text">标题</label>
          <input id="title-text" value="{html.escape(title)}" />
        </div>
        <div class="field span-2">
          <label for="summary">摘要</label>
          <textarea id="summary">{html.escape(render_meta.summary)}</textarea>
        </div>
        <div class="field span-2">
          <label for="source-statement">来源声明</label>
          <textarea id="source-statement">{html.escape(render_meta.source_statement)}</textarea>
        </div>
      </div>
      <div class="actions">
        <button type="button" id="copy-rich">一键复制富文本</button>
        <button type="button" class="ghost" id="select-body">选中正文</button>
      </div>
      <div class="status" id="status">复制时会同时写入 <code>text/html</code> 和纯文本。</div>
    </section>
    <section class="canvas">
      <div id="copy-root">{fragment}</div>
    </section>
  </main>
  <script>
    const copyRoot = document.getElementById("copy-root");
    const status = document.getElementById("status");
    const fields = {{
      title: document.getElementById("title-text"),
      publishDate: document.getElementById("publish-date"),
      author: document.getElementById("author"),
      sourceName: document.getElementById("source-name"),
      summary: document.getElementById("summary"),
      sourceStatement: document.getElementById("source-statement"),
    }};

    function applyMeta() {{
      const title = fields.title.value.trim();
      const publishDate = fields.publishDate.value.trim();
      const author = fields.author.value.trim();
      const sourceName = fields.sourceName.value.trim();
      const summary = fields.summary.value.trim();
      const sourceStatement = fields.sourceStatement.value.trim();
      const metaLine = [publishDate, author, sourceName].filter(Boolean).join(" · ");

      const titleNodes = copyRoot.querySelectorAll("[data-meta-title]");
      const metaNodes = copyRoot.querySelectorAll("[data-meta-line]");
      const dateNodes = copyRoot.querySelectorAll("[data-meta-publish-date]");
      const authorNodes = copyRoot.querySelectorAll("[data-meta-author]");
      const sourceNodes = copyRoot.querySelectorAll("[data-meta-source-name]");
      const summaryNodes = copyRoot.querySelectorAll("[data-meta-summary]");
      const statementNodes = copyRoot.querySelectorAll("[data-meta-source-statement]");

      titleNodes.forEach((node) => node.textContent = title);
      metaNodes.forEach((node) => node.textContent = metaLine);
      dateNodes.forEach((node) => node.textContent = publishDate);
      authorNodes.forEach((node) => node.textContent = author);
      sourceNodes.forEach((node) => node.textContent = sourceName);
      summaryNodes.forEach((node) => node.textContent = summary);
      statementNodes.forEach((node) => node.textContent = sourceStatement);
    }}

    async function copyRichHtml() {{
      applyMeta();
      const currentHtml = copyRoot.innerHTML;
      try {{
        if (navigator.clipboard && window.ClipboardItem) {{
          const item = new ClipboardItem({{
            "text/html": new Blob([currentHtml], {{ type: "text/html" }}),
            "text/plain": new Blob([copyRoot.innerText], {{ type: "text/plain" }})
          }});
          await navigator.clipboard.write([item]);
          status.textContent = "已复制富文本。直接到公众号编辑器粘贴。";
          return;
        }}
      }} catch (error) {{
        status.textContent = "浏览器拒绝了富文本复制，已切换到手动选择模式。";
      }}
      selectBody();
    }}

    function selectBody() {{
      applyMeta();
      const range = document.createRange();
      range.selectNodeContents(copyRoot);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = "正文已经选中。现在按 Ctrl+C，然后去公众号编辑器 Ctrl+V。";
    }}

    Object.values(fields).forEach((field) => field.addEventListener("input", applyMeta));
    applyMeta();
    document.getElementById("copy-rich").addEventListener("click", copyRichHtml);
    document.getElementById("select-body").addEventListener("click", selectBody);
  </script>
</body>
</html>
"""


def _render_article_hero(
    title: str,
    theme: WechatTheme,
    render_meta: ArticleRenderMeta,
    *,
    paste_optimized: bool = False,
) -> str:
    padding = "20px 18px" if paste_optimized else "26px 22px 20px"
    subtitle = theme.name if paste_optimized else "Share Layout"
    meta = (
        f"{html.escape(render_meta.publish_date)} ? {html.escape(render_meta.author)} ? "
        f"{html.escape(render_meta.source_name)}"
    )
    summary_html = (
        f'<p style="margin:12px 0 0;color:{theme.muted};font-size:14px;line-height:1.8;">'
        f'<span data-meta-summary>{html.escape(render_meta.summary)}</span></p>'
    )
    source_html = (
        f'<div style="margin:12px 0 0;color:{theme.muted};font-size:12px;line-height:1.7;">'
        f'<span data-meta-source-statement>{html.escape(render_meta.source_statement)}</span></div>'
    )
    return (
        f'<section style="margin:0 0 18px;padding:{padding};background:{theme.card_bg};'
        f'border-radius:18px;border:1px solid {theme.line};box-shadow:{theme.shadow};">'
        f'<div style="margin:0 0 10px;color:{theme.accent};font-size:12px;letter-spacing:0.18em;'
        f'text-transform:uppercase;">{html.escape(subtitle)}</div>'
        f'<h1 data-meta-title style="margin:0;color:{theme.text};font-size:30px;line-height:1.22;letter-spacing:0;">'
        f"{html.escape(title)}</h1>"
        f'<div data-meta-line style="margin:10px 0 0;color:{theme.muted};font-size:12px;line-height:1.7;">{meta}</div>'
        f"{summary_html}{source_html}</section>"
    )
def _render_content_sections(
    document: ArticleDocument,
    theme: WechatTheme,
    image_mapping: dict[Path, str],
    *,
    paste_optimized: bool,
) -> str:
    groups = _group_blocks(document)
    rendered: list[str] = []
    first_paragraph = True

    for kind, blocks in groups:
        if kind == "paragraph":
            text = blocks[0].text
            if first_paragraph:
                rendered.append(_render_intro_panel(text, theme))
                first_paragraph = False
            else:
                rendered.append(
                    f'<section style="margin:0 0 18px;padding:18px;background:{theme.card_bg};'
                    f'border:1px solid {theme.line};border-radius:16px;box-shadow:{theme.shadow};">'
                    f'<p style="margin:0;color:{theme.muted};font-size:14px;line-height:1.9;text-align:justify;">'
                    f"{html.escape(text)}</p></section>"
                )
        elif kind == "gallery":
            rendered.append(_render_gallery(blocks, theme, image_mapping, paste_optimized=paste_optimized))
        elif kind == "cta":
            rendered.append(_render_cta(blocks[0], theme, image_mapping))

    return "".join(rendered)


def _render_gallery(
    blocks: list[ArticleBlock],
    theme: WechatTheme,
    image_mapping: dict[Path, str],
    *,
    paste_optimized: bool,
) -> str:
    cards: list[str] = []
    for index, block in enumerate(blocks, start=1):
        src = image_mapping[block.image_path]
        margin_right = "0" if index % 3 == 0 else "3.2%"
        image_style = (
            "display:block;width:100%;height:auto;"
            if paste_optimized
            else "display:block;width:100%;height:auto;aspect-ratio:1 / 2;object-fit:cover;"
        )
        cards.append(
            f'<span style="display:inline-block;width:31.2%;margin:0 {margin_right} 14px 0;vertical-align:top;'
            f'border-radius:10px;overflow:hidden;background:{theme.card_bg};border:1px solid {theme.line};'
            f'box-shadow:{theme.shadow};"><img src="{html.escape(src)}" alt="" style="{image_style}" /></span>'
        )

    return f'<section style="margin:0 0 18px;font-size:0;line-height:0;">{"".join(cards)}</section>'


def _render_cta(block: ArticleBlock, theme: WechatTheme, image_mapping: dict[Path, str]) -> str:
    src = image_mapping[block.image_path]
    link = html.escape(block.link or "#")
    return (
        f'<section style="margin:0 0 10px;padding:10px;background:{theme.card_bg};border:1px solid {theme.line};'
        f'border-radius:16px;box-shadow:{theme.shadow};text-align:center;">'
        f'<a href="{link}" style="display:block;text-decoration:none;"><img src="{html.escape(src)}" alt="" '
        'style="display:block;width:90%;max-width:540px;height:auto;margin:0 auto;border-radius:10px;" /></a>'
        "</section>"
    )


def _build_cover_png(
    document: ArticleDocument,
    theme: WechatTheme,
    image_mapping: dict[Path, str],
    render_meta: ArticleRenderMeta,
    output_path: Path,
) -> None:
    width, height = 1200, 1600
    image = _build_gradient((width, height), theme.shell_bg, theme.accent_soft).convert("RGBA")
    draw = ImageDraw.Draw(image)

    line_color = _hex_to_rgb(theme.line)
    accent = _hex_to_rgb(theme.accent)
    text = _hex_to_rgb(theme.text)
    muted = _hex_to_rgb(theme.muted)
    card = _hex_to_rgb(theme.card_bg)

    draw.rounded_rectangle((46, 46, width - 46, height - 46), radius=34, fill=card + (236,), outline=line_color + (180,), width=2)
    draw.rounded_rectangle((78, 78, width - 78, 420), radius=28, fill=(255, 255, 255, 228), outline=line_color + (120,), width=2)

    eyebrow_font = _load_font(28, bold=True)
    title_font = _load_font(66, bold=True)
    body_font = _load_font(24)

    draw.text((112, 118), theme.name.upper(), font=eyebrow_font, fill=accent)
    draw.text((112, 170), "公众号首图", font=eyebrow_font, fill=muted)
    _draw_text_block(draw, document.title, 112, 232, font=title_font, fill=text, max_width=820, line_gap=12)
    _draw_text_block(draw, render_meta.summary, 112, 358, font=body_font, fill=muted, max_width=820, line_gap=8)
    draw.text((112, 442), f"{render_meta.publish_date} · {render_meta.author}", font=body_font, fill=accent)
    _draw_text_block(draw, render_meta.source_statement, 112, 474, font=_load_font(20), fill=muted, max_width=820, line_gap=6)

    preview_sources = [block.image_path for block in document.blocks if block.type == "image" and block.image_path][:3]
    slots = [
        (120, 520, 430, 1200),
        (445, 470, 755, 1300),
        (770, 540, 1080, 1240),
    ]
    for source, slot in zip(preview_sources, slots):
        relative = image_mapping[source]
        asset_path = output_path.parent / relative
        frame = _fit_cover_image(asset_path, slot[2] - slot[0], slot[3] - slot[1])
        draw.rounded_rectangle(slot, radius=22, fill=(255, 255, 255, 210), outline=line_color + (140,), width=2)
        mask = Image.new("L", (slot[2] - slot[0], slot[3] - slot[1]), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, slot[2] - slot[0], slot[3] - slot[1]), radius=22, fill=255)
        image.paste(frame, (slot[0], slot[1]), mask)

    draw.rounded_rectangle((90, 1328, 1110, 1490), radius=24, fill=(255, 255, 255, 226), outline=line_color + (120,), width=2)
    footer_font = _load_font(26, bold=True)
    note_font = _load_font(22)
    draw.text((120, 1368), "内容模板输出", font=footer_font, fill=text)
    draw.text((120, 1414), "适合公众号正文首图、文章头图和封面分享。", font=note_font, fill=muted)
    draw.text((810, 1400), theme.key, font=note_font, fill=accent)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


def _build_article_header_png(
    document: ArticleDocument,
    theme: WechatTheme,
    image_mapping: dict[Path, str],
    render_meta: ArticleRenderMeta,
    output_path: Path,
) -> None:
    width, height = 1242, 702
    image = _build_gradient((width, height), theme.shell_bg, theme.accent_soft).convert("RGBA")

    shell_box = (42, 42, width - 42, height - 42)
    _draw_panel(image, shell_box, radius=34, fill=(255, 255, 255, 238), outline=_hex_to_rgb(theme.line), shadow_alpha=22)
    draw = ImageDraw.Draw(image)

    eyebrow_font = _load_font(24, bold=True)
    title_font = _load_font(54, bold=True)
    meta_font = _load_font(22)
    note_font = _load_font(20)

    content_left = 84
    content_top = 86
    content_right = width - 84

    title_lines, _, title_line_height = _measure_text_block(
        draw, document.title, title_font, 560, line_gap=12
    )
    draw.text((content_left, content_top), theme.name.upper(), font=eyebrow_font, fill=_hex_to_rgb(theme.accent))
    _draw_lines(
        draw,
        title_lines,
        content_left,
        content_top + 42,
        font=title_font,
        fill=_hex_to_rgb(theme.text),
        line_gap=12,
        line_height=title_line_height,
    )
    meta_y = content_top + 42 + len(title_lines) * title_line_height + max(0, len(title_lines) - 1) * 12 + 24
    draw.text((content_left, meta_y), f"{render_meta.publish_date} · {render_meta.author}", font=eyebrow_font, fill=_hex_to_rgb(theme.muted))
    draw.text((content_left, meta_y + 40), render_meta.summary, font=meta_font, fill=_hex_to_rgb(theme.muted))

    swatch_y = meta_y + 94
    swatches = [theme.accent, theme.accent_soft, theme.line]
    for index, color in enumerate(swatches):
        x = content_left + index * 36
        draw.rounded_rectangle((x, swatch_y, x + 24, swatch_y + 24), radius=8, fill=_hex_to_rgb(color))
    draw.text((content_left + 126, swatch_y + 1), f"{render_meta.source_name} · {len(image_mapping)} images", font=note_font, fill=_hex_to_rgb(theme.muted))

    preview_sources = [block.image_path for block in document.blocks if block.type == "image" and block.image_path][:3]
    card_width = 186
    card_height = 430
    gap = 18
    right_margin = 94
    first_x = content_right - (card_width * 3 + gap * 2)
    top_y = 118
    offsets = [38, 0, 58]
    rotations = [-5.5, 2.5, -3.0]

    for index, source in enumerate(preview_sources):
        x = first_x + index * (card_width + gap)
        y = top_y + offsets[index]
        frame = Image.new("RGBA", (card_width, card_height), (255, 255, 255, 0))
        _draw_panel(frame, (0, 0, card_width, card_height), radius=24, fill=(255, 255, 255, 244), outline=_hex_to_rgb(theme.line), shadow_alpha=0)
        tile = _fit_cover_image(output_path.parent / image_mapping[source], card_width, card_height)
        _paste_rounded(frame, tile, (0, 0), radius=24)
        rotated = frame.rotate(rotations[index], resample=Image.Resampling.BICUBIC, expand=True)
        paste_x = int(x - (rotated.width - card_width) / 2)
        paste_y = int(y - (rotated.height - card_height) / 2)
        image.alpha_composite(rotated, (paste_x, paste_y))

    ribbon_box = (content_left, height - 170, width - right_margin, height - 104)
    _draw_panel(image, ribbon_box, radius=22, fill=(255, 255, 255, 236), outline=_hex_to_rgb(theme.line), shadow_alpha=18)
    draw = ImageDraw.Draw(image)
    draw.text((content_left + 28, height - 148), "公众号封面 / 转发头图 / 正文首屏", font=eyebrow_font, fill=_hex_to_rgb(theme.accent))
    draw.text((content_left + 28, height - 114), render_meta.source_statement[:56], font=note_font, fill=_hex_to_rgb(theme.muted))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


def _build_article_long_png(
    document: ArticleDocument,
    theme: WechatTheme,
    image_mapping: dict[Path, str],
    render_meta: ArticleRenderMeta,
    output_path: Path,
) -> None:
    width = 1242
    outer_margin = 54
    shell_padding = 36
    section_gap = 24
    shell_width = width - outer_margin * 2
    content_width = shell_width - shell_padding * 2
    card_padding = 28
    card_inner_width = content_width - card_padding * 2
    column_gap = 18
    gallery_width = (content_width - column_gap * 2) // 3
    gallery_height = int(gallery_width * 1.68)

    eyebrow_font = _load_font(20, bold=True)
    title_font = _load_font(56, bold=True)
    section_font = _load_font(18, bold=True)
    body_font = _load_font(26)
    quote_font = _load_font(24)
    footer_font = _load_font(22)

    measure_image = Image.new("RGBA", (width, 32), (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(measure_image)

    title_lines, title_block_height, title_line_height = _measure_text_block(
        measure_draw, document.title, title_font, card_inner_width, line_gap=14
    )
    summary_lines, summary_block_height, summary_line_height = _measure_text_block(
        measure_draw, render_meta.summary, body_font, card_inner_width, line_gap=8
    )
    source_lines, source_block_height, source_line_height = _measure_text_block(
        measure_draw, render_meta.source_statement, footer_font, card_inner_width, line_gap=6
    )
    hero_height = max(260, 30 + 24 + 18 + title_block_height + 16 + 28 + summary_block_height + 16 + source_block_height + 28)

    sections: list[dict[str, object]] = []
    first_paragraph = True
    groups = _group_blocks(document)
    total_content_height = hero_height

    for kind, blocks in groups:
        if kind == "paragraph":
            text = blocks[0].text
            if first_paragraph:
                quotes = _extract_quotes(text)
                if quotes:
                    quote_items: list[list[str]] = []
                    quote_height = 0
                    for quote in quotes:
                        lines, block_height, _ = _measure_text_block(
                            measure_draw,
                            f'"{quote}"',
                            quote_font,
                            card_inner_width,
                            line_gap=10,
                        )
                        quote_items.append(lines)
                        quote_height += block_height + 10
                    section_height = 30 + 18 + 14 + max(0, quote_height - 10) + 28
                    sections.append(
                        {
                            "type": "intro_quotes",
                            "quotes": quote_items,
                            "height": section_height,
                        }
                    )
                else:
                    lines, block_height, _ = _measure_text_block(
                        measure_draw, text, body_font, card_inner_width, line_gap=10
                    )
                    section_height = 30 + block_height + 30
                    sections.append(
                        {
                            "type": "paragraph",
                            "lines": lines,
                            "height": section_height,
                        }
                    )
                first_paragraph = False
            else:
                lines, block_height, _ = _measure_text_block(
                    measure_draw, text, body_font, card_inner_width, line_gap=10
                )
                section_height = 30 + block_height + 30
                sections.append(
                    {
                        "type": "paragraph",
                        "lines": lines,
                        "height": section_height,
                    }
                )
        elif kind == "gallery":
            rows = (len(blocks) + 2) // 3
            section_height = rows * gallery_height + max(0, rows - 1) * column_gap
            sections.append(
                {
                    "type": "gallery",
                    "blocks": blocks,
                    "height": section_height,
                    "card_width": gallery_width,
                    "card_height": gallery_height,
                }
            )
        elif kind == "cta":
            asset_path = output_path.parent / image_mapping[blocks[0].image_path]
            preview_width = int(content_width * 0.88)
            preview_height = _measure_contain_height(asset_path, preview_width, min_height=180, max_height=380)
            section_height = preview_height + 42
            sections.append(
                {
                    "type": "cta",
                    "asset_path": asset_path,
                    "height": section_height,
                    "preview_width": preview_width,
                    "preview_height": preview_height,
                }
            )
        total_content_height += section_gap + int(sections[-1]["height"])

    footer_height = 128
    total_content_height += section_gap + footer_height
    shell_height = shell_padding * 2 + total_content_height
    canvas_height = shell_height + outer_margin * 2

    image = _build_gradient((width, canvas_height), theme.shell_bg, theme.accent_soft).convert("RGBA")
    draw = ImageDraw.Draw(image)

    shell_box = (outer_margin, outer_margin, outer_margin + shell_width, outer_margin + shell_height)
    _draw_panel(image, shell_box, radius=34, fill=(255, 255, 255, 238), outline=_hex_to_rgb(theme.line))

    content_left = outer_margin + shell_padding
    cursor_y = outer_margin + shell_padding
    content_right = content_left + content_width

    hero_box = (content_left, cursor_y, content_right, cursor_y + hero_height)
    _draw_panel(image, hero_box, radius=26, fill=(255, 255, 255, 245), outline=_hex_to_rgb(theme.line), shadow_alpha=26)
    draw = ImageDraw.Draw(image)
    draw.text((content_left + card_padding, cursor_y + 30), "SHARE LAYOUT", font=eyebrow_font, fill=_hex_to_rgb(theme.muted))
    title_y = cursor_y + 72
    _draw_lines(
        draw,
        title_lines,
        content_left + card_padding,
        title_y,
        font=title_font,
        fill=_hex_to_rgb(theme.text),
        line_gap=14,
        line_height=title_line_height,
    )
    meta_y = title_y + len(title_lines) * title_line_height + max(0, len(title_lines) - 1) * 14 + 14
    draw.text(
        (content_left + card_padding, meta_y),
        f"{render_meta.publish_date} · {render_meta.author} · {render_meta.source_name}",
        font=eyebrow_font,
        fill=_hex_to_rgb(theme.accent),
    )
    _draw_lines(
        draw,
        summary_lines,
        content_left + card_padding,
        meta_y + 28,
        font=body_font,
        fill=_hex_to_rgb(theme.muted),
        line_gap=8,
        line_height=summary_line_height,
    )
    source_y = meta_y + 28 + len(summary_lines) * summary_line_height + max(0, len(summary_lines) - 1) * 8 + 14
    _draw_lines(
        draw,
        source_lines,
        content_left + card_padding,
        source_y,
        font=footer_font,
        fill=_hex_to_rgb(theme.muted),
        line_gap=6,
        line_height=source_line_height,
    )
    cursor_y += hero_height + section_gap

    for section in sections:
        section_height = int(section["height"])
        if section["type"] == "intro_quotes":
            box = (content_left, cursor_y, content_right, cursor_y + section_height)
            _draw_panel(image, box, radius=24, fill=(255, 255, 255, 242), outline=_hex_to_rgb(theme.line), shadow_alpha=22)
            draw = ImageDraw.Draw(image)
            draw.text((content_left + card_padding, cursor_y + 26), "QUOTE SELECTION", font=section_font, fill=_hex_to_rgb(theme.accent))
            line_y = cursor_y + 62
            quote_line_height = _line_height(draw, quote_font)
            for lines in section["quotes"]:
                _draw_lines(
                    draw,
                    lines,
                    content_left + card_padding,
                    line_y,
                    font=quote_font,
                    fill=_hex_to_rgb(theme.muted),
                    line_gap=10,
                    line_height=quote_line_height,
                )
                line_y += len(lines) * quote_line_height + max(0, len(lines) - 1) * 10 + 10
        elif section["type"] == "paragraph":
            box = (content_left, cursor_y, content_right, cursor_y + section_height)
            _draw_panel(image, box, radius=24, fill=(255, 255, 255, 242), outline=_hex_to_rgb(theme.line), shadow_alpha=22)
            draw = ImageDraw.Draw(image)
            _draw_lines(
                draw,
                section["lines"],
                content_left + card_padding,
                cursor_y + 28,
                font=body_font,
                fill=_hex_to_rgb(theme.muted),
                line_gap=10,
                line_height=_line_height(draw, body_font),
            )
        elif section["type"] == "gallery":
            blocks = section["blocks"]
            card_width = int(section["card_width"])
            card_height = int(section["card_height"])
            for index, block in enumerate(blocks):
                row = index // 3
                col = index % 3
                x = content_left + col * (card_width + column_gap)
                y = cursor_y + row * (card_height + column_gap)
                box = (x, y, x + card_width, y + card_height)
                _draw_panel(image, box, radius=20, fill=(255, 255, 255, 240), outline=_hex_to_rgb(theme.line), shadow_alpha=18)
                asset_path = output_path.parent / image_mapping[block.image_path]
                tile = _fit_cover_image(asset_path, card_width, card_height)
                _paste_rounded(image, tile, (x, y), radius=20)
        elif section["type"] == "cta":
            preview_width = int(section["preview_width"])
            preview_height = int(section["preview_height"])
            x = content_left + (content_width - preview_width) // 2
            y = cursor_y + 12
            box = (x, y, x + preview_width, y + preview_height)
            _draw_panel(image, box, radius=22, fill=(255, 255, 255, 242), outline=_hex_to_rgb(theme.line), shadow_alpha=18)
            tile = _fit_contain_image(Path(section["asset_path"]), preview_width, preview_height)
            _paste_rounded(image, tile, (x, y), radius=22)
        cursor_y += section_height + section_gap

    footer_box = (content_left, cursor_y, content_right, cursor_y + footer_height)
    _draw_panel(image, footer_box, radius=24, fill=(255, 255, 255, 240), outline=_hex_to_rgb(theme.line), shadow_alpha=18)
    draw = ImageDraw.Draw(image)
    draw.text((content_left + card_padding, cursor_y + 26), "LONG IMAGE EXPORT", font=section_font, fill=_hex_to_rgb(theme.accent))
    draw.text(
        (content_left + card_padding, cursor_y + 52),
        f"{render_meta.publish_date} ? {render_meta.author} ? {render_meta.source_name}",
        font=footer_font,
        fill=_hex_to_rgb(theme.muted),
    )
    draw.text((content_left + card_padding, cursor_y + 82), theme.key, font=footer_font, fill=_hex_to_rgb(theme.muted))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


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


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
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


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 10,
) -> int:
    lines = _wrap_text(text, font, max_width, draw)
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        bbox = draw.textbbox((x, cursor), line, font=font)
        cursor += (bbox[3] - bbox[1]) + line_gap
    return cursor


def _measure_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    *,
    line_gap: int = 10,
) -> tuple[list[str], int, int]:
    lines = _wrap_text(text, font, max_width, draw)
    line_height = _line_height(draw, font)
    total_height = len(lines) * line_height + max(0, len(lines) - 1) * line_gap
    return lines, total_height, line_height


def _line_height(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    return bbox[3] - bbox[1]


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    x: int,
    y: int,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    line_gap: int,
    line_height: int,
) -> int:
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += line_height + line_gap
    return cursor


def _draw_panel(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int],
    shadow_alpha: int = 24,
) -> None:
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_box = (box[0], box[1] + 10, box[2], box[3] + 10)
    shadow_draw.rounded_rectangle(shadow_box, radius=radius, fill=(48, 38, 30, shadow_alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    image.alpha_composite(shadow)

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline + (180,), width=2)


def _paste_rounded(image: Image.Image, tile: Image.Image, position: tuple[int, int], *, radius: int) -> None:
    mask = Image.new("L", tile.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, tile.size[0], tile.size[1]), radius=radius, fill=255)
    image.paste(tile, position, mask)


def _measure_contain_height(path: Path, width: int, *, min_height: int, max_height: int) -> int:
    with Image.open(path) as source:
        ratio = source.height / source.width if source.width else 1
    height = int(width * ratio)
    return max(min_height, min(max_height, height))


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


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


def _fit_cover_image(path: Path, width: int, height: int) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    source_ratio = image.width / image.height
    target_ratio = width / height

    if source_ratio > target_ratio:
        crop_width = int(image.height * target_ratio)
        left = (image.width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, image.height))
    else:
        crop_height = int(image.width / target_ratio)
        top = (image.height - crop_height) // 2
        image = image.crop((0, top, image.width, top + crop_height))

    return image.resize((width, height), Image.Resampling.LANCZOS)


def _fit_contain_image(path: Path, width: int, height: int) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    x = (width - image.width) // 2
    y = (height - image.height) // 2
    canvas.paste(image, (x, y), image)
    return canvas


# ── Registry adapter ──

def register_wechat_adapter(registry) -> None:
    """Register the WeChat article renderer with the template registry."""
    from src.templates.registry import RenderResult

    def _wechat_adapter(
        manifest,
        input_data: dict,
        theme,
        output_dir: str,
    ) -> "RenderResult":
        """Adapter: registry → wechat_renderer."""
        markdown_file = input_data.get("markdown_file", "")
        if not markdown_file:
            raise ValueError("wechat template requires 'markdown_file' field")

        rendered = render_wechat_article(
            markdown_file,
            theme=theme.id,
            title=input_data.get("title"),
            author=input_data.get("author"),
            source_name=input_data.get("source_name"),
            source_statement=input_data.get("source_statement"),
            publish_date=input_data.get("publish_date"),
            summary=input_data.get("summary"),
            output_dir=output_dir,
        )
        return RenderResult(
            template_id=manifest.id,
            theme_id=theme.id,
            output_dir=output_dir,
            artifacts={
                "preview_html": str(rendered.preview_html_path),
                "wechat_html": str(rendered.wechat_html_path),
                "wechat_body": str(rendered.wechat_body_path),
                "wechat_paste": str(rendered.wechat_paste_path),
                "cover_png": str(rendered.cover_png_path),
            },
        )

    registry.register_renderer("wechat_renderer", _wechat_adapter)
