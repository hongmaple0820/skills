from pathlib import Path

from src.core.models import DailyLogEntry
from src.reports.daily_renderer import (
    list_themes,
    render_daily_report,
    render_theme_preview_gallery,
    summarize_daily_logs,
)


def sample_logs():
    return [
        DailyLogEntry(
            date="2026-05-13",
            skill_name="LLM Workflow",
            learning_content="优化日报工作流渲染器",
            duration_minutes=90,
            insights=["把日报从 CLI 输出推进到展示层"],
            problems=["公众号正文不适合直接跑脚本"],
            plans=["增加主题配置", "补图片导出测试"],
            mood=4,
        ),
        DailyLogEntry(
            date="2026-05-13",
            skill_name="Prompt Engineering",
            learning_content="梳理 AI 科技主题的视觉语言",
            duration_minutes=45,
            insights=["统一主题变量后扩展成本会明显下降"],
            problems=["需要同时兼顾图片和交互页面"],
            plans=["支持更多主题"],
            mood=5,
        ),
    ]


def test_summarize_daily_logs():
    summary = summarize_daily_logs(
        sample_logs(),
        date="2026-05-13",
        theme="maple-ai",
        title="AI 科技日报",
        description="测试描述",
        author="Codex",
        source_name="Skills Platform",
        source_statement="测试来源声明",
        user_note="测试备注",
    )

    assert summary.total_minutes == 135
    assert summary.total_entries == 2
    assert summary.skills == ["LLM Workflow", "Prompt Engineering"]
    assert summary.mood == 4
    assert summary.highlights


def test_render_daily_report_outputs(tmp_path: Path):
    rendered = render_daily_report(
        sample_logs(),
        date="2026-05-13",
        theme="maple-ai",
        title="AI 科技日报",
        description="测试描述",
        author="Codex",
        source_name="Skills Platform",
        source_statement="测试来源声明",
        user_note="测试备注",
        output_dir=str(tmp_path),
    )

    assert rendered.poster_svg_path.exists()
    assert rendered.poster_png_path.exists()
    assert rendered.poster_html_path.exists()
    assert rendered.widget_path.exists()
    assert rendered.article_path.exists()

    poster = rendered.poster_svg_path.read_text(encoding="utf-8")
    poster_html = rendered.poster_html_path.read_text(encoding="utf-8")
    widget = rendered.widget_path.read_text(encoding="utf-8")
    article = rendered.article_path.read_text(encoding="utf-8")

    assert "AI 科技日报" in poster
    assert "来源声明" in poster_html
    assert "Codex" in poster_html
    assert "交互时间线" in widget
    assert "作者 Codex" in widget
    assert rendered.widget_path.name in article
    assert rendered.poster_svg_path.name in article
    assert rendered.poster_png_path.name in article


def test_list_themes_contains_brand_metadata():
    themes = list_themes()

    assert themes
    assert themes[0]["key"]
    assert themes[0]["name"]
    assert themes[0]["accent"].startswith("#")
    assert themes[0]["description"]


def test_render_theme_preview_gallery(tmp_path: Path):
    gallery_path, bundles = render_theme_preview_gallery(
        sample_logs(),
        date="2026-05-13",
        title="主题预览",
        description="统一示例",
        author="Codex",
        source_name="Skills Platform",
        source_statement="测试来源声明",
        user_note="测试备注",
        output_dir=str(tmp_path),
    )

    assert gallery_path.exists()
    assert len(bundles) >= 2
    gallery = gallery_path.read_text(encoding="utf-8")
    assert "日报主题预览" in gallery
    assert bundles[0].poster_png_path.exists()
    assert bundles[0].poster_html_path.exists()
