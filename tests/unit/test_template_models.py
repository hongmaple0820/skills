"""Tests for template models and registry."""

from pathlib import Path
import tempfile

import yaml

from src.templates.models import (
    TemplateField,
    TemplateFieldType,
    TemplateManifest,
    TemplateSlot,
    ThemeManifest,
)
from src.templates.registry import TemplateRegistry


# ========== TemplateField Tests ==========

def test_template_field_defaults():
    field = TemplateField(key="title", label="标题")
    assert field.key == "title"
    assert field.label == "标题"
    assert field.type == "string"
    assert field.required is False
    assert field.default is None


def test_template_field_required():
    field = TemplateField(key="content", label="内容", required=True, type="text")
    assert field.required is True
    assert field.type == "text"


def test_template_field_with_select_options():
    field = TemplateField(
        key="theme",
        label="主题",
        type="select",
        options=[{"label": "AI 科技", "value": "maple-ai"}, {"label": "品牌专栏", "value": "maple-editorial"}],
    )
    assert len(field.options) == 2
    assert field.options[0]["value"] == "maple-ai"


# ========== TemplateSlot Tests ==========

def test_template_slot_defaults():
    slot = TemplateSlot(key="poster", label="海报")
    assert slot.key == "poster"
    assert slot.label == "海报"
    assert slot.formats == ["html"]
    assert slot.required is False


def test_template_slot_with_formats():
    slot = TemplateSlot(key="poster_png", label="海报PNG", formats=["png", "svg"])
    assert "png" in slot.formats
    assert "svg" in slot.formats


# ========== ThemeManifest Tests ==========

def test_theme_manifest():
    theme = ThemeManifest(
        id="maple-ai",
        name="AI 科技",
        description="AI 自动化日报主题",
        tokens={
            "color.bg_start": "#2f0f12",
            "color.bg_end": "#5c1d18",
            "color.accent": "#b63a2b",
        },
    )
    assert theme.id == "maple-ai"
    assert theme.tokens["color.accent"] == "#b63a2b"
    assert len(theme.tokens) == 3


def test_theme_manifest_no_tokens():
    theme = ThemeManifest(id="minimal", name="极简")
    assert theme.tokens == {}


# ========== TemplateManifest Tests ==========

def test_template_manifest_minimal():
    manifest = TemplateManifest(
        id="test.template",
        name="测试模板",
        renderer="test_renderer",
    )
    assert manifest.id == "test.template"
    assert manifest.name == "测试模板"
    assert manifest.renderer == "test_renderer"
    assert manifest.version == "1.0.0"
    assert manifest.fields == []
    assert manifest.slots == []


def test_template_manifest_with_fields_and_slots():
    manifest = TemplateManifest(
        id="daily.report",
        name="日报",
        renderer="daily_renderer",
        fields=[
            TemplateField(key="title", label="标题", required=True),
            TemplateField(key="author", label="作者", default="Codex"),
        ],
        slots=[
            TemplateSlot(key="poster", label="海报", formats=["svg", "png"], required=True),
            TemplateSlot(key="widget", label="Widget", formats=["html"]),
        ],
        themes=[
            {"id": "maple-ai", "name": "AI 科技", "file": "themes/maple-ai.yaml"},
        ],
    )
    assert len(manifest.fields) == 2
    assert len(manifest.slots) == 2
    assert len(manifest.themes) == 1
    assert manifest.get_field("title") is not None
    assert manifest.get_field("title").required is True
    assert manifest.get_field("nonexistent") is None
    assert manifest.get_slot("poster") is not None
    assert manifest.get_slot("poster").required is True


# ========== Field Validation Tests ==========

class TestFieldValidation:
    def test_required_field_missing(self):
        manifest = TemplateManifest(
            id="test", name="Test", renderer="r",
            fields=[TemplateField(key="title", label="标题", required=True)],
        )
        errors = manifest.validate_fields({})
        assert len(errors) == 1
        assert "required" in errors[0].lower()

    def test_required_field_empty_string(self):
        manifest = TemplateManifest(
            id="test", name="Test", renderer="r",
            fields=[TemplateField(key="title", label="标题", required=True)],
        )
        errors = manifest.validate_fields({"title": ""})
        assert len(errors) == 1

    def test_required_field_present(self):
        manifest = TemplateManifest(
            id="test", name="Test", renderer="r",
            fields=[TemplateField(key="title", label="标题", required=True)],
        )
        errors = manifest.validate_fields({"title": "Hello"})
        assert len(errors) == 0

    def test_string_min_length(self):
        manifest = TemplateManifest(
            id="test", name="Test", renderer="r",
            fields=[TemplateField(key="name", label="名称", validation={"min_length": 2})],
        )
        errors = manifest.validate_fields({"name": "A"})
        assert len(errors) == 1
        errors = manifest.validate_fields({"name": "AB"})
        assert len(errors) == 0

    def test_select_validation(self):
        manifest = TemplateManifest(
            id="test", name="Test", renderer="r",
            fields=[TemplateField(
                key="theme", label="主题", type="select",
                options=[{"label": "A", "value": "a"}, {"label": "B", "value": "b"}],
            )],
        )
        errors = manifest.validate_fields({"theme": "a"})
        assert len(errors) == 0
        errors = manifest.validate_fields({"theme": "c"})
        assert len(errors) == 1

    def test_multiple_required_fields(self):
        manifest = TemplateManifest(
            id="test", name="Test", renderer="r",
            fields=[
                TemplateField(key="a", label="A", required=True),
                TemplateField(key="b", label="B", required=True),
                TemplateField(key="c", label="C", required=False),
            ],
        )
        errors = manifest.validate_fields({"a": "ok"})
        assert len(errors) == 1  # b is missing
        errors = manifest.validate_fields({"a": "ok", "b": "ok"})
        assert len(errors) == 0


