# Contributing

Thanks for helping with resume-generator. Ideas and fixes are welcome.

## Suggest an idea or a fix

Open an [issue](https://github.com/edwardasilva/resume-generator/issues/new/choose) and describe what you would change and why. A short description is all it needs.

## Open a pull request

1. Fork the repo (or cut a short branch if you have write access).
2. Make one change. Keep the pull request small.
3. If you can, run these before you push:

```bash
pip install ruff==0.16.9
ruff format
ruff check
./run examples/alex.json
bash tests/check.sh
```

`tests/check.sh` needs LuaLaTeX and poppler-utils. If you change `run` or a script, also run `shellcheck` on it.

If you change a file in `examples/`, commit its rebuilt PDF. Otherwise discard the rebuilt PDFs with `git restore examples/`. If `examples/Alex-Doe-Resume.pdf` changes, rebuild `examples/alex-doe-resume.png` with `pdftoppm -png -r 80 -singlefile examples/Alex-Doe-Resume.pdf examples/alex-doe-resume`.

Every resume PDF in `examples/` must stay exactly one page. A CV PDF (`*-CV.pdf`) may take one or two, and `examples/Alex-Doe-CV.pdf` must stay exactly two. If you skip the checks, maintainers run them before merging.

4. Open a pull request into `main` with a short description of what changed and why. That is all a pull request needs. An issue link is optional. Maintainers review the change.

## Coding agents

Use the `gemini` label, or comment `@gemini-cli`, for easy tasks: low severity, small, one or two files, docs, wording, config, tests, or polish.

Use the `claude` label, or comment `@claude`, for harder work: medium or high severity, multi-file changes, design, security, workflows, or anything that needs judgment.

Only the repository owner can start either workflow. Both work on a branch and open a pull request. Neither pushes to `main`, merges, tags, or cuts a release.

## Releases

Only the repository owner cuts releases.

Release notes are the notes GitHub generates from pull requests, plus a Breaking changes line written by hand when there is one. There is no CHANGELOG file. Put the Breaking changes text in `.github/breaking-changes.md` before cutting the tag; the release workflow prepends it to the generated notes. After the release, clear that file or replace it with the next breaking change.

## Conduct

Be kind and assume good intent. To report a problem with someone's behavior, use GitHub's Report content feature or message the repository owner in private.

To report a vulnerability, use GitHub's private vulnerability reporting on this repository. Do not open a public issue.

## License

By contributing, you agree that your code is licensed under the [MIT License](../LICENSE) and your content (the examples and the docs) under [CC BY 4.0](../LICENSE-CONTENT). The fonts in `fonts/` keep their own licenses. Reuse of content is credited to [resume-generator contributors](https://github.com/edwardasilva/resume-generator).
