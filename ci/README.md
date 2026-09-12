# CI

`leak-gate.yml` is the leak gate as a GitHub Actions workflow. It is **active**: the same file is
installed at `.github/workflows/leak-gate.yml` and runs on every push and pull request.

It scans the tree, validates the skills tree, and scans the full git history. That matters because
the pre-commit hook is client-side and bypassable with `--no-verify`; CI is the version that
actually enforces anything.

## Keeping the two copies in sync

`.github/workflows/leak-gate.yml` is the live workflow; this file is its source. Edit here first,
then copy:

```bash
mkdir -p .github/workflows
cp ci/leak-gate.yml .github/workflows/
```

Commit both. Enabling it the first time required a token with the `workflow` scope — the publishing
automation deliberately does not hold one, which is why the file also lives here.

**Leave this copy in `ci/`.** If you delete it, the next person cannot tell the workflow was ever
optional, or where to edit it.
