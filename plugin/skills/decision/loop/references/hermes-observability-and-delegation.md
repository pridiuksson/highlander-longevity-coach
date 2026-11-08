# Hermes Native Solutions for Loop/Delegation Problems

Condensed from full Hermes docs (2.9MB, 62K lines). Maps previously unsolved problems to native Hermes features.

## Hook System (Shell + Plugin)

Three hook systems, all non-blocking:

| System | Location | Runs in | Can block tools |
|--------|----------|---------|-----------------|
| Shell hooks | `$HERMES_HOME/agent-hooks/` + `hooks:` in config.yaml | CLI + Gateway | Yes (`pre_tool_call`) |
| Plugin hooks | `ctx.register_hook()` in `$HERMES_HOME/plugins/` | CLI + Gateway | Yes (`pre_tool_call`) |
| Gateway hooks | `$HERMES_HOME/hooks/<name>/HOOK.yaml + handler.py` | Gateway only | No |

### Key hooks for subagent observability

| Hook event | When | Use case |
|-----------|------|----------|
| `subagent_stop` | After every `delegate_task` child | Log outcomes, capture summaries |
| `post_tool_call` | After every tool call | Full execution trace |
| `pre_tool_call` | Before every tool call | Block dangerous calls, enforce policy |
| `pre_llm_call` | Before LLM call each turn | Inject context into user message |
| `on_session_end` | Session teardown | Flush state, final logging |

### Shell hook JSON wire protocol

stdin receives JSON with: `hook_event_name`, `tool_name`, `tool_input`, `session_id`, `cwd`, `extra`.
stdout can return: `{"decision": "block", "reason": "..."}` or `{"context": "..."}` (for `pre_llm_call`).

## Kanban (Durable Task Board)

- Storage: `$HERMES_HOME/kanban.db` (SQLite)
- Workers: Named Hermes profiles with persistent memory
- Dispatcher sets outcome, not worker — eliminates Ralph Wiggum
- Fire-and-forget after create — no blocking wait
- Survives gateway restarts
- Board queryable via `kanban_show`, `kanban_list`, CLI, dashboard

### When Kanban beats delegate_task
- Multi-session tasks
- Named agents that accumulate memory over time
- Research triage (parallel researchers + analyst + writer)
- Engineering pipelines (decompose → parallel implement → review → iterate)
- Fleet work (one specialist managing N subjects)

## No-Agent Cron (`no_agent=true`)

Script-only cron jobs with zero LLM tokens:
- Script in `$HERMES_HOME/scripts/` (bash or python)
- Emit stdout → delivered as message. Empty stdout → silent.
- Same scheduler as LLM cron jobs (pause, resume, list, delivery targeting)
- Perfect for: watchdogs, pollers, threshold alerts, CI notifications, heartbeats

## Steer Mode

```yaml
display:
  busy_input_mode: "steer"
```

Injects message into current run after next tool call — no interrupt, no new turn.
Fallbacks: if agent hasn't started yet or images attached, falls back to "queue" behavior.

## Context Engine Plugins

Pluggable via `ContextEngine` ABC:
```yaml
context:
  engine: "compressor"  # default (lossy)
  engine: "lcm"         # plugin (lossless DAG)
```

Engine methods: `should_compress()`, `compress()`, `on_session_start()`, `on_session_end()`, `get_tool_schemas()`, `handle_tool_call()`.

## Plugin LLM Access

`ctx.llm.complete(prompt)` and `ctx.llm.complete_structured(prompt, schema)` let plugins borrow the user's active model + auth for one-shot completions. Useful for classification, extraction, and summarization within hooks.

## Key Config Locations

| Setting | File | Path |
|---------|------|------|
| Hooks | config.yaml | `hooks:` block |
| Busy mode | config.yaml | `display.busy_input_mode` |
| Context engine | config.yaml | `context.engine` |
| Memory provider | config.yaml | `memory.provider` |
| Cron jobs | JSON | `$HERMES_HOME/cron/jobs.json` |
| Kanban | SQLite | `$HERMES_HOME/kanban.db` |
| Shell hooks | Files | `$HERMES_HOME/agent-hooks/` |
| Gateway hooks | Dirs | `$HERMES_HOME/hooks/<name>/` |
