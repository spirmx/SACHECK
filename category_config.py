import importlib.util
import pprint
from pathlib import Path


def load_category_module(category_path: Path):
    if not category_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("sacheck_user_category", category_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_category_config(category_path: Path, categories, extension_types, url_rules, icon_dir):
    content = (
        '"""Editable category definitions for SACHECK.\n\n'
        "Add new work categories here. Put optional category icon images in:\n"
        'assets/category_icons/<icon_file>\n"""\n\n'
        f"CATEGORY_ICON_DIR = {icon_dir!r}\n\n"
        f"CATEGORIES = {pprint.pformat(categories, width=120, sort_dicts=False)}\n\n"
        f"EXTENSION_TYPES = {pprint.pformat(extension_types, width=120, sort_dicts=False)}\n\n"
        f"URL_RULES = {pprint.pformat(url_rules, width=120, sort_dicts=False)}\n"
    )
    category_path.write_text(content, encoding="utf-8")
    return category_path
