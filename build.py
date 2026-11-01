#!/usr/bin/env python3
"""Build a one-page PDF resume from a JSON file.

Usage: build.py [file.json]   (default resume.json; writes <name>.pdf here)

Reads the JSON file, writes the LaTeX body and layout settings into build/,
runs LuaLaTeX, and tries layouts from roomiest to tightest until one fits.
Standard library only. Run it through ./run, which installs TeX if needed.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"

# Layouts to try, roomiest first: (font size in pt, margin in inches).
# The first one that fits on one page is kept.
LAYOUTS = [
    (11.0, 0.5), (10.75, 0.5), (10.5, 0.5), (10.25, 0.5), (10.0, 0.5),
    (10.0, 0.45), (10.0, 0.4),
]
LINE_SPACING = 1.07
# Compact spacing in points: before each section title and between entries.
SECTION_GAP = 7.0
ENTRY_GAP = 6.3
# When a page has room left, section and entry gaps grow by at most this
# many points each, so a short resume keeps a little room at the bottom
# instead of large gaps.
MAX_EXTRA_GAP = 3.0

SECTIONS = ("education", "projects", "experience", "skills")
SEMESTER = re.compile(r"^(Expected )?(Spring|Summer|Fall|Winter) \d{4}$")
MONTH = re.compile(
    r"^(Expected )?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|"
    r"March|April|June|July|August|September|October|November|December) \d{4}$"
)

TEX_SPECIAL = {
    "\\": r"\textbackslash{}", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}",
    "{": r"\{", "}": r"\}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$",
}
TEX_RE = re.compile("|".join(re.escape(c) for c in TEX_SPECIAL))


class ResumeError(Exception):
    pass


def esc(text):
    """Escape text for LaTeX in a single pass."""
    return TEX_RE.sub(lambda m: TEX_SPECIAL[m.group()], str(text or ""))


def esc_url(url):
    """Escape a URL for \\href."""
    return re.sub(r"([\\{}%#~])", r"\\\1", url)


def present(items):
    return [x for x in items or [] if x]


def shown(entries):
    return [e for e in entries or [] if not e.get("hide")]


def joined(items):
    return ", ".join(esc(x) for x in present(items))


def check_date(value, style, where):
    if not value or value == "Present":
        return
    pattern = SEMESTER if style == "semester" else MONTH
    if not pattern.match(value):
        example = "Fall 2025" if style == "semester" else "Sep 2025"
        raise ResumeError(f'{where}: "{value}" doesn\'t match the {style} date style (like "{example}")')


def date_range(start, end):
    start, end = start or "", end or ""
    if start and not end:
        end = "Present"
    if not start or start == end:
        return esc(start or end)
    return f"{esc(start)}--{esc(end)}"


def date_styles(data):
    styles = (data.get("settings") or {}).get("dateStyle") or {}
    if not isinstance(styles, dict):
        raise ResumeError('settings.dateStyle must be an object, like {"projects": "semester"}')
    for section, style in styles.items():
        if style not in ("semester", "month"):
            raise ResumeError(f'settings.dateStyle.{section} must be "semester" or "month"')
    return styles


def validate(data):
    styles = date_styles(data)
    for section in ("education", "projects", "experience"):
        style = styles.get(section, "semester")
        for i, entry in enumerate(shown(data.get(section))):
            for key in ("gradDate", "start", "end"):
                check_date(entry.get(key), style, f"{section}[{i}].{key}")


def header(h):
    out = [r"\begin{resumeheader}", rf"  {{\resumename {esc(h.get('name'))}}}\par\vspace{{3pt}}"]
    contact = []
    if h.get("phone"):
        digits = re.sub(r"[^\d+]", "", h["phone"])
        contact.append(rf"\href{{tel:{esc_url(digits)}}}{{{esc(h['phone'])}}}")
    if h.get("email"):
        contact.append(rf"\href{{mailto:{esc_url(h['email'])}}}{{{esc(h['email'])}}}")
    for key in ("linkedin", "github"):
        if h.get(key):
            shown_url = re.sub(r"^(https?://)?(www\.)?", "", h[key])
            contact.append(rf"\href{{https://{esc_url(shown_url)}}}{{{esc(shown_url)}}}")
    if contact:
        out.append("  " + r" \textbar{} ".join(contact) + r"\par")
    status = [esc(h.get("location")), esc(h.get("workStatus")),
              "Willing to relocate" if h.get("relocate") else "", esc(h.get("clearance"))]
    status = [s for s in status if s]
    if status:
        out.append("  " + r" \textbar{} ".join(status) + r"\par")
    out.append(r"\end{resumeheader}")
    return out


def bullets(items):
    items = present(items)
    if not items:
        return []
    return [r"\begin{itemize}"] + [rf"  \item {esc(b)}" for b in items] + [r"\end{itemize}"]


def education(data):
    out = []
    for e in shown(data.get("education")):
        title = rf"\textbf{{{esc(e.get('degree'))}}}"
        if e.get("gpa"):
            title += f", GPA {esc(e['gpa'])}"
        out.append(rf"\entry{{{title}}}{{{esc(e.get('gradDate'))}}}")
        if e.get("school"):
            out.append(esc(e["school"]) + r"\par")
        for label, key in (("Relevant coursework", "coursework"), ("Activities", "activities")):
            if present(e.get(key)):
                out.append(rf"\textbf{{{label}:}} {joined(e[key])}\par")
        out.append(r"\entrygap")
    return out


def projects(data):
    out = []
    for p in shown(data.get("projects")):
        out.append(rf"\entry{{\textbf{{{esc(p.get('title'))}}}}}{{{date_range(p.get('start'), p.get('end'))}}}")
        if present(p.get("tools")):
            out.append(rf"\tools{{{joined(p['tools'])}}}")
        out += bullets(p.get("bullets"))
        out.append(r"\entrygap")
    return out


def experience(data):
    out = []
    for x in shown(data.get("experience")):
        name = esc(x.get("title"))
        if x.get("company"):
            name += ", " + esc(x["company"])
        place = f", {esc(x['location'])}" if x.get("location") else ""
        dates = date_range(x.get("start"), x.get("end"))
        if x.get("engineering"):
            out.append(rf"\entry{{\textbf{{{name}}}{place}}}{{{dates}}}")
            out += bullets(x.get("bullets"))
        else:
            out.append(rf"\entry{{{name}{place}}}{{{dates}}}")
        out.append(r"\entrygap")
    return out


def skills(data):
    s = data.get("skills") or {}
    groups = (("Software", "software"), ("Hardware/Lab", "hardwareLab"), ("Certifications", "certifications"))
    return [rf"\textbf{{{label}:}} {joined(s.get(key))}\par" for label, key in groups if present(s.get(key))]


RENDER = {"education": education, "projects": projects, "experience": experience, "skills": skills}
TITLES = {"education": "Education", "projects": "Projects", "experience": "Experience", "skills": "Skills"}


def body(data):
    out = header(data.get("header") or {})
    order = (data.get("settings") or {}).get("sectionOrder") or list(SECTIONS)
    for name in order:
        if name not in RENDER:
            raise ResumeError(f'settings.sectionOrder: unknown section "{name}"')
        lines = RENDER[name](data)
        if lines:
            if lines[-1] == r"\entrygap":
                lines.pop()
            out += [rf"\resumesection{{{TITLES[name]}}}"] + lines
    return "\n".join(out) + "\n"


def settings(font, margin, extra=0.0):
    line = font * 1.2 * LINE_SPACING
    return "\n".join([
        rf"\newcommand{{\resumemargin}}{{{margin}in}}",
        rf"\newcommand{{\resumefont}}{{\fontsize{{{font}pt}}{{{line:.2f}pt}}\selectfont}}",
        rf"\newcommand{{\resumename}}{{\fontsize{{{font * 1.9:.1f}pt}}{{{font * 2.2:.1f}pt}}\selectfont}}",
        rf"\newcommand{{\sectiongap}}{{{SECTION_GAP + extra:.2f}pt}}",
        rf"\newcommand{{\entryspace}}{{{ENTRY_GAP + extra * 0.75:.2f}pt}}",
        "",
    ])


def compile_once(font, margin, extra=0.0):
    """Build at one layout. Return (pages, log text)."""
    (BUILD / "settings.tex").write_text(settings(font, margin, extra), encoding="utf-8")
    env = dict(os.environ, SOURCE_DATE_EPOCH="0", FORCE_SOURCE_DATE="1")
    result = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory=build", "resume.tex"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    log = (BUILD / "resume.log").read_text(encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = "\n".join(log.splitlines()[-20:])
        raise ResumeError(f"LaTeX failed. Last lines of build/resume.log:\n{tail}")
    pages = re.search(r"Output written on .*?\((\d+) pages?", log, re.S)
    return int(pages.group(1)) if pages else 0, log


def measure(log, key):
    m = re.search(rf"RESUME-{key} page=(\d+) used=([\d.]+)pt goal=([\d.]+)pt line=([\d.]+)pt", log)
    return (int(m.group(1)), *map(float, m.groups()[1:])) if m else None


def spread(tex, end):
    """Extra points for each gap, using about half the free space, capped."""
    if not end:
        return 0.0
    _, used, goal, _ = end
    gaps = tex.count(r"\resumesection") + 0.75 * tex.count(r"\entrygap")
    if gaps == 0:
        return 0.0
    return min(MAX_EXTRA_GAP, 0.5 * (goal - used) / gaps)


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "resume.json"
    output = ROOT / f"{source.stem}.pdf"
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except OSError as e:
        sys.exit(f"Can't read {source.name}: {e.strerror}")
    except json.JSONDecodeError as e:
        sys.exit(f"{source.name} isn't valid JSON: {e}")
    try:
        validate(data)
        BUILD.mkdir(exist_ok=True)
        tex = body(data)
        (BUILD / "body.tex").write_text(tex, encoding="utf-8")
        for font, margin in LAYOUTS:
            pages, log = compile_once(font, margin)
            if pages == 1:
                extra = spread(tex, measure(log, "END"))
                if extra and compile_once(font, margin, extra)[0] != 1:
                    extra = 0.0
                    compile_once(font, margin)
                shutil.copy(BUILD / "resume.pdf", output)
                print(f"Wrote {output.name} (1 page, {font:g} pt text, {margin:g} in margins, "
                      f"gaps +{extra:.1f} pt).")
                return
    except ResumeError as e:
        sys.exit(str(e))
    end = measure(log, "END")
    lines = 1
    if end:
        page, used, goal, line = end
        lines = max(1, round(((page - 2) * goal + used) / line + 0.5))
    sys.exit(
        f"{source.name} doesn't fit on one page, even at {LAYOUTS[-1][0]:g} pt with {LAYOUTS[-1][1]:g} in margins.\n"
        f"Cut about {lines} line(s). Try dropping a coursework item first, then a bullet."
    )


if __name__ == "__main__":
    main()
