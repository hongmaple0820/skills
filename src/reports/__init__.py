"""Report rendering utilities.

Provides the shared registry singleton that wires template manifests
to their corresponding renderer implementations.
"""

from src.reports.daily_renderer import (
    list_themes,
    render_daily_report,
    render_theme_preview_gallery,
    register_daily_adapter,
)
from src.reports.wechat_renderer import (
    list_wechat_themes,
    render_wechat_article,
    register_wechat_adapter,
)

__all__ = [
    "list_themes",
    "list_wechat_themes",
    "render_daily_report",
    "render_theme_preview_gallery",
    "render_wechat_article",
    "get_registry",
    "setup_registry",
]

# ── Shared singleton registry ──
import threading

_lock = threading.Lock()
_registry: "TemplateRegistry | None" = None


def get_registry() -> "TemplateRegistry":
    """Get the shared template registry, creating and wiring it on first access."""
    global _registry
    if _registry is None:
        with _lock:
            # Double-check inside lock
            if _registry is None:
                from src.templates.registry import TemplateRegistry

                _registry = TemplateRegistry()
                _registry.load_all()
                register_daily_adapter(_registry)
                register_wechat_adapter(_registry)
    return _registry


def setup_registry() -> "TemplateRegistry":
    """Explicitly initialize and return the shared registry."""
    return get_registry()
