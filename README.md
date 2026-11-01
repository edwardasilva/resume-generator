# resume-generator

Turn one JSON file into a clean, one-page PDF resume. The owner writes the content in `resume.json`; the script handles the layout and fits it onto a single page.

It was built for engineering students, and the layout follows the advice on [eeprep's resume page](https://eeprep.com/get-hired/resume/). It works for any field.

See a sample resume: [docs/sample.pdf](docs/sample.pdf)

## Quick start

1. **Get the code.**

   ```sh
   git clone https://github.com/edwardasilva/resume-generator.git
   cd resume-generator
   ```

2. **Edit `resume.json`.** The sample belongs to Jane Doe, a made-up electrical engineering student. Replace Jane's details with the resume owner's. The field guide below says what goes where.

3. **Build it.**

   ```sh
   ./run
   ```

   This writes `resume.pdf`. It needs Python 3 and LuaLaTeX. If either is missing, the script says what it will install and asks before it uses `sudo`. It supports Fedora (dnf), Debian, Ubuntu and WSL (apt), and macOS (Homebrew). Run `./run --yes` to skip the question. `./run` checks the tools and then calls `build.py`, which does the layout and fitting.

## Field guide

JSON doesn't allow comments, so this section explains each field. A blank field (`""`) or an empty list (`[]`) is left out of the PDF.

### `settings`

| Field | What to put | Example |
| --- | --- | --- |
| `sectionOrder` | Order of the sections. Lead with the owner's strongest one. | `["education", "projects", "experience", "skills"]` |
| `dateStyle` | The date style for each section: `semester` (Fall 2025) or `month` (Sep 2025). Every date in a section must use that section's style; the build stops if one doesn't. A section left out uses `semester`. | `{"education": "semester", "projects": "semester", "experience": "month"}` |

Common orders: students with no engineering job usually go education, projects, experience, skills. Once they have an engineering internship, try experience first. School terms suit education and projects; jobs usually use months.

### `header`

| Field | What to put | Example |
| --- | --- | --- |
| `name` | The name they want recruiters to use. | `Jane Doe` |
| `phone` | Their phone number. No label such as "Cell:". | `(555) 555-0142` |
| `email` | An address they check every day. A school address is fine. | `jane.doe@example.com` |
| `linkedin` | Their profile URL without `https://`. | `linkedin.com/in/jane-doe-example` |
| `github` | Only if it holds work they're proud of. | `github.com/jane-doe-example` |
| `location` | City and state. | `Springfield, ST` |
| `workStatus` | Their work authorization, if it helps them. Always be truthful. | `US Citizen` |
| `relocate` | `true` adds "Willing to relocate". | `true` |
| `clearance` | An active security clearance, if they hold one. | `""` |

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
| `tools` | Tools, languages and parts they actually used. Shown on their own line under the title. | `["Verilog", "Vivado", "MATLAB"]` |
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

`build.py` tries layouts from roomiest to tightest: 11 pt text with 0.5 in margins, then the font in steps down to 10 pt, then the margins down to 0.4 in. It keeps the roomiest layout that fits on one page, then spreads any leftover space evenly between sections, entries and lines, so the page looks full instead of ending in a big gap. Line spacing never goes below 1.07. If the resume still doesn't fit at 10 pt and 0.4 in, it stops and says about how many lines to cut. Drop a coursework item first, then the weakest bullet, or add `"hide": true` to an older project.

## Before applying

A good resume helps, but a referral helps more. The owner should ask someone who knows their work for a referral before applying. [eeprep's resume page](https://eeprep.com/get-hired/resume/) covers each section in more detail.

## License

MIT. See [LICENSE](LICENSE).
