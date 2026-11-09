# Contributing

Anyone can open an issue or a pull request. Be kind and keep it on topic.

## Opening a pull request

1. Fork the repository and branch from `main`.
2. Make one change per pull request.
3. Run the checks:

```sh
pip install ruff==0.16.9
ruff format --check
ruff check
shellcheck run .github/check-pdfs.sh
./run --yes examples/alex.json
```

`build.py` is formatted and linted with [ruff](https://docs.astral.sh/ruff/), configured in `pyproject.toml`. Run `ruff format` to fix formatting. Run the `shellcheck` line only if you changed `run` or `.github/check-pdfs.sh`.

4. Open a pull request into `main`. Fill in the template, and write `Part of #N` if there is an issue.

Keep examples made-up and neutral, such as Alex Doe with they and them. Never add real personal data or invent resume content.

## Releases and merges

All four repos (eeprep, resume-generator, edwardasilva, information) are on the 0.0.x beta line, and the current release is `v0.0.1`. A release bumps only the last number. Each release is exactly one commit on `main`. `v0.0.1` is a single commit with no parent. Each later release is one squashed commit whose parent is the previous release commit, tagged `vX.Y.Z` with an annotated tag whose message is `<repo> vX.Y.Z`. Pushing the tag makes CI build and check every resume and attach the zip and a sample PDF to the GitHub release. Every merge is a squash merge. `protect-main` is paused only while the release commit is pushed, and turned back on right after.

## Claude Code

Claude Code can take an issue to a pull request. Add the `claude` label to an issue, or comment `@claude` on an issue or a pull request, and `.github/workflows/claude.yml` runs it. Only the repo owner can start it. Claude works on a `claude/` branch, opens a pull request that closes the issue, and answers review comments that mention `@claude`. It never merges, pushes to `main`, tags, or cuts a release. The owner squash-merges each pull request, and a merge does not cut a release.

## CI

CI runs the same checks, builds every file in `examples/` with `./run`, and fails if any PDF isn't exactly one page, uses a font that isn't in `fonts/`, or doesn't pass the text check. Release tags, a monthly run, and a manual run (`gh workflow run build.yml --ref main`) also build them on a bare TeX Live with no font packages and on macOS with BasicTeX. Pull requests skip those two slower jobs.
