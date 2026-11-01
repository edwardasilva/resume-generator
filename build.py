#!/usr/bin/env python3
"""Build a one-page PDF resume from a JSON file.

Usage: build.py [file.json]

The default input is resume.json. The PDF is written next to the input file
with the same name, so examples/new-grad.json becomes examples/new-grad.pdf.

The script reads the JSON file, writes the LaTeX body and layout settings into
build/, runs LuaLaTeX, and tries layouts from roomiest to tightest until one
fits on a single page. It uses only the Python standard library. Run it
through ./run, which installs Python and TeX first if they are missing.
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
    (11.0, 0.5),
    (10.75, 0.5),
    (10.5, 0.5),
    (10.25, 0.5),
    (10.0, 0.5),
    (10.0, 0.45),
    (10.0, 0.4),
]
# Line spacing as a multiple of the usual 1.2 times the font size.
LINE_SPACING = 1.07
# Compact spacing in points: before each section title and between entries.
SECTION_GAP = 7.0
ENTRY_GAP = 6.3
# When a page has room left, section and entry gaps grow by at most this
# many points each, so a short resume keeps a little room at the bottom
# instead of large gaps.
MAX_EXTRA_GAP = 3.0

# Fonts allowed in settings.font: font files in fonts/, loaded by path so the
# build doesn't depend on the fonts installed on the system. The first one is
# the default.
FONTS = {
    "libertinus": ("LibertinusSerif", "*-Regular", "*-Bold"),
    "times": ("texgyretermes", "*-regular", "*-bold"),
    "arial": ("texgyreheros", "*-regular", "*-bold"),
}

# Sections in their default order, and the date patterns for each style.
SECTIONS = ("education", "projects", "experience", "skills")
SEMESTER = re.compile(r"^(Expected )?(Spring|Summer|Fall|Winter) \d{4}$")
MONTH = re.compile(
    r"^(Expected )?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|"
    r"March|April|June|July|August|September|October|November|December) \d{4}$"
)

# Characters that LaTeX treats specially, and what to print for each one.
TEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
    "{": r"\{",
    "}": r"\}",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "$": r"\$",
}
TEX_RE = re.compile("|".join(re.escape(c) for c in TEX_SPECIAL))


class ResumeError(Exception):
    """A problem with the resume file or the LaTeX run, shown to the user."""


def esc(text):
    """Escape text for LaTeX in a single pass."""
    return TEX_RE.sub(lambda m: TEX_SPECIAL[m.group()], str(text or ""))


def esc_url(url):
    """Escape a URL for a LaTeX link, adding https:// when it has no scheme.

    Only web, mailto: and tel: links are allowed. Spaces and characters that
    can't appear in a URL are percent-encoded first. Then %, #, &, _ and ~ get
    a backslash, which the link command turns back into the plain character
    even inside another command's argument.
    """
    url = str(url).strip()
    scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", url)
    if not scheme:
        url = "https://" + url
    elif scheme.group(1).lower() not in ("http", "https", "mailto", "tel"):
        raise ResumeError(
            f'Links must use https://, http://, mailto: or tel:, not "{url}"'
        )
    url = re.sub(r'[\s"<>\\^`{|}$]', lambda m: f"%{ord(m.group()):02X}", url)
    return re.sub(r"([%#&_~])", r"\\\1", url)


def short_url(url):
    """Return a URL as people read it: no scheme, no www. and no trailing slash."""
    return re.sub(r"^(https?://)?(www\.)?", "", str(url).strip()).rstrip("/")


def link(url, text):
    """Wrap LaTeX text in a hyperlink to url, or return the text if url is blank."""
    return rf"\href{{{esc_url(url)}}}{{{text}}}" if url else text


# A Markdown-style inline link in bullet text: [text](url).
INLINE_LINK = re.compile(r"\[([^\[\]]+)\]\(([^()\s]+)\)")


def rich(text):
    """Escape bullet text, turning each [text](url) into a hyperlink."""
    text, out, last = str(text or ""), [], 0
    for m in INLINE_LINK.finditer(text):
        out += [esc(text[last : m.start()]), link(m.group(2), esc(m.group(1)))]
        last = m.end()
    return "".join(out) + esc(text[last:])


def present(items):
    """Return the non-empty items of a list, or an empty list for None."""
    return [x for x in items or [] if x]


def shown(entries):
    """Return the entries that are not marked with "hide": true."""
    return [e for e in entries or [] if not e.get("hide")]


def item(x):
    """Escape a list item: a string, or {"name": ..., "url": ...} for a link."""
    if isinstance(x, dict):
        return link(x.get("url"), esc(x.get("name")))
    return esc(x)


def joined(items):
    """Escape the non-empty items and join them with commas."""
    return ", ".join(item(x) for x in present(items))


def check_date(value, style, where):
    """Raise ResumeError if a date doesn't match its section's date style."""
    if not value or value == "Present":
        return
    pattern = SEMESTER if style == "semester" else MONTH
    if not pattern.match(value):
        example = "Fall 2025" if style == "semester" else "Sep 2025"
        raise ResumeError(
            f'{where}: "{value}" doesn\'t match the {style} date style '
            f'(like "{example}")'
        )


def date_range(start, end):
    """Format a date range, using Present for a blank end and one date if equal."""
    start, end = start or "", end or ""
    if start and not end:
        end = "Present"
    if not start or start == end:
        return esc(start or end)
    return f"{esc(start)}--{esc(end)}"


def date_styles(data):
    """Return the date style for each section, checking that each one is valid."""
    styles = (data.get("settings") or {}).get("dateStyle") or {}
    if not isinstance(styles, dict):
        raise ResumeError(
            'settings.dateStyle must be an object, like {"projects": "semester"}'
        )
    for section, style in styles.items():
        if style not in ("semester", "month"):
            raise ResumeError(
                f'settings.dateStyle.{section} must be "semester" or "month"'
            )
    return styles


def font_name(data):
    """Return the chosen font, checking that it is one of the allowed fonts."""
    font = (data.get("settings") or {}).get("font") or next(iter(FONTS))
    if font not in FONTS:
        allowed = ", ".join(f'"{name}"' for name in FONTS)
        raise ResumeError(f'settings.font must be one of {allowed}, not "{font}"')
    return font


def validate(data):
    """Check the font and every visible date against its section's style."""
    font_name(data)
    styles = date_styles(data)
    for section in ("education", "projects", "experience"):
        style = styles.get(section, "semester")
        for i, entry in enumerate(shown(data.get(section))):
            for key in ("gradDate", "start", "end"):
                check_date(entry.get(key), style, f"{section}[{i}].{key}")