# ========== TemplateRegistry Tests ==========

class TestTemplateRegistry:
    def test_empty_registry(self):
        """Registry without templates should return empty lists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = TemplateRegistry(template_dirs=[Path(tmpdir)])
            templates = registry.list_templates()
            assert templates == []

    def test_load_manifest_from_yaml(self, tmp_path: Path):
        """Load a valid manifest.yaml and list templates."""
        tpl_dir = tmp_path / "templates" / "test.alpha"
        tpl_dir.mkdir(parents=True)

        manifest = {
            "id": "test.alpha",
            "name": "Test Alpha",
            "renderer": "alpha_renderer",
            "fields": [
                {"key": "title", "label": "标题", "type": "string", "required": True},
                {"key": "count", "label": "数量", "type": "number"},
            ],
            "slots": [
                {"key": "output", "label": "Output", "formats": ["html"], "required": True},
            ],
        }
        with open(tpl_dir / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump(manifest, f, allow_unicode=True)

        registry = TemplateRegistry(template_dirs=[tmp_path / "templates"])
        templates = registry.list_templates()
        assert len(templates) == 1
        assert templates[0]["id"] == "test.alpha"
        assert templates[0]["field_count"] == 2
        assert templates[0]["slot_count"] == 1
        assert templates[0]["theme_count"] == 0

    def test_load_multiple_templates(self, tmp_path: Path):
        """Load multiple templates from different directories."""
        for tid in ["alpha", "beta"]:
            tpl_dir = tmp_path / "templates" / f"test.{tid}"
            tpl_dir.mkdir(parents=True)
            with open(tpl_dir / "manifest.yaml", "w", encoding="utf-8") as f:
                yaml.dump({"id": f"test.{tid}", "name": f"Test {tid.title()}", "renderer": "r"}, f)

        registry = TemplateRegistry(template_dirs=[tmp_path / "templates"])
        templates = registry.list_templates()
        assert len(templates) == 2
        ids = [t["id"] for t in templates]
        assert "test.alpha" in ids
        assert "test.beta" in ids

    def test_load_theme_files(self, tmp_path: Path):
        """Load themes referenced in manifests."""
        tpl_dir = tmp_path / "templates" / "test.with-themes"
        tpl_dir.mkdir(parents=True)
        theme_dir = tpl_dir / "themes"
        theme_dir.mkdir()

        manifest = {
            "id": "test.with-themes",
            "name": "With Themes",
            "renderer": "r",
            "themes": [
                {"id": "dark", "name": "Dark", "file": "themes/dark.yaml"},
                {"id": "light", "name": "Light", "file": "themes/light.yaml"},
            ],
        }
        with open(tpl_dir / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump(manifest, f, allow_unicode=True)

        for theme_id, theme_name in [("dark", "Dark"), ("light", "Light")]:
            with open(theme_dir / f"{theme_id}.yaml", "w", encoding="utf-8") as f:
                yaml.dump({
                    "id": theme_id,
                    "name": theme_name,
                    "tokens": {"color.bg": "#000" if theme_id == "dark" else "#fff"},
                }, f)

        registry = TemplateRegistry(template_dirs=[tmp_path / "templates"])
        themes = registry.list_themes("test.with-themes")
        assert len(themes) == 2
        theme_ids = [t["id"] for t in themes]
        assert "dark" in theme_ids
        assert "light" in theme_ids

        # Get individual theme
        dark = registry.get_theme("test.with-themes", "dark")
        assert dark is not None
        assert dark.tokens["color.bg"] == "#000"

    def test_inspect_template(self, tmp_path: Path):
        """Inspect returns detailed template info."""
        tpl_dir = tmp_path / "templates" / "test.inspect-me"
        tpl_dir.mkdir(parents=True)

        with open(tpl_dir / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump({
                "id": "test.inspect-me",
                "name": "Inspect Me",
                "renderer": "r",
                "fields": [{"key": "x", "label": "X", "type": "number"}],
                "slots": [{"key": "out", "label": "Out", "formats": ["json"]}],
            }, f, allow_unicode=True)

        registry = TemplateRegistry(template_dirs=[tmp_path / "templates"])
        detail = registry.inspect_template("test.inspect-me")
        assert detail is not None
        assert detail["id"] == "test.inspect-me"
        assert len(detail["fields"]) == 1
        assert detail["fields"][0]["key"] == "x"

        # Non-existent template
        assert registry.inspect_template("nope") is None

    def test_render_template_missing(self, tmp_path: Path):
        """Rendering a non-existent template raises ValueError."""
        registry = TemplateRegistry(template_dirs=[tmp_path / "templates"])
        try:
            registry.render_template("ghost", {"x": "y"})
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown template" in str(e)
