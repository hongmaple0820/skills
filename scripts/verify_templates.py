"""Quick script to verify template manifests load correctly."""
import sys
import os

# Ensure project root is on the path so "from src..." imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.templates.registry import TemplateRegistry

registry = TemplateRegistry()
templates = registry.list_templates()
for t in templates:
    print(f'  [{t["id"]}] {t["name"]} (fields={t["field_count"]}, themes={t["theme_count"]}, renderer={t["renderer"]})')
    if t['theme_count'] > 0:
        themes = registry.list_themes(t['id'])
        for th in themes:
            print(f'    theme: {th["id"]} ({th["name"]}, tokens={th["token_count"]})')

if not templates:
    print("ERROR: No templates found!")
    import sys
    sys.exit(1)
