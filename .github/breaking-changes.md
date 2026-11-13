Breaking changes

The PDF file name is no longer taken from the JSON file name. `resume.json` writes `[Name]-Resume.pdf` (or `Resume.pdf` with no name). Any other input except `alex.json` adds the JSON file name, so `examples/new-grad.json` writes `examples/Alex-Doe-Resume-new-grad.pdf`. In v0.0.1 the same commands wrote `resume.pdf` and `examples/new-grad.pdf`.

A job with `"engineering": false` now prints its bullets on a resume, unless the resume has an engineering job and the rest of the resume fills the page. Then that job drops to one line. In v0.0.1 those bullets were always left out of a resume.