def header(h):
    """Return LaTeX lines for the centered name, contact line and status line."""
    out = [
        r"\begin{resumeheader}",
        rf"  {{\resumename {esc(h.get('name'))}}}\par\vspace{{3pt}}",
    ]
    contact = []
    if h.get("phone"):
        digits = re.sub(r"[^\d+]", "", h["phone"])
        contact.append(link(f"tel:{digits}", esc(h["phone"])))
    if h.get("email"):
        contact.append(link(f"mailto:{h['email']}", esc(h["email"])))
    for key in ("linkedin", "github", "website"):
        if h.get(key):
            contact.append(link(h[key], esc(short_url(h[key]))))
    if contact:
        out.append("  " + r"\headersep{}".join(contact) + r"\par")
    status = [
        esc(h.get("location")),
        esc(h.get("workStatus")),
        "Willing to relocate" if h.get("relocate") else "",
        esc(h.get("clearance")),
    ]
    status = [s for s in status if s]
    if status:
        out.append("  " + r"\headersep{}".join(status) + r"\par")
    out.append(r"\end{resumeheader}")
    return out


def bullets(items):
    """Return LaTeX lines for a bullet list, or nothing if there are no bullets."""
    items = present(items)
    if not items:
        return []
    return (
        [r"\begin{itemize}"]
        + [rf"  \item {rich(b)}" for b in items]
        + [r"\end{itemize}"]
    )


