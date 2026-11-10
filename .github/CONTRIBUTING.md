# Contributing

Thanks for helping with resume-generator. Ideas and fixes are welcome.

## Suggest an idea or a fix

Open an [issue](https://github.com/edwardasilva/resume-generator/issues/new/choose) and pick a template. Say what you would change and why.

## Open a pull request

1. Fork the repo (or cut a short branch if you have write access).
2. Make one change. Keep the pull request small.
3. Before you push:

```bash
pip install ruff==0.16.9
ruff format
ruff check
./run examples/alex.json
```

If you change a file in `examples/`, commit its rebuilt PDF. Otherwise discard the rebuilt PDFs with `git restore examples/`.

CI builds every file in `examples/` and fails if any PDF is not exactly one page. Merges are squash merges.

## Coding agents

Use the `gemini` label, or comment `@gemini-cli`, for easy tasks: low severity, small, one or two files, docs, wording, config, tests, or polish.

Use the `claude` label, or comment `@claude`, for harder work: medium or high severity, multi-file changes, design, security, workflows, or anything that needs judgment.

Only the repository owner can start either workflow. Both work on a branch and open a pull request. Neither pushes to `main`, merges, tags, or cuts a release.

## Releases

Before cutting a release, run release-cut and land or close every `release-sweep` issue.

## Conduct

Be kind and assume good intent. To report a problem with someone's behavior, use GitHub's Report content feature or message the repository owner in private.

To report a vulnerability, use GitHub's private vulnerability reporting on this repository. Do not open a public issue.

## License

By contributing, you agree that your code is licensed under the [MIT License](../LICENSE) and your content (the examples and the docs) under [CC BY 4.0](../LICENSE-CONTENT). The fonts in `fonts/` keep their own licenses. Reuse of content is credited to [resume-generator contributors](https://github.com/edwardasilva/resume-generator).
