Breaking changes

The PDF file name is no longer taken from the JSON file name. `resume.json` writes `[Name]-Resume.pdf` (or `Resume.pdf` with no name). Any other input except `alex.json` adds the JSON file name, so `examples/new-grad.json` writes `examples/Alex-Doe-Resume-new-grad.pdf`. In v0.0.1 the same commands wrote `resume.pdf` and `examples/new-grad.pdf`.
