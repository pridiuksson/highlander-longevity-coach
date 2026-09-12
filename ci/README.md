# CI

The leak gate runs as a GitHub Actions workflow at `.github/workflows/leak-gate.yml`, on every push
and pull request. It scans the tree (with its secrets pass), validates the skills tree, scans the
full history for identity/path/health patterns, and runs a separate full-history `gitleaks` pass.
That matters because the pre-commit hook is client-side and bypassable with `--no-verify`; CI is the
version that actually enforces anything.

## Why a copy once lived in this directory

Activating a workflow needs a token with the `workflow` scope, and GitHub refuses to let a token
without it create or update anything under `.github/workflows/`. The automation that first populated
this repo deliberately did not hold that scope, so the workflow was shipped inert as
`ci/leak-gate.yml` and enabled by hand.

That file has been removed. One copy under `.github/workflows/` is now the only copy — edit it in
place. The duplicate had already started to drift: the live workflow gained a full-history
`gitleaks` step that the `ci/` copy never had.
