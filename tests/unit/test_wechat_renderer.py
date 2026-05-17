from pathlib import Path

from PIL import Image

from src.reports.wechat_renderer import (
    list_wechat_themes,
    parse_article_markdown,
    render_wechat_article,
)


def _create_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 1280), color).save(path)


def _sample_markdown(tmp_path: Path) -> Path:
    image_dir = tmp_path / "images"
    _create_image(image_dir / "a.png", (180, 120, 100))
    _create_image(image_dir / "b.png", (120, 140, 180))
    _create_image(image_dir / "c.png", (100, 160, 120))
    _create_image(image_dir / "cta.png", (90, 90, 90))

    markdown = tmp_path / "article.md"
    markdown.write_text(
        "\n".join(
            [
                "# SHARE壁纸｜百看不厌的壁纸",
                "",
                "一些宿命感很强的小众短句文案：“我把想念折成船放进深夜的雨里” “后来我才明白遗憾也会发光” “海没有回答我浪替它叹了口气”",
                "",
                "![图片](images/a.png)",
                "",
                "![图片](images/b.png)",
                "",
                "![图片](images/c.png)",
                "",
                "一些文案：“成长大概是学会和自己的废墟握手” “灯一盏盏亮起像迟到的理解”",
                "",
                "[![图片](images/cta.png)](https://example.com)",
            ]
        ),
        encoding="utf-8",
    )
    return markdown


def test_parse_article_markdown(tmp_path: Path):
    markdown = _sample_markdown(tmp_path)

    document = parse_article_markdown(markdown)

    assert document.title == "SHARE壁纸|百看不厌的壁纸"
    assert len(document.blocks) == 6
    assert document.blocks[0].type == "paragraph"
    assert document.blocks[1].type == "image"
    assert document.blocks[-1].type == "linked_image"


def test_render_wechat_article_outputs(tmp_path: Path):
    markdown = _sample_markdown(tmp_path)

    rendered = render_wechat_article(
        markdown,
        output_dir=str(tmp_path / "out"),
        author="Codex",
        source_name="Skills Lab",
        source_statement="数据来自 Skills Lab 自动整理，仅用于内容排版测试。",
        summary="这是一段用于测试的摘要。",
        publish_date="2026-05-15",
    )

    assert rendered.cover_png_path.exists()
    assert rendered.article_header_png_path.exists()
    assert rendered.article_long_png_path.exists()
    assert rendered.preview_html_path.exists()
    assert rendered.wechat_html_path.exists()
    assert rendered.wechat_body_path.exists()
    assert rendered.wechat_paste_path.exists()
    assert rendered.wechat_copyboard_path.exists()
    assert rendered.assets_dir.exists()
    assert rendered.image_count == 4

    with Image.open(rendered.article_header_png_path) as exported:
        assert exported.width == 1242
        assert exported.height == 702

    with Image.open(rendered.article_long_png_path) as exported:
        assert exported.width == 1242
        assert exported.height > exported.width

    preview = rendered.preview_html_path.read_text(encoding="utf-8")
    wechat_html = rendered.wechat_html_path.read_text(encoding="utf-8")
    wechat_body = rendered.wechat_body_path.read_text(encoding="utf-8")
    wechat_paste = rendered.wechat_paste_path.read_text(encoding="utf-8")
    copyboard = rendered.wechat_copyboard_path.read_text(encoding="utf-8")

    assert "SHARE壁纸|百看不厌的壁纸" in preview
    assert "Quote Selection" in preview
    assert "assets/a.png" in preview
    assert "ambient-grid" in preview
    assert "@keyframes beamSweep" in preview
    assert "https://example.com" in wechat_body
    assert "<body" in wechat_html
    assert "SHARE壁纸|百看不厌的壁纸" in wechat_body
    assert "2026-05-15" in wechat_body
    assert "Codex" in wechat_body
    assert "Skills Lab" in wechat_body
    assert "这是一段用于测试的摘要。" in wechat_body
    assert "SHARE壁纸|百看不厌的壁纸" in wechat_paste
    assert "一键复制富文本" in copyboard
    assert "ClipboardItem" in copyboard
    assert "ambient-grid" in copyboard
    assert "@keyframes beamSweep" in copyboard
    assert 'id="author"' in copyboard
    assert 'id="source-name"' in copyboard
    assert 'id="publish-date"' in copyboard
    assert "applyMeta()" in copyboard
    assert "data-meta-summary" in copyboard
    assert rendered.preview_html_path.parent.name.endswith("mist-gallery")


def test_render_wechat_article_separates_themes(tmp_path: Path):
    markdown = _sample_markdown(tmp_path)

    mist = render_wechat_article(markdown, theme="mist-gallery", output_dir=str(tmp_path / "out"))
    maple = render_wechat_article(markdown, theme="maple-gallery", output_dir=str(tmp_path / "out"))

    assert mist.preview_html_path != maple.preview_html_path
    assert mist.preview_html_path.exists()
    assert maple.preview_html_path.exists()


def test_list_wechat_themes():
    themes = list_wechat_themes()

    assert themes
    assert {theme["key"] for theme in themes} >= {"mist-gallery", "maple-gallery"}
