"""Pure library modules wrapping the plugin's skill scripts for in-process tool use.

The ``_ledger_impl``, ``_triage_impl``, and ``_recovery_impl`` modules are vendored
copies of the corresponding skill scripts (skills/proactive/proactive-coach/scripts/ledger.py,
skills/decision/stress-dialogue/scripts/dialogue_triage.py,
skills/health/biometric-recovery-ledger/scripts/rebound_tracker.py). They are duplicated
here so the plugin is self-contained when installed from the catalog (the plugin
directory is cloned in isolation). Keep them in sync when the source scripts change.
"""