def education(data):
    """Return LaTeX lines for the education entries."""
    out = []
    for e in shown(data.get("education")):
        title = rf"\textbf{{{esc(e.get('degree'))}}}"
        if e.get("gpa"):
            title += f", GPA {esc(e['gpa'])}"
        out.append(rf"\entry{{{title}}}{{{esc(e.get('gradDate'))}}}")
        if e.get("school"):
            out.append(link(e.get("url"), esc(e["school"])) + r"\par")
        for label, key in (
            ("Relevant coursework", "coursework"),
            ("Activities", "activities"),
        ):
            if present(e.get(key)):
                out.append(rf"\textbf{{{label}:}} {joined(e[key])}\par")
        out.append(r"\entrygap")
    return out


def projects(data):
    """Return LaTeX lines for the projects: title and dates, tools, then bullets."""
    out = []
    for p in shown(data.get("projects")):
        title = rf"\textbf{{{link(p.get('url'), esc(p.get('title')))}}}"
        dates = date_range(p.get("start"), p.get("end"))
        out.append(rf"\entry{{{title}}}{{{dates}}}")
        if present(p.get("tools")):
            out.append(rf"\tools{{{joined(p['tools'])}}}")
        out += bullets(p.get("bullets"))
        out.append(r"\entrygap")
    return out


def experience(data):
    """Return LaTeX lines for experience, with bullets only for engineering jobs."""
    out = []
    for x in shown(data.get("experience")):
        if x.get("company"):
            name = esc(x.get("title")) + ", " + link(x.get("url"), esc(x["company"]))
        else:
            name = link(x.get("url"), esc(x.get("title")))
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
    """Return one LaTeX line for each non-empty skill group."""
    s = data.get("skills") or {}
    groups = (
        ("Software", "software"),
        ("Hardware/Lab", "hardwareLab"),
        ("Certifications", "certifications"),
    )
    return [
        rf"\textbf{{{label}:}} {joined(s.get(key))}\par"
        for label, key in groups
        if present(s.get(key))
    ]


RENDER = {
    "education": education,
    "projects": projects,
    "experience": experience,
    "skills": skills,
}
TITLES = {
    "education": "Education",
    "projects": "Projects",
    "experience": "Experience",
    "skills": "Skills",
}


def body(data):
    """Return the LaTeX body: the header, then each section in the chosen order."""
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


def settings(typeface, font, margin, extra=0.0):
    """Return LaTeX definitions for the font, size, margins and gaps of a layout."""
    line = font * 1.2 * LINE_SPACING
    name, name_line = font * 1.9, font * 2.2
    base, upright, bold = FONTS[typeface]
    return "\n".join(
        [
            rf"\newcommand{{\resumemainfont}}{{\setmainfont{{{base}}}"
            rf"[Path=./fonts/, Extension=.otf, UprightFont={upright}, "
            rf"BoldFont={bold}]}}",
            rf"\newcommand{{\resumemargin}}{{{margin}in}}",
            rf"\newcommand{{\resumefont}}"
            rf"{{\fontsize{{{font}pt}}{{{line:.2f}pt}}\selectfont}}",
            rf"\newcommand{{\resumename}}"
            rf"{{\fontsize{{{name:.1f}pt}}{{{name_line:.1f}pt}}\selectfont}}",
            rf"\newcommand{{\sectiongap}}{{{SECTION_GAP + extra:.2f}pt}}",
            rf"\newcommand{{\entryspace}}{{{ENTRY_GAP + extra * 0.75:.2f}pt}}",
            "",
        ]
    )


