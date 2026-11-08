"""Registration contract test for the longevity-coach plugin.

Verifies that register(ctx) registers exactly the tools/hooks declared in
plugin.yaml (capability probe gate), plus the bundled skills and blueprint.
Happy path only.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugin"


def _read_provides_tools():
    """Parse provides_tools from plugin.yaml without a YAML dependency."""
    lines = (PLUGIN_DIR / "plugin.yaml").read_text().splitlines()
    tools = []
    in_tools = False
    for line in lines:
        if line.strip() == "provides_tools:":
            in_tools = True
            continue
        if in_tools:
            stripped = line.strip()
            if stripped.startswith("- "):
                tools.append(stripped[2:].strip())
            elif stripped == "" or stripped.startswith("#"):
                continue
            else:
                # new top-level key
                if not line.startswith(" ") and not line.startswith("\t"):
                    break
                # indented non-list means end of list
                if not stripped.startswith("-"):
                    break
    return tools


class _FakeCtx:
    def __init__(self):
        self.tools = []
        self.skills = []
        self.blueprints = []
        self.hooks = []

    def register_tool(self, name, toolset, schema, handler, **kw):
        self.tools.append(name)

    def register_skill(self, name, path, **kw):
        self.skills.append(name)

    def register_automation_blueprint(self, key, **kw):
        self.blueprints.append(key)

    def register_hook(self, name, fn, **kw):
        self.hooks.append(name)


def _load_plugin():
    spec = importlib.util.spec_from_file_location("longevity_coach_plugin", PLUGIN_DIR / "__init__.py",
                                                  submodule_search_locations=[str(PLUGIN_DIR)])
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["longevity_coach_plugin"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_registration_matches_manifest():
    declared = set(_read_provides_tools())
    plugin = _load_plugin()
    ctx = _FakeCtx()
    plugin.register(ctx)

    registered = set(ctx.tools)
    assert registered == declared, f"tool mismatch: declared={declared} registered={registered}"

    assert len(ctx.skills) == 9, f"expected 9 bundled skills, got {len(ctx.skills)}: {ctx.skills}"
    assert "weekly-crunch" in ctx.blueprints, f"blueprint not registered: {ctx.blueprints}"