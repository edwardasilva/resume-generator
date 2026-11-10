# Rules for the coding agent

This repo builds one-page resume PDFs from a JSON file. Read `README.md` and `.github/CONTRIBUTING.md` before you change anything, and follow them. The rules below are the same ones that apply to every coding agent in this repo.

## Routing

Use the `gemini` label, or comment `@gemini-cli`, for easy tasks: low severity, small, one or two files, docs, wording, config, tests, or polish.

Use the `claude` label, or comment `@claude`, for harder work: medium or high severity, multi-file changes, design, security, workflows, or anything that needs judgment.

Only the repository owner can start either workflow. Both work on a branch and open a pull request. Neither pushes to `main`, merges, tags, or cuts a release.

## Git

- Work on a branch. Never push to `main`.
- Every change reaches `main` through a pull request, and every merge is a squash merge. Only the repository owner merges.
- The pull request body names its issue on its own line, as `Part of #N`. Add `Closes #N` when the pull request finishes the issue.
- Keep each pull request to one change.
- Do not create tags. Do not force-push or rewrite pushed history.
- A release is cut only when the repository owner says so.

## Writing and data

- No emoji anywhere: files, commits, pull requests, comments, or output.
- Do not put bot or tool names in repo text or commit messages.
- Keep examples neutral, such as Alex Doe with they and them.
- Never invent resume content. The examples use made-up people.

## Checks

Before you push:

```bash
pip install ruff==0.16.9
ruff format
ruff check
```

Run `shellcheck` on `run` and `.github/check-pdfs.sh` if you touch either script. CI builds every file in `examples/` and fails if any PDF is not exactly one page.

## Secrets

Never print or commit secrets, tokens, or environment variables.
