# resume-generator

Turn one JSON file into a clean, one-page PDF resume. You write the content in `resume.json`, and the script does the layout and fits it onto a single page.

This project is a companion to [eeprep.com](https://eeprep.com). It was built for engineering students and follows the advice on [eeprep's resume page](https://eeprep.com/advice/resume/), but it works for any field. See a sample: [examples/alex.pdf](examples/alex.pdf).

## Download

Get the latest zip from the [releases page](https://github.com/edwardasilva/resume-generator/releases/latest), unzip it, edit `resume.json` (see the field guide below) and run `./run`. It writes `resume.pdf`.

`./run` needs Python 3 and LuaLaTeX. If either is missing, it says what it will install and asks before it uses `sudo`. It supports Fedora (dnf), Debian, Ubuntu and WSL (apt), and macOS (Homebrew). Run `./run --yes` to skip the question. The fonts come with the project in `fonts/`, so no font packages are needed, and the PDF looks the same on every system.

To work from the repository instead, clone it and run `./run`. The first run copies `examples/alex.json` to `resume.json`. Git ignores `resume.json` and `resume.pdf`, so your personal details stay out of the repository.

To build any other file, pass it as an argument: `./run examples/new-grad.json` writes `examples/new-grad.pdf` next to it.

## Examples

Each example in `examples/` is a made-up resume and the PDF built from it, from nearly empty to completely full.

| File | Who it describes | PDF |
| --- | --- | --- |
| `alex.json` | The starting point. It matches the finished example on eeprep's resume page. The student graduates in 2027 and has two projects, a one-line job and two skill lines. Every tool in the skill lines appears in a bullet. `[X]` marks a number you measure. | [alex.pdf](examples/alex.pdf) |
| `first-year.json` | A first-year student with one class project, a one-line retail job and a few skills. The page has room left at the bottom. | [first-year.pdf](examples/first-year.pdf) |
| `sophomore.json` | A second-year student with two projects, an electrical lead role in a robotics club and a one-line job. | [sophomore.pdf](examples/sophomore.pdf) |
| `new-grad.json` | A new graduate with two internships, two projects and certifications. They lead with experience and use the `times` font. | [new-grad.pdf](examples/new-grad.pdf) |
| `packed.json` | A graduating student with three engineering roles, a one-line job, three projects and long skill lists, in the `arial` font. The script tightens it to fit. | [packed.pdf](examples/packed.pdf) |

## Field guide

JSON doesn't allow comments, so this section explains each field. A blank field (`""`) or an empty list (`[]`) is left out of the PDF. Text goes in quotes, `true` and `false` go without them, and lists such as `bullets` go in brackets, even with one item. The build stops and names any field with the wrong kind of value.

The phone, email, LinkedIn, GitHub and website in the header are links. The email opens a new message and the phone number dials. Any entry can also have a link:

| Field | What to put | Example |
| --- | --- | --- |
| `url` | Optional on any education, project or experience entry. The school, project title or employer becomes a link, shown in the normal text color. To link a skill, coursework or activity item, write it as `{"name": "...", "url": "..."}`. Inside a bullet, `[text](url)` links the text. The URL may contain parentheses, as in `en.wikipedia.org/wiki/Buck_(converter)`. Links must be web addresses (`https://` is added if missing), `mailto:` or `tel:`. | `github.com/alex-doe-example/cubesat-buck-converter` |

### `settings`

| Field | What to put | Example |
| --- | --- | --- |
| `sectionOrder` | Order of the sections. Lead with your strongest one. | `["education", "projects", "experience", "skills"]` |
| `font` | `libertinus`, `times` or `arial`. Leave it out to use `libertinus`. | `"libertinus"` |
| `dateStyle` | The date style for each section: `semester` (Fall 2025) or `month` (Sep 2025 or Sept 2025). Every date in a section must use that section's style. The build stops if one doesn't. A section left out uses `semester`. | `{"education": "semester", "projects": "semester", "experience": "semester"}` |

Common orders: students with no engineering job usually go education, projects, experience, skills. Once you have an engineering internship, try experience first. Give every section the same date style, so the page never mixes Fall 2025 with Sep 2025.

Acceptable fonts for `settings.font`:

| Value | Font | Looks like |
| --- | --- | --- |
| `libertinus` | Libertinus Serif (default) | A classic book serif |
| `times` | TeX Gyre Termes | A free font close to Times New Roman. The PDF embeds TeX Gyre Termes from `fonts/`, not Times. |
| `arial` | TeX Gyre Heros | A free font close to Helvetica and Arial. The PDF embeds TeX Gyre Heros from `fonts/`, not Arial. |

### `header`

| Field | What to put | Example |
| --- | --- | --- |
| `name` | The name you want recruiters to use. It also fills the PDF's title (`Alex Doe Resume`) and author properties. | `Alex Doe` |
| `phone` | Their phone number. No label such as "Cell:". | `(555) 555-0142` |
| `email` | An address you check every day. A school address is fine. | `alex.doe@example.com` |
| `linkedin` | Their profile URL without `https://`. | `linkedin.com/in/alex-doe-example` |
| `github` | Only if it holds work you're proud of. | `github.com/alex-doe-example` |
| `website` | A personal site or portfolio, if you have one. | `example.com/~alex-doe` |
| `location` | City and state. | `Springfield, ST` |
| `relocate` | `true` adds "Willing to relocate". | `true` |

### `education`

A list. Most students have one entry. Add a second for a master's degree.

| Field | What to put | Example |
| --- | --- | --- |
| `degree` | Degree and major. | `B.S. Electrical Engineering` |
| `gpa` | `N.NN/4.00`. List it when a posting sets a minimum you meet. | `3.62/4.00` |
| `school` | Their university. | `Example State University` |
| `gradDate` | Your graduation date, in the education date style. Add "Expected" if you haven't graduated. | `Expected Spring 2027` |
| `coursework` | Upper-level courses that match the jobs you want. | `["Power Electronics", "Embedded Systems"]` |
| `activities` | Clubs and honor societies. Put real build work in `projects`. | `["IEEE student branch"]` |

### `projects`

A list, best project first. This is where you show what you can do.

| Field | What to put | Example |
| --- | --- | --- |
| `title` | A plain name for what you built. Don't use the word "project". | `FPGA Audio Equalizer` |
| `tools` | Tools, languages and parts you used. Shown in parentheses after the title, like `CubeSat Power Board (KiCad, LTspice)`. | `["Verilog", "Vivado", "MATLAB"]` |
| `start`, `end` | Dates in the projects date style. A blank `end` or `Present` means ongoing. Matching dates show once. | `Spring 2025` |
| `bullets` | One to four lines on what you did and what happened. | see below |
| `hide` | `true` leaves the entry out without deleting it. | `true` |

### `experience`

A list, most recent first.

| Field | What to put | Example |
| --- | --- | --- |
| `title`, `company` | Your role and where you worked. | `Power Subsystem Lead`, `Example State CubeSat Team` |
| `location` | City and state, or blank. | `Springfield, ST` |
| `start`, `end` | Dates in the experience date style. A blank `end` or `Present` means ongoing. | `Sep 2024`, `Present` |
| `engineering` | `true` for engineering work with bullets. `false` gives a one-line entry for other jobs, and the build notes any bullets it leaves out. | `false` |
| `bullets` | Same rules as project bullets. | |
| `hide` | `true` leaves the entry out. | |

A non-engineering job still shows you can hold a job. One line is enough.

### `skills`

| Field | What to put | Example |
| --- | --- | --- |
| `software` | Tools and languages, most important first. Write `C, C++`, not `C/C++`. | `["KiCad", "LTspice", "Python"]` |
| `hardwareLab` | Lab equipment and hardware you can use without help. | `["Oscilloscope", "Electronic load"]` |
| `certifications` | Only ones you can prove. | `[]` |

Put every listed skill in a bullet or a project's `tools`. Leave out soft skills such as "communication". Show them in the bullets instead.

## Writing good bullets

Start with a past-tense verb, say what you built or changed, and end with a result you measured:

> Cut output ripple from 80 mV to 25 mV peak to peak, measured on an oscilloscope, by redesigning the 4-layer PCB in KiCad with a solid ground plane and a tighter switching loop

- Use a real number you measured or can defend in an interview. Don't make one up.
- Don't start with "Helped", "Assisted", "Worked on" or "Utilized".
- Don't bold words inside a bullet.

## Fitting on one page

The layout follows the rules on [eeprep's resume page](https://eeprep.com/advice/resume/): text from 10 to 11 pt, margins of 0.5 in, line spacing of at least 1.07, the same gap between every pair of sections, and a page that is full but not crammed.

`build.py` finds the largest text that fits. It starts at 11 pt text with 0.5 in margins, steps the text down to 10 pt while the margins stay at 0.5 in, and keeps the first layout that fits on one page. It then fills the page. Line spacing, section gaps and entry gaps grow together, in proportion, until the page is full. They go from compact (1.07 line spacing, 7 pt section gaps) up to roomy (1.15 and 10 pt). Spacing never shrinks below compact to fit more.

If the page still has more than 3 empty lines at roomy spacing, the build notes it. eeprep's page counts empty space as wasted, so add a class project, lab work or a bullet instead. The build also notes any bullet whose second line fills less than half the line. Cut it to one line, or add a detail that fills most of the second.

If the resume doesn't fit at 10 pt, the build stops and says about how many lines to cut. Drop a coursework item first, then the weakest bullet, or add `"hide": true` to an older project.

## Checking the text

Applicant tracking systems read the PDF's text, not its look. When `pdftotext` is installed, each build extracts the text. It comes with poppler, for example `brew install poppler` or `sudo apt-get install poppler-utils`. The build checks that the name, contact items, section titles, entries and bullets all come out whole and in reading order, with no broken ligatures or unreadable glyphs. Problems print as a warning. Set `RESUME_TEXT_CHECK=strict` to make them an error. Words never break with a hyphen across lines, because a split word can't be found by a keyword search.

## Writing the content with an AI tool

If you draft `resume.json` with Claude Code, Cursor, or another coding agent, give it [the eeprep resume skill](https://eeprep.com/skills/eeprep-resume/README.md) first. It teaches the agent the layout rules this tool follows, the bullet pattern, how to tailor a version to one posting, and the one rule that matters most: it never invents a number, a tool, or a result you did not give it. It writes `[X]` where a measurement belongs and tells you to go measure it.

## Before applying

A referral helps more than a good resume. Before you apply, ask someone who knows your work for one. For more on resumes, referrals and applying for engineering jobs, see [eeprep.com](https://eeprep.com) and its [resume page](https://eeprep.com/advice/resume/).

## Contributing

All four repos (eeprep, resume-generator, edwardasilva, information) are on the 0.0.x beta line, and the current release is `v0.0.1`. A release bumps only the last number. Each release is exactly one commit on `main`. `v0.0.1` is a single commit with no parent. Each later release is one squashed commit whose parent is the previous release commit, tagged `vX.Y.Z` with an annotated tag whose message is `<repo> vX.Y.Z`. Pushing the tag makes CI build and check every resume and attach the zip and a sample PDF to the GitHub release. Every merge is a squash merge. `protect-main` is paused only while the release commit is pushed, and turned back on right after.

`build.py` is formatted and linted with [ruff](https://docs.astral.sh/ruff/), configured in `pyproject.toml`. Before opening a pull request, run:

```sh
pip install ruff==0.16.9
ruff format
ruff check
```

CI runs the same checks, builds every file in `examples/` with `./run`, and fails if any PDF isn't exactly one page, uses a font that isn't in `fonts/`, or doesn't pass the text check. It also builds them on a bare TeX Live with no font packages and on macOS with BasicTeX.

## License

The code is MIT. See [LICENSE](LICENSE).

The fonts in `fonts/` keep their own licenses: Libertinus Serif is under the SIL Open Font License 1.1 ([fonts/OFL.txt](fonts/OFL.txt)), and TeX Gyre Termes and TeX Gyre Heros are under the GUST Font License ([fonts/GUST-FONT-LICENSE.txt](fonts/GUST-FONT-LICENSE.txt)). See [fonts/README.md](fonts/README.md) for where each file comes from.
