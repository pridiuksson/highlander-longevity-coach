#!/usr/bin/env bash
# Internal smoke test for longevity-coach plugin (maintainers only).
# NOT the contest demo video script: it uses Hermes internals and a temp HERMES_HOME.
# For the <90s judge demo, record a real Hermes UI session showing:
#   1) install/load plugin, 2) run "Run the longevity crunch in demo mode"
#      (or coach_run_crunch demo=true), 3) show weekly-crunch blueprint / ledger tool chain.
set -euo pipefail
HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-}"
[ -n "$HERMES_AGENT_DIR" ] && export PYTHONPATH="$HERMES_AGENT_DIR${PYTHONPATH:+:$PYTHONPATH}"
export HERMES_HOME="${HERMES_HOME:-/tmp/scratchpad/hermes-longevity-coach-smoke}"

echo "=== Internal smoke test (not a product demo) ==="
python3 - <<'PY'
import os
from hermes_cli.plugins import PluginManager
from tools.registry import registry
from tools.skills_tool import skill_view

pm = PluginManager(); pm.discover_and_load()
assert 'coach_run_crunch' in registry.get_all_tool_names(), 'coach_run_crunch missing'
out = registry.dispatch('coach_run_crunch', {'demo': True, 'text': 'I feel exhausted and overwhelmed'})
print(out)
assert '[DEMO / SYNTHETIC DATA' in str(out), 'demo banner missing'
r = skill_view('longevity-coach:grill')
assert 'grill' in str(r).lower(), 'skill view failed'
print('OK: plugin loaded, demo crunch returned synthetic output, qualified skill loads')
PY

