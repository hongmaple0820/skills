"""
Template Registry.

Loads, lists, inspects, and orchestrates template rendering.
Aligns with Phase 1 of the implementation roadmap.
"""

from pathlib import Path

import yaml

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable

from src.templates.models import TemplateManifest, ThemeManifest


@dataclass
class RenderResult:
    """Standard result from a template renderer adapter."""
    template_id: str
    theme_id: str
    output_dir: str
    artifacts: Dict[str, str]
    extra: Optional[Dict[str, Any]] = None


# Default template directories to scan
TEMPLATE_DIRS = [
    Path("templates"),
]


class TemplateRegistry:
    """Registry of installed templates loaded from YAML manifests."""

    def __init__(self, template_dirs: Optional[List[Path]] = None):
        self._templates: Dict[str, TemplateManifest] = {}
        self._themes: Dict[str, Dict[str, ThemeManifest]] = {}  # template_id -> {theme_id -> ThemeManifest}
        self._renderers: Dict[str, Callable] = {}
        self._template_dirs = template_dirs or TEMPLATE_DIRS
        self._loaded = False

    def register_renderer(self, key: str, render_fn: Callable) -> None:
        """Register a renderer function by key (e.g. daily_renderer)."""
        self._renderers[key] = render_fn

    def load_all(self) -> None:
        """Scan template directories and load all manifests."""
        self._templates.clear()
        self._themes.clear()

        for template_dir in self._template_dirs:
            if not template_dir.is_dir():
                continue
            for manifest_path in template_dir.rglob("manifest.yaml"):
                self._load_manifest(manifest_path)
        self._loaded = True

    def _load_manifest(self, manifest_path: Path) -> None:
        """Load a single template manifest and its theme files."""
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Failed to load manifest {manifest_path}: {e}")

        if not data or "id" not in data:
            raise ValueError(f"Invalid manifest (missing 'id'): {manifest_path}")

        manifest = TemplateManifest(**data)
        manifest._manifest_dir = manifest_path.parent
        self._templates[manifest.id] = manifest

        # Load themes
        theme_dir = manifest_path.parent / "themes"
        theme_map: Dict[str, ThemeManifest] = {}
        if theme_dir.is_dir():
            for theme_file in theme_dir.iterdir():
                if theme_file.suffix in (".yaml", ".yml"):
                    try:
                        with open(theme_file, "r", encoding="utf-8") as f:
                            theme_data = yaml.safe_load(f)
                        if theme_data and "id" in theme_data:
                            theme = ThemeManifest(**theme_data)
                            theme_map[theme.id] = theme
                    except Exception as e:
                        raise ValueError(f"Failed to load theme {theme_file}: {e}")

        self._themes[manifest.id] = theme_map

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all loaded templates with summary info."""
        if not self._loaded:
            self.load_all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description or "",
                "version": t.version,
                "author": t.author or "",
                "field_count": len(t.fields),
                "slot_count": len(t.slots),
                "theme_count": len(self._themes.get(t.id, {})),
                "renderer": t.renderer,
                "tags": t.tags,
            }
            for t in sorted(self._templates.values(), key=lambda x: x.id)
        ]

    def get_template(self, template_id: str) -> Optional[TemplateManifest]:
        """Get a template manifest by ID."""
        if not self._loaded:
            self.load_all()
        return self._templates.get(template_id)

    def get_theme(self, template_id: str, theme_id: str) -> Optional[ThemeManifest]:
        """Get a theme by template and theme ID."""
        if not self._loaded:
            self.load_all()
        theme_map = self._themes.get(template_id, {})
        return theme_map.get(theme_id)

    def list_themes(self, template_id: str) -> List[Dict[str, Any]]:
        """List all themes for a template (returns dict summaries)."""
        if not self._loaded:
            self.load_all()
        theme_map = self._themes.get(template_id, {})
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description or "",
                "token_count": len(t.tokens),
            }
            for t in sorted(theme_map.values(), key=lambda x: x.id)
        ]

    def list_theme_manifests(self, template_id: str) -> List[ThemeManifest]:
        """List all themes for a template (returns ThemeManifest objects)."""
        if not self._loaded:
            self.load_all()
        theme_map = self._themes.get(template_id, {})
        return sorted(theme_map.values(), key=lambda x: x.id)

    def inspect_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a template."""
        manifest = self.get_template(template_id)
        if not manifest:
            return None
        return {
            "id": manifest.id,
            "name": manifest.name,
            "description": manifest.description or "",
            "version": manifest.version,
            "author": manifest.author or "",
            "tags": manifest.tags,
            "renderer": manifest.renderer,
            "fields": [f.model_dump() for f in manifest.fields],
            "slots": [s.model_dump() for s in manifest.slots],
            "outputs": [o.model_dump() for o in manifest.outputs],
            "themes": self.list_themes(template_id),
        }

    def render_template(
        self,
        template_id: str,
        input_data: Dict[str, Any],
        *,
        theme_id: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Render a template with given input data.

        Returns a dict with render results keyed by slot/output key.
        """
        manifest = self.get_template(template_id)
        if not manifest:
            raise ValueError(f"Unknown template: {template_id}")

        # Validate fields
        errors = manifest.validate_fields(input_data)
        if errors:
            raise ValueError(f"Validation failed for template '{template_id}':\n" + "\n".join(errors))

        # Resolve theme
        resolved_theme = None
        if theme_id:
            theme = self.get_theme(template_id, theme_id)
            if not theme:
                raise ValueError(f"Unknown theme '{theme_id}' for template '{template_id}'")
            resolved_theme = theme
        elif manifest.themes:
            # Use first theme as default
            first_theme_ref = manifest.themes[0]
            resolved_theme = self.get_theme(template_id, first_theme_ref["id"])

        # Find renderer
        render_fn = self._renderers.get(manifest.renderer)
        if not render_fn:
            raise ValueError(f"No renderer registered for '{manifest.renderer}' (template: {template_id})")

        # Call renderer
        result = render_fn(
            manifest=manifest,
            input_data=input_data,
            theme=resolved_theme,
            output_dir=output_dir or Path("data/reports"),
        )
        return result
