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

CI builds every file in `examples/` and fails if any PDF is not exactly one page. Merges are squash merges.

## Conduct

Be kind and assume good intent. To report a problem with someone's behavior, use GitHub's Report content feature or message the repository owner in private.

To report a vulnerability, use GitHub's private vulnerability reporting on this repository. Do not open a public issue.

## License

By contributing, you agree that code is licensed under the [MIT License](../LICENSE). The fonts in `fonts/` keep their own licenses.
