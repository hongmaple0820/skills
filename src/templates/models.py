"""
Template Manifest Models.

Defines the schema for template manifests, fields, slots, outputs, and themes.
Aligns with Section 5 of the workflow-platform-design document.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


class TemplateFieldType:
    """Supported field types for template fields."""
    STRING = "string"
    TEXT = "text"
    IMAGE = "image"
    COLOR = "color"
    NUMBER = "number"
    SELECT = "select"
    BOOLEAN = "boolean"
    DATE = "date"


class TemplateField(BaseModel):
    """A single editable field in a template."""
    key: str = Field(..., description="Field identifier (snake_case)")
    type: str = Field(default="string", description="Field type: string, text, image, color, number, select, boolean, date")
    label: str = Field(..., description="Human-readable label")
    description: Optional[str] = None
    required: bool = False
    default: Any = None
    placeholder: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None  # For select type: [{label, value}, ...]
    validation: Optional[Dict[str, Any]] = None  # e.g. {min_length: 1, max_length: 100}
    group: Optional[str] = None  # Field group for UI organization


class TemplateSlot(BaseModel):
    """An output slot that a template can produce."""
    key: str = Field(..., description="Slot identifier (snake_case)")
    label: str = Field(..., description="Human-readable label")
    description: Optional[str] = None
    formats: List[str] = Field(default_factory=lambda: ["html"], description="Output formats: html, svg, png, json, txt")
    output_path: Optional[str] = None  # e.g. "poster.png" (relative to render output dir)
    required: bool = False


class TemplateOutput(BaseModel):
    """Declared output artifact of a template render."""
    key: str = Field(..., description="Output identifier")
    label: str = Field(..., description="Human-readable label")
    path_template: Optional[str] = None  # e.g. "{date}-{theme}-poster.png"
    format: str = Field(default="html", description="Output format")


class ThemeManifest(BaseModel):
    """A theme definition loaded from a YAML file."""
    id: str = Field(..., description="Theme identifier")
    name: str = Field(..., description="Theme display name")
    description: Optional[str] = None
    tokens: Dict[str, Any] = Field(default_factory=dict, description="Theme token values")

    def to_flat_dict(self, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Convert dotted tokens to a flat dict using an explicit key mapping.

        Args:
            mapping: Maps dotted token keys (e.g. 'color.bg_start') to
                     flat dict keys (e.g. 'bg_start').

        Returns:
            Flat dict with mapped keys + 'name', 'description'.
        """
        result: Dict[str, Any] = {
            "name": self.name,
            "description": self.description or "",
        }
        for token_key, flat_key in mapping.items():
            if token_key in self.tokens:
                result[flat_key] = self.tokens[token_key]
        return result


class TemplateManifest(BaseModel):
    """Top-level manifest for a template package."""
    id: str = Field(..., description="Unique template identifier (e.g. daily.report)")
    name: str = Field(..., description="Template display name")
    description: Optional[str] = None
    version: str = Field(default="1.0.0")
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Template definition
    fields: List[TemplateField] = Field(default_factory=list)
    slots: List[TemplateSlot] = Field(default_factory=list)
    outputs: List[TemplateOutput] = Field(default_factory=list)

    # Theme references
    themes: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Theme references: [{id, name, file}, ...]",
    )

    # Renderer binding
    renderer: str = Field(..., description="Renderer key (e.g. daily_renderer, wechat_renderer)")

    # Metadata
    preview_image: Optional[str] = None
    category: Optional[str] = None

    # Internal: populated at load time
    _manifest_dir: Optional[Path] = None

    def get_field(self, key: str) -> Optional[TemplateField]:
        """Get a field by key."""
        for f in self.fields:
            if f.key == key:
                return f
        return None

    def get_slot(self, key: str) -> Optional[TemplateSlot]:
        """Get a slot by key."""
        for s in self.slots:
            if s.key == key:
                return s
        return None

    def validate_fields(self, input_data: Dict[str, Any]) -> List[str]:
        """Validate input data against field definitions. Returns list of error messages."""
        errors: List[str] = []
        for field in self.fields:
            value = input_data.get(field.key)
            if field.required and (value is None or value == ""):
                errors.append(f"Field '{field.key}' ({field.label}) is required")
                continue
            if value is not None:
                if field.type == TemplateFieldType.STRING and isinstance(value, str):
                    if field.validation:
                        min_len = field.validation.get("min_length", 0)
                        max_len = field.validation.get("max_length")
                        if len(value) < min_len:
                            errors.append(f"Field '{field.key}' must be at least {min_len} characters")
                        if max_len and len(value) > max_len:
                            errors.append(f"Field '{field.key}' must be at most {max_len} characters")
                if field.type == TemplateFieldType.NUMBER:
                    try:
                        float(value)
                    except (TypeError, ValueError):
                        errors.append(f"Field '{field.key}' must be a number")
                if field.type == TemplateFieldType.SELECT and field.options:
                    valid_values = {o.get("value", o.get("label")) for o in field.options}
                    if str(value) not in valid_values:
                        errors.append(
                            f"Field '{field.key}' must be one of: {', '.join(valid_values)}"
                        )
        return errors
