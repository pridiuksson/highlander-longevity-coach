# CI

`leak-gate.yml` is the leak gate as a GitHub Actions workflow. It is **not active by default** —
it lives here rather than in `.github/workflows/` because activating it requires a token with the
`workflow` scope, and the automation that populates this repo deliberately does not hold one.

However you obtain the file, enabling it is a copy:

```bash
mkdir -p .github/workflows
cp ci/leak-gate.yml .github/workflows/
git add .github/workflows/leak-gate.yml
git commit -m "ci: enable the leak gate"
git push
```

Once enabled it runs on every push and pull request, scanning the tree **and the full git
history**. That matters because the pre-commit hook is client-side and bypassable with
`--no-verify`; CI is the version that actually enforces anything.

**Leave the copy in `ci/`.** If you delete it, the next person has no workflow to enable and the
reason it is inactive is no longer discoverable.
