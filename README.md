# resume-generator

Turn one JSON file into a clean, one-page PDF resume. You write the content in `resume.json`; the script handles the layout and fits it onto a single page.

It was built for engineering students, and the layout follows the advice on [eeprep's resume page](https://eeprep.com/get-hired/resume/). It works for any field.

## Quick start

1. **Get the code.**

   ```sh
   git clone https://github.com/edwardasilva/resume-generator.git
   cd resume-generator
   ```

2. **Edit `resume.json`.** The sample belongs to Jane Doe, a made-up electrical engineering student. Replace her details with yours. The field guide below says what goes where.

3. **Build it.**

   ```sh
   ./run
   ```

   This writes `resume.pdf`. If LuaLaTeX isn't installed, the script tells you what it will install and asks before it uses `sudo`. It supports Fedora (dnf), Debian, Ubuntu and WSL (apt), and macOS (Homebrew BasicTeX). Run `./run --yes` to skip the question.

## Field guide

JSON doesn't allow comments, so this section explains each field. A blank field (`""`) or an empty list (`[]`) is left out of the PDF.

### `settings`

| Field | What to put | Example |
| --- | --- | --- |
| `sectionOrder` | Order of the sections. Lead with your strongest one. | `["education", "projects", "experience", "skills"]` |
| `dateStyle` | `semester` or `month`. Use one style for every date. | `semester` |

Common orders: students with no engineering job usually go education, projects, experience, skills. Once you have an engineering internship, try experience first.

### `header`

| Field | What to put | Example |
| --- | --- | --- |
| `name` | The name you want recruiters to use. | `Jane Doe` |
| `phone` | Your phone number. No label such as "Cell:". | `(555) 555-0142` |
| `email` | An address you check every day. A school address is fine. | `jane.doe@example.com` |
| `linkedin` | Your profile URL without `https://`. | `linkedin.com/in/jane-doe-example` |
| `github` | Only if it holds work you're proud of. | `github.com/jane-doe-example` |
| `location` | City and state. | `Springfield, ST` |
| `workStatus` | Your work authorization, if it helps you. Always be truthful. | `US Citizen` |
| `relocate` | `true` adds "Willing to relocate". | `true` |
| `clearance` | An active security clearance, if you hold one. | `""` |

### `education`

A list. Most students have one entry. Add a second for a master's degree.

| Field | What to put | Example |
| --- | --- | --- |
| `degree` | Degree and major. | `B.S. Electrical Engineering` |
| `gpa` | `N.NN/4.00`. List it when a posting sets a minimum you meet. | `3.62/4.00` |
| `school` | Your university. | `Example State University` |
| `gradDate` | Your graduation date. Add "Expected" if you haven't graduated. | `Expected Spring 2027` |
| `coursework` | Upper-level courses that match the jobs you want. | `["Power Electronics", "Embedded Systems"]` |
| `activities` | Clubs and honor societies. Put real build work in `projects`. | `["IEEE student branch"]` |

### `projects`

A list, best project first. This is where most students show what they can do.

| Field | What to put | Example |
| --- | --- | --- |
| `title` | A plain name for what you built. Don't use the word "project". | `FPGA Audio Equalizer` |
| `tools` | Tools, languages and parts you actually used. | `["Verilog", "Vivado", "MATLAB"]` |
| `start`, `end` | Dates in your chosen style. `end` can be `Present`. | `Spring 2025` |
| `bullets` | One to four lines on what you did and what happened. | see below |
| `hide` | `true` leaves the entry out without deleting it. | `true` |

### `experience`

A list, most recent first.

| Field | What to put | Example |
| --- | --- | --- |
| `title`, `company` | Your role and where you worked. | `Power Subsystem Lead`, `Example State CubeSat Team` |
| `location` | City and state, or blank. | `Springfield, ST` |
| `start`, `end` | Dates in your chosen style. | `Fall 2024`, `Present` |
| `engineering` | `true` for engineering work with bullets. `false` gives a one-line entry for other jobs. | `false` |
| `bullets` | Same rules as project bullets. | |
| `hide` | `true` leaves the entry out. | |

A non-engineering job still shows you can hold a job. One line is enough.

### `skills`

| Field | What to put | Example |
| --- | --- | --- |
| `software` | Tools and languages, most important first. Write `C, C++`, not `C/C++`. | `["KiCad", "LTspice", "Python"]` |
| `hardwareLab` | Lab equipment and hardware you can use without help. | `["Oscilloscope", "Electronic load"]` |
| `certifications` | Only ones you can prove. | `[]` |

Every skill you list should appear in a bullet or a project's `tools`. Leave out soft skills such as "communication". Show them in your bullets instead.

## Writing good bullets

Start with a past-tense verb, say what you built or changed, and end with a result you measured:

> Cut output ripple from 80 mV to 25 mV peak to peak, measured on an oscilloscope, by redesigning the 4-layer PCB in KiCad with a solid ground plane and a tighter switching loop

- Use a real number you measured or can defend in an interview. Don't make one up.
- Don't start with "Helped", "Assisted", "Worked on" or "Utilized".
- Don't bold words inside a bullet.

## Fitting on one page

The script starts with the roomiest layout (11 pt text, 0.75 in margins) and tightens one step at a time: first the spacing, then the margins down to 0.4 in, then the font down to 10 pt. It keeps the roomiest layout that still fits on one page. Line spacing never goes below 1.07. If the resume still doesn't fit, it stops and tells you about how many lines to cut. Drop a coursework item first, then your weakest bullet, or add `"hide": true` to an older project.

## Before you apply

A good resume helps, but a referral helps more. Ask someone who knows your work to refer you before you apply. [eeprep's resume page](https://eeprep.com/get-hired/resume/) covers each section in more detail.

## License

MIT. See [LICENSE](LICENSE).
