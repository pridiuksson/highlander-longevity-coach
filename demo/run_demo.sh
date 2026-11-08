#!/usr/bin/env bash
# Demo script for longevity-coach plugin (90s video).
# Run from repo root with a Hermes install on PATH.
HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-}"
[ -n "$HERMES_AGENT_DIR" ] && export PYTHONPATH="$HERMES_AGENT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "=== 1. Plugin loads ==="
HERMES_HOME=/tmp/scratchpad/hermes-test python3 -c "
import os, sys
os.environ['HERMES_HOME']='/tmp/scratchpad/hermes-test'
from hermes_cli.plugins import PluginManager
pm = PluginManager(); pm.discover_and_load()
from tools.registry import registry
print('OK: plugin loaded, coach_run_crunch registered:', 'coach_run_crunch' in registry.get_all_tool_names())
"

echo ""
echo "=== 2. Skill loads (qualified name) ==="
HERMES_HOME=/tmp/scratchpad/hermes-test python3 -c "
import os, sys
from tools.skills_tool import skill_view
r = skill_view('longevity-coach:grill')
print('OK: longevity-coach:grill loaded,', len(str(r)), 'chars')
"

echo ""
echo "=== 3. Manual crunch trigger (produces recommendation) ==="
HERMES_HOME=/tmp/scratchpad/hermes-test python3 -c "
import os, sys
os.environ['HERMES_HOME']=os.environ.get('HERMES_HOME','/tmp/scratchpad/hermes-test')
from hermes_cli.plugins import PluginManager
pm = PluginManager(); pm.discover_and_load()
from tools.registry import registry
print(registry.dispatch('coach_run_crunch', {'text': 'I feel exhausted and overwhelmed'}))
"
