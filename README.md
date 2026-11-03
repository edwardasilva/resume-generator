# resume-generator

Turn one JSON file into a clean, one-page PDF resume. The owner writes the content in `resume.json`, and the script handles the layout and fits it onto a single page.

This project is a companion to [eeprep.com](https://eeprep.com). It was built for engineering students and follows the advice on [eeprep's resume page](https://eeprep.com/get-hired/resume/), but it works for any field. See a sample: [examples/alex.pdf](examples/alex.pdf).

## Download

Get the latest zip from the [releases page](https://github.com/edwardasilva/resume-generator/releases/latest), unzip it, edit `resume.json` (see the field guide below) and run `./run`. It writes `resume.pdf`.

`./run` needs Python 3 and LuaLaTeX. If either is missing, it says what it will install and asks before it uses `sudo`. It supports Fedora (dnf), Debian, Ubuntu and WSL (apt), and macOS (Homebrew). Run `./run --yes` to skip the question. The fonts come with the project in `fonts/`, so no font packages are needed, and the PDF looks the same on every system.

To work from the repository instead, clone it and run `./run`. The first run copies `examples/alex.json` to `resume.json`, which is ignored by git along with `resume.pdf`, so personal details stay out of the repository.

To build any other file, pass it as an argument: `./run examples/new-grad.json` writes `examples/new-grad.pdf` next to it.

## Examples

Each example in `examples/` is a made-up resume and the PDF built from it, from nearly empty to completely full.

| File | Who it describes | PDF |
| --- | --- | --- |
| `alex.json` | The starting point, matching the finished example on eeprep's resume page: a student graduating in 2027 with two projects, a one-line job, and two skill lines whose every tool appears in a bullet. `[X]` marks a number the owner measures. | [alex.pdf](examples/alex.pdf) |
| `first-year.json` | A first-year student with one class project, a one-line retail job and a few skills. The page has room left at the bottom. | [first-year.pdf](examples/first-year.pdf) |
| `sophomore.json` | A second-year student with two projects, an electrical lead role in a robotics club and a one-line job. | [sophomore.pdf](examples/sophomore.pdf) |
| `new-grad.json` | A new graduate with two internships, two projects and certifications. They lead with experience and use the `times` font. | [new-grad.pdf](examples/new-grad.pdf) |
| `packed.json` | A graduating student with three engineering roles, a one-line job, three projects and long skill lists, in the `arial` font. The script tightens it to fit. | [packed.pdf](examples/packed.pdf) |

## Field guide

JSON doesn't allow comments, so this section explains each field. A blank field (`""`) or an empty list (`[]`) is left out of the PDF.

The phone, email, LinkedIn, GitHub and website in the header are links. The email opens a new message and the phone number dials. Any entry can also have a link:

| Field | What to put | Example |
| --- | --- | --- |
| `url` | Optional on any education, project or experience entry. The school, project title or employer becomes a link, shown in the normal text color. To link a skill, coursework or activity item, write it as `{"name": "...", "url": "..."}`. Inside a bullet, `[text](url)` links the text. Links must be web addresses (`https://` is added if missing), `mailto:` or `tel:`. | `github.com/alex-doe-example/cubesat-buck-converter` |

### `settings`

| Field | What to put | Example |
| --- | --- | --- |
| `sectionOrder` | Order of the sections. Lead with the owner's strongest one. | `["education", "projects", "experience", "skills"]` |
| `font` | One of the three fonts below. Leave it out to use `libertinus`. | `"libertinus"` |
| `dateStyle` | The date style for each section: `semester` (Fall 2025) or `month` (Sep 2025). Every date in a section must use that section's style. The build stops if one doesn't. A section left out uses `semester`. | `{"education": "semester", "projects": "semester", "experience": "month"}` |

Common orders: students with no engineering job usually go education, projects, experience, skills. Once they have an engineering internship, try experience first. School terms suit education and projects. Jobs usually use months.

Acceptable fonts for `settings.font`:

| Value | Font | Looks like |
| --- | --- | --- |
| `libertinus` | Libertinus Serif (default) | A classic book serif |
| `times` | TeX Gyre Termes | A free version of Times New Roman |
| `arial` | TeX Gyre Heros | A free version of Arial and Helvetica |

### `header`

| Field | What to put | Example |
| --- | --- | --- |
| `name` | The name they want recruiters to use. | `Alex Doe` |
| `phone` | Their phone number. No label such as "Cell:". | `(555) 555-0142` |
| `email` | An address they check every day. A school address is fine. | `alex.doe@example.com` |
| `linkedin` | Their profile URL without `https://`. | `linkedin.com/in/alex-doe-example` |
| `github` | Only if it holds work they're proud of. | `github.com/alex-doe-example` |
| `website` | A personal site or portfolio, if they have one. | `example.com/~sam-doe` |
| `location` | City and state. | `Springfield, ST` |
| `relocate` | `true` adds "Willing to relocate". | `true` |

### `education`

A list. Most students have one entry. Add a second for a master's degree.

| Field | What to put | Example |
| --- | --- | --- |
| `degree` | Degree and major. | `B.S. Electrical Engineering` |
| `gpa` | `N.NN/4.00`. List it when a posting sets a minimum they meet. | `3.62/4.00` |
| `school` | Their university. | `Example State University` |
| `gradDate` | Their graduation date, in the education date style. Add "Expected" if they haven't graduated. | `Expected Spring 2027` |
| `coursework` | Upper-level courses that match the jobs they want. | `["Power Electronics", "Embedded Systems"]` |
| `activities` | Clubs and honor societies. Put real build work in `projects`. | `["IEEE student branch"]` |

### `projects`

A list, best project first. This is where most students show what they can do.

| Field | What to put | Example |
| --- | --- | --- |
| `title` | A plain name for what they built. Don't use the word "project". | `FPGA Audio Equalizer` |
| `tools` | Tools, languages and parts they actually used. Shown in parentheses after the title, like `CubeSat Power Board (KiCad, LTspice)`. | `["Verilog", "Vivado", "MATLAB"]` |
| `start`, `end` | Dates in the projects date style. A blank `end` or `Present` means ongoing. Matching dates show once. | `Spring 2025` |
| `bullets` | One to four lines on what they did and what happened. | see below |
| `hide` | `true` leaves the entry out without deleting it. | `true` |

### `experience`

A list, most recent first.

| Field | What to put | Example |
| --- | --- | --- |
| `title`, `company` | Their role and where they worked. | `Power Subsystem Lead`, `Example State CubeSat Team` |
| `location` | City and state, or blank. | `Springfield, ST` |
| `start`, `end` | Dates in the experience date style. A blank `end` or `Present` means ongoing. | `Sep 2024`, `Present` |
| `engineering` | `true` for engineering work with bullets. `false` gives a one-line entry for other jobs. | `false` |
| `bullets` | Same rules as project bullets. | |
| `hide` | `true` leaves the entry out. | |

A non-engineering job still shows they can hold a job. One line is enough.

### `skills`

| Field | What to put | Example |
| --- | --- | --- |
| `software` | Tools and languages, most important first. Write `C, C++`, not `C/C++`. | `["KiCad", "LTspice", "Python"]` |
| `hardwareLab` | Lab equipment and hardware they can use without help. | `["Oscilloscope", "Electronic load"]` |
| `certifications` | Only ones they can prove. | `[]` |

Every listed skill should appear in a bullet or a project's `tools`. Leave out soft skills such as "communication". Show them in the bullets instead.

## Writing good bullets

Start with a past-tense verb, say what they built or changed, and end with a result they measured:

> Cut output ripple from 80 mV to 25 mV peak to peak, measured on an oscilloscope, by redesigning the 4-layer PCB in KiCad with a solid ground plane and a tighter switching loop

- Use a real number they measured or can defend in an interview. Don't make one up.
- Don't start with "Helped", "Assisted", "Worked on" or "Utilized".
- Don't bold words inside a bullet.

## Fitting on one page

`build.py` tries layouts from roomiest to tightest: 11 pt text with 0.5 in margins, then the font in steps down to 10 pt, then the margins down to 0.4 in. It keeps the roomiest layout that fits on one page. The spacing stays compact. If there is room left, the gaps between sections and entries grow by at most 3 pt each, so a short resume keeps some room at the bottom instead of large gaps. Line spacing never goes below 1.07. If the resume still doesn't fit at 10 pt and 0.4 in, it stops and says about how many lines to cut. Drop a coursework item first, then the weakest bullet, or add `"hide": true` to an older project.

## Checking the text

Applicant tracking systems read the PDF's text, not its look. When `pdftotext` is installed (it comes with poppler, for example `brew install poppler` or `sudo apt-get install poppler-utils`), each build extracts the text and checks that the name, contact items, section titles, entries and bullets all come out whole and in reading order, with no broken ligatures or unreadable glyphs. Problems print as a warning. Set `RESUME_TEXT_CHECK=strict` to make them an error. Words never break with a hyphen across lines, because a split word can't be found by a keyword search.

## Before applying

A good resume helps, but a referral helps more. The owner should ask someone who knows their work for a referral before applying. For more on resumes, referrals and applying for engineering jobs, see [eeprep.com](https://eeprep.com) and its [resume page](https://eeprep.com/get-hired/resume/).

## Contributing

Releases are made by pushing a tag such as `v0.1.0`. CI then builds and checks every resume and attaches the zip and a sample PDF to a GitHub release.

`build.py` is formatted and linted with [ruff](https://docs.astral.sh/ruff/), configured in `pyproject.toml`. Before opening a pull request, run:

```sh
pip install ruff
ruff format
ruff check
```

CI runs the same checks, builds every file in `examples/` with `./run`, and fails if any PDF isn't exactly one page, uses a font that isn't in `fonts/`, or doesn't pass the text check. It also builds them on a bare TeX Live with no font packages and on macOS with BasicTeX.

## License

The code is MIT. See [LICENSE](LICENSE).

The fonts in `fonts/` keep their own licenses: Libertinus Serif is under the SIL Open Font License 1.1 ([fonts/OFL.txt](fonts/OFL.txt)), and TeX Gyre Termes and TeX Gyre Heros are under the GUST Font License ([fonts/GUST-FONT-LICENSE.txt](fonts/GUST-FONT-LICENSE.txt)). See [fonts/README.md](fonts/README.md) for where each file comes from.