def compile_once(typeface, font, margin, extra=0.0):
    """Build the PDF at one layout and return the page count and the log text."""
    (BUILD / "settings.tex").write_text(
        settings(typeface, font, margin, extra), encoding="utf-8"
    )
    env = dict(os.environ, SOURCE_DATE_EPOCH="0", FORCE_SOURCE_DATE="1")
    result = subprocess.run(
        [
            "lualatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory=build",
            "resume.tex",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log = (BUILD / "resume.log").read_text(encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise ResumeError(latex_error(log))
    pages = re.search(r"Output written on .*?\((\d+) pages?", log, re.S)
    return int(pages.group(1)) if pages else 0, log


def latex_error(log):
    """Return a short message about a failed LaTeX run, from its first error."""
    lines = log.splitlines()
    first = next((i for i, x in enumerate(lines) if x.startswith("!")), None)
    if first is None:
        error = "LaTeX stopped without an error message."
    else:
        error = " ".join(lines[first : first + 2])
        error = " ".join(re.sub(r"^! |\(\w+\)", " ", error).split())
    hint = "Update TeX Live with: tlmgr update --all, then run ./run again."
    if "fontspec" in log and "cannot be found" in log:
        hint = "A font file in fonts/ is missing. Download the project again."
    elif "File `" in error and "not found" in error:
        package = re.search(r"File `([^']+)\.sty'", error)
        name = package.group(1) if package else "the missing package"
        hint = f"Install {name}, for example with: tlmgr install {name}"
    return f"LaTeX failed: {error}\n{hint}\nThe full log is in {BUILD / 'resume.log'}"


def measure(log, key):
    """Read a measurement written by resume.tex from the log.

    Returns (page, used, goal, line) in points, or None if it is missing.
    """
    pattern = (
        rf"RESUME-{key} page=(\d+) used=([\d.]+)pt "
        rf"goal=([\d.]+)pt line=([\d.]+)pt"
    )
    m = re.search(pattern, log)
    return (int(m.group(1)), *map(float, m.groups()[1:])) if m else None


def spread(tex, end):
    """Return the extra points to add to each gap when the page has room left.

    It uses at most half of the free space and never more than MAX_EXTRA_GAP.
    """
    if not end:
        return 0.0
    _, used, goal, _ = end
    gaps = tex.count(r"\resumesection") + 0.75 * tex.count(r"\entrygap")
    if gaps == 0:
        return 0.0
    return min(MAX_EXTRA_GAP, 0.5 * (goal - used) / gaps)


def main():
    """Build the PDF, or exit with a message saying what to fix."""
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "resume.json"
    output = source.with_suffix(".pdf")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except OSError as e:
        sys.exit(f"Can't read {source.name}: {e.strerror}")
    except json.JSONDecodeError as e:
        sys.exit(f"{source.name} isn't valid JSON: {e}")
    try:
        validate(data)
        typeface = font_name(data)
        BUILD.mkdir(exist_ok=True)
        tex = body(data)
        (BUILD / "body.tex").write_text(tex, encoding="utf-8")
        for font, margin in LAYOUTS:
            pages, log = compile_once(typeface, font, margin)
            if pages == 1:
                extra = spread(tex, measure(log, "END"))
                if extra and compile_once(typeface, font, margin, extra)[0] != 1:
                    extra = 0.0
                    compile_once(typeface, font, margin)
                shutil.copy(BUILD / "resume.pdf", output)
                print(
                    f"Wrote {output.name} (1 page, {typeface}, {font:g} pt text, "
                    f"{margin:g} in margins, gaps +{extra:.1f} pt)."
                )
                return
    except ResumeError as e:
        sys.exit(str(e))
    end = measure(log, "END")
    lines = 1
    if end:
        page, used, goal, line = end
        lines = max(1, round(((page - 2) * goal + used) / line + 0.5))
    font, margin = LAYOUTS[-1]
    sys.exit(
        f"{source.name} doesn't fit on one page, even at {font:g} pt with "
        f"{margin:g} in margins.\n"
        f"Cut about {lines} line(s). "
        "Try dropping a coursework item first, then a bullet."
    )


if __name__ == "__main__":
    main()
