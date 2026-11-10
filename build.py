#!/usr/bin/env python3
"""Build a one-page PDF resume from a JSON file.

Usage: build.py [file.json]

The default input is resume.json. The PDF is written next to the input file
and named after the header name: resume.json becomes Alex-Doe-Resume.pdf.
Any other input adds its file name, so examples/new-grad.json becomes
examples/Alex-Doe-Resume-new-grad.pdf, and resume-firmware.json becomes
Alex-Doe-Resume-firmware.pdf. A file named alex.json keeps Alex-Doe-Resume.pdf.

The script reads the JSON file, writes the LaTeX body and layout settings into
build/, runs LuaLaTeX, and tries layouts from roomiest to tightest until one
fits on a single page. It uses only the Python standard library. Run it
through ./run, which installs Python and TeX first if they are missing.
"""

import html
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
]
# The rules below follow eeprep's resume page (eeprep.com/advice/resume/):
# text 10 to 11 pt, margins of 0.5 in, line spacing of at least 1.07,
# one gap size between every pair of sections, and a page that is filled but
# not crammed. White space never shrinks below the compact sizes to fit more.
#
# Line spacing as a multiple of the usual 1.2 times the font size, and
# spacing in points before each section title and between entries. A full
# page uses the compact values. A page with room left grows all of them
# together, in proportion, up to the roomy values, until the page is full.
LINE_SPACING = (1.07, 1.15)
SECTION_GAP = (7.0, 10.0)
ENTRY_GAP = (6.3, 8.55)
# Room left at the bottom of a filled page, in lines, so rounding can't push
# the last line onto a second page.
FILL_RESERVE = 0.5
# A page with more than this many empty lines at the roomy spacing gets a
# note: the resume needs more content, not more space.
EMPTY_LINES_NOTE = 3
# A bullet whose last line fills less than this share of the line gets a
# note. eeprep's page says a bullet fills one line or most of two.
SHORT_LAST_LINE = 0.5

# Input file names (without .json) that add nothing to the PDF name.
PLAIN_STEMS = ("resume", "alex")

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
    r"^(Expected )?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
    r"January|February|March|April|June|July|August|September|October|November|"
    r"December) \d{4}$"
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
# Control characters, which LaTeX rejects as invalid input. Tabs and line
# breaks are whitespace and become a single space instead.
CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")


class ResumeError(Exception):
    """A problem with the resume file or the LaTeX run, shown to the user."""


def esc(text):
    """Escape text for LaTeX in a single pass.

    Runs of spaces, tabs and line breaks become one space, so a blank line
    pasted into a bullet can't start a new paragraph. Control characters are
    dropped. A no-break space is kept.
    """
    text = re.sub(r"[ \t\n\r\f\v]+", " ", CONTROL.sub("", str(text or "")))
    return TEX_RE.sub(lambda m: TEX_SPECIAL[m.group()], text)


def esc_url(url):
    """Escape a URL for a LaTeX link, adding https:// when it has no scheme.

    Only web, mailto: and tel: links are allowed. Spaces and characters that
    can't appear in a URL are percent-encoded first. Then %, #, &, _ and ~ get
    a backslash, which the link command turns back into the plain character
    even inside another command's argument.
    """
    url = str(url).strip()
    scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", url)
    if scheme and scheme.group(1).lower() in ("http", "https", "mailto", "tel"):
        pass
    elif not scheme or re.match(r"\d+(?:[/?#]|$)", url[scheme.end() :]):
        # No scheme, or a host with a port such as example.com:8443/me.
        url = "https://" + url
    else:
        raise ResumeError(
            f'Links must use https://, http://, mailto: or tel:, not "{url}"'
        )
    url = re.sub(
        r'[\s\x00-\x1f\x7f"<>\\^`{|}$]', lambda m: f"%{ord(m.group()):02X}", url
    )
    return re.sub(r"([%#&_~])", r"\\\1", url)


def short_url(url):
    """Return a URL as people read it: no scheme, no www. and no trailing slash."""
    url = re.sub(r"^(https?://)?(www\.)?", "", str(url).strip(), flags=re.I)
    return url.rstrip("/")


def link(url, text):
    """Wrap LaTeX text in a hyperlink to url, or return the text if url is blank."""
    return rf"\href{{{esc_url(url)}}}{{{text}}}" if url else text


# A Markdown-style inline link in bullet text: [text](url). The URL may hold
# balanced parentheses, as in en.wikipedia.org/wiki/Buck_(converter).
INLINE_LINK = re.compile(r"\[([^\[\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")


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
    return [e for e in entries or [] if e and not e.get("hide")]


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
    return f"{esc(start)} -- {esc(end)}"


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


# The type of each field: "text" (a string), "flag" (true or false), "lines"
# (a list of strings) or "items" (a list of strings or {"name", "url"} links).
# null counts as blank for any field.
ENTRY_FIELDS = {
    "education": {
        **dict.fromkeys(("degree", "gpa", "school", "gradDate", "url"), "text"),
        **dict.fromkeys(("start", "end"), "text"),
        "coursework": "items",
        "activities": "items",
        "hide": "flag",
    },
    "projects": {
        **dict.fromkeys(("title", "url", "start", "end"), "text"),
        "tools": "items",
        "bullets": "lines",
        "hide": "flag",
    },
    "experience": {
        **dict.fromkeys(("title", "company", "location", "url"), "text"),
        **dict.fromkeys(("start", "end"), "text"),
        "engineering": "flag",
        "bullets": "lines",
        "hide": "flag",
    },
}
HEADER_FIELDS = {
    **dict.fromkeys(
        ("name", "phone", "email", "linkedin", "github", "website", "location"),
        "text",
    ),
    "relocate": "flag",
}
SKILL_FIELDS = dict.fromkeys(("software", "hardwareLab", "certifications"), "items")


def check_field(value, kind, where):
    """Raise ResumeError if a field's value doesn't have the type it needs."""
    if value is None:
        return
    if kind == "text" and not isinstance(value, str):
        like = value if isinstance(value, (int, float)) else "..."
        raise ResumeError(f'{where} must be text in quotes, like "{like}"')
    if kind == "flag" and not isinstance(value, bool):
        raise ResumeError(f"{where} must be true or false, without quotes")
    if kind in ("lines", "items"):
        if not isinstance(value, list):
            raise ResumeError(f'{where} must be a list in brackets, like ["..."]')
        for i, x in enumerate(value):
            if isinstance(x, str) or x is None:
                continue
            if kind == "items" and isinstance(x, dict):
                for key in ("name", "url"):
                    check_field(x.get(key), "text", f"{where}[{i}].{key}")
                continue
            what = (
                'text or {"name": "...", "url": "..."}' if kind == "items" else "text"
            )
            raise ResumeError(f"{where}[{i}] must be {what}")


def check_object(value, where):
    """Raise ResumeError unless value is a JSON object or null."""
    if value is not None and not isinstance(value, dict):
        raise ResumeError(f"{where} must be an object in braces, like {{...}}")


def check_types(data):
    """Check that every field has the type the layout expects."""
    if not isinstance(data, dict):
        raise ResumeError("The resume file must hold one object in braces, {...}")
    settings = data.get("settings")
    check_object(settings, "settings")
    settings = settings or {}
    check_field(settings.get("font"), "text", "settings.font")
    order = settings.get("sectionOrder")
    check_field(order, "lines", "settings.sectionOrder")
    for name in order or []:
        if name not in SECTIONS:
            raise ResumeError(f'settings.sectionOrder: unknown section "{name}"')
        if order.count(name) > 1:
            raise ResumeError(f'settings.sectionOrder lists "{name}" twice')
    check_object(data.get("header"), "header")
    for key, kind in HEADER_FIELDS.items():
        check_field((data.get("header") or {}).get(key), kind, f"header.{key}")
    check_object(data.get("skills"), "skills")
    for key, kind in SKILL_FIELDS.items():
        check_field((data.get("skills") or {}).get(key), kind, f"skills.{key}")
    for section, fields in ENTRY_FIELDS.items():
        entries = data.get(section)
        if entries is not None and not isinstance(entries, list):
            raise ResumeError(f"{section} must be a list in brackets, like [{{...}}]")
        for i, entry in enumerate(entries or []):
            check_object(entry, f"{section}[{i}]")
            for key, kind in fields.items():
                check_field((entry or {}).get(key), kind, f"{section}[{i}].{key}")


def validate(data):
    """Check field types, the font, and each visible date against its style."""
    check_types(data)
    font_name(data)
    styles = date_styles(data)
    for section in ("education", "projects", "experience"):
        style = styles.get(section, "semester")
        for i, entry in enumerate(data.get(section) or []):
            if not entry or entry.get("hide"):
                continue
            for key in ("gradDate", "start", "end"):
                check_date(entry.get(key), style, f"{section}[{i}].{key}")
            if section == "experience" and present(entry.get("bullets")):
                if not entry.get("engineering"):
                    print(
                        f"Note: experience[{i}] has bullets, but they're left out "
                        'because it doesn\'t have "engineering": true.',
                        file=sys.stderr,
                    )


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
    # Each item is kept whole, so a line never breaks inside a URL.
    if contact:
        out.append(
            "  " + r"\headersep{}".join(rf"\mbox{{{c}}}" for c in contact) + r"\par"
        )
    status = [
        esc(h.get("location")),
        "Willing to relocate" if h.get("relocate") else "",
    ]
    status = [s for s in status if s]
    if status:
        out.append(
            "  " + r"\headersep{}".join(rf"\mbox{{{x}}}" for x in status) + r"\par"
        )
    out.append(r"\end{resumeheader}")
    return out


def bullets(items):
    """Return LaTeX lines for a bullet list, or nothing if there are no bullets."""
    items = present(items)
    if not items:
        return []
    return (
        [r"\begin{itemize}"]
        # \relax stops \item from reading a bullet that starts with "[" as
        # its optional label.
        + [rf"  \item\relax {rich(b)}" for b in items]
        + [r"\end{itemize}"]
    )


def education(data):
    """Return LaTeX lines for the education entries."""
    out = []
    for e in shown(data.get("education")):
        title = rf"\textbf{{{esc(e.get('degree'))}}}"
        if e.get("gpa"):
            title += f", GPA {esc(e['gpa'])}"
        school = link(e.get("url"), esc(e["school"])) if e.get("school") else ""
        date = esc(e.get("gradDate"))
        if school:
            out.append(rf"\eduentry{{{title}}}{{{date}}}{{{school}}}")
        else:
            out.append(rf"\entry{{{title}}}{{{date}}}")
        for label, key in (
            ("Relevant coursework", "coursework"),
            ("Activities", "activities"),
        ):
            if present(e.get(key)):
                out.append(rf"\textbf{{{label}:}} {joined(e[key])}\par")
        out.append(r"\entrygap")
    return out


def projects(data):
    """Return LaTeX lines for the projects: title (tools) and dates, then bullets."""
    out = []
    for p in shown(data.get("projects")):
        title = rf"\textbf{{{link(p.get('url'), esc(p.get('title')))}}}"
        if present(p.get("tools")):
            title += f" ({joined(p['tools'])})"
        dates = date_range(p.get("start"), p.get("end"))
        out.append(rf"\entry{{{title}}}{{{dates}}}")
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
        out.append(rf"\entry{{\textbf{{{name}}}{place}}}{{{dates}}}")
        if x.get("engineering"):
            out += bullets(x.get("bullets"))
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


def metadata(data):
    """Return a hypersetup line for the PDF's document properties.

    The title is "<name> Resume" and the author is the name, as eeprep's
    resume page suggests. The subject is "Resume". A blank name leaves out the
    title and author.
    """
    name = esc((data.get("header") or {}).get("name"))
    fields = [("pdfsubject", "Resume")]
    if name:
        fields = [("pdftitle", f"{name} Resume"), ("pdfauthor", name)] + fields
    return [r"\hypersetup{" + ", ".join(f"{k}={{{v}}}" for k, v in fields) + "}"]


def body(data):
    """Return the LaTeX body: PDF properties, the header, then each section."""
    out = metadata(data) + header(data.get("header") or {})
    order = (data.get("settings") or {}).get("sectionOrder") or list(SECTIONS)
    for name in order:
        lines = RENDER[name](data)
        if lines:
            if lines[-1] == r"\entrygap":
                lines.pop()
            out += [rf"\resumesection{{{TITLES[name]}}}"] + lines
    return "\n".join(out) + "\n"


# Characters that mean the PDF text layer is broken for an applicant tracking
# system: unmapped glyphs, the replacement character, ligature code points
# (fi, fl and friends) and private-use glyphs.
TEXT_JUNK = re.compile(r"\(cid:\d+\)|[\ufffd\ufb00-\ufb06\ue000-\uf8ff]")
# Typographic characters that LaTeX makes from plain ones, mapped back.
TEXT_PLAIN = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
    }
)


def plain(text):
    """Return text as a reader sees it: straight quotes, hyphens, single spaces."""
    text = CONTROL.sub("", str(text or "")).replace("---", "-").replace("--", "-")
    text = re.sub(r"``|''", '"', text).translate(TEXT_PLAIN)
    return " ".join(text.split())


def expected_text(data):
    """Return the strings the PDF must contain, in reading order."""
    out = []
    h = data.get("header") or {}
    out.append(h.get("name"))
    out += [h.get("phone"), h.get("email")]
    out += [short_url(h[k]) for k in ("linkedin", "github", "website") if h.get(k)]
    out.append(h.get("location"))
    out.append("Willing to relocate" if h.get("relocate") else "")

    def names(items):
        return [x.get("name") if isinstance(x, dict) else x for x in present(items)]

    def lines(items):
        return [INLINE_LINK.sub(r"\1", str(b)) for b in present(items)]

    order = (data.get("settings") or {}).get("sectionOrder") or list(SECTIONS)
    for name in order:
        before = len(out)
        if name == "education":
            for e in shown(data.get("education")):
                gpa = f", GPA {e['gpa']}" if e.get("gpa") else ""
                out += [f"{e.get('degree') or ''}{gpa}", e.get("school")]
                out += names(e.get("coursework")) + names(e.get("activities"))
        elif name == "projects":
            for p in shown(data.get("projects")):
                out += [p.get("title")] + names(p.get("tools"))
                out += lines(p.get("bullets"))
        elif name == "experience":
            for x in shown(data.get("experience")):
                out += [x.get("title"), x.get("company"), x.get("location")]
                if x.get("engineering"):
                    out += lines(x.get("bullets"))
        elif name == "skills":
            for key in ("software", "hardwareLab", "certifications"):
                out += names((data.get("skills") or {}).get(key))
        if any(out[before:]):
            out.insert(before, TITLES[name])
    return [plain(x) for x in out if plain(x)]


def check_text(pdf, data):
    """Return problems with the PDF's text layer, or [] if it reads cleanly.

    It extracts the text the way an applicant tracking system does, with
    pdftotext, and checks that every heading, header item, entry and bullet
    is there in reading order, with no broken ligatures or unmapped glyphs.
    """
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [f"pdftotext couldn't read {pdf.name}: {result.stderr.strip()}"]
    raw = result.stdout
    problems = []
    for m in TEXT_JUNK.finditer(raw):
        near = plain(raw[max(0, m.start() - 30) : m.end() + 30])
        problems.append(f'unreadable text "{m.group()}" near "{near}"')
    text, pos = plain(raw), 0
    for want in expected_text(data):
        found = text.find(want, pos)
        if found >= 0:
            pos = found + len(want)
        elif want in text:
            problems.append(f'out of reading order: "{want}"')
        else:
            problems.append(f'missing or garbled: "{want}"')
    return problems


def grow(span, fill):
    """Return the value fill of the way from the compact to the roomy end."""
    low, high = span
    return low + fill * (high - low)


def settings(typeface, font, margin, fill=0.0):
    """Return LaTeX definitions for the font, size, margins and spacing.

    fill runs from 0 (compact) to 1 (roomy) and sets the line spacing and
    gaps together.
    """
    line = font * 1.2 * grow(LINE_SPACING, fill)
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
            rf"\newcommand{{\sectiongap}}{{{grow(SECTION_GAP, fill):.2f}pt}}",
            rf"\newcommand{{\entryspace}}{{{grow(ENTRY_GAP, fill):.2f}pt}}",
            "",
        ]
    )


def compile_once(typeface, font, margin, fill=0.0):
    """Build the PDF at one layout and return the page count and the log text."""
    (BUILD / "settings.tex").write_text(
        settings(typeface, font, margin, fill), encoding="utf-8"
    )
    env = dict(os.environ, SOURCE_DATE_EPOCH="0", FORCE_SOURCE_DATE="1")
    log_file = BUILD / "resume.log"
    # A log left from an earlier run would hide why this one failed.
    log_file.unlink(missing_ok=True)
    try:
        result = subprocess.run(
            [
                "lualatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                # The resume never needs to run programs. Turning shell
                # escape off keeps it that way whatever the TeX config says.
                "-no-shell-escape",
                "-output-directory=build",
                "resume.tex",
            ],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise ResumeError(
            "lualatex isn't installed or isn't on PATH. "
            "Run ./run, which offers to install it."
        ) from None
    if not log_file.exists():
        raise ResumeError(
            f"lualatex exited with code {result.returncode} and wrote no log."
        )
    log = log_file.read_text(encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise ResumeError(latex_error(log))
    pages = re.search(r"Output written on .*?\((\d+) pages?", log, re.S)
    if not pages:
        raise ResumeError(
            "The resume has nothing to print. Fill in at least the header name."
        )
    return int(pages.group(1)), log


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


def overflow(end):
    """Return how many points of content don't fit on page 1 (negative: room).

    The measurement can come before or after LaTeX breaks the page: on page 1
    the overflow is used minus goal, and on page 2 it's what landed there.
    used + (page - 2) * goal covers both.
    """
    page, used, goal, _ = end
    return used + (page - 2) * goal


def fit(typeface):
    """Find the roomiest layout that fits on one page, then fill the page.

    Returns (font, margin, fill, free lines), or None and the log of the
    tightest try when nothing fits.
    """
    for font, margin in LAYOUTS:
        pages, log = compile_once(typeface, font, margin)
        if pages == 1:
            return (font, margin, *fill_page(typeface, font, margin, log)), log
    return None, log


def fill_page(typeface, font, margin, compact_log):
    """Grow the spacing to fill a page that fits, and return (fill, free lines).

    Line breaks don't depend on vertical spacing, so the page's height grows in
    a straight line with fill. One build at the roomy end gives the slope, and
    one more lands on a full page.
    """
    compact = measure(compact_log, "END")
    if not compact:
        return 0.0, 0.0
    line = compact[3]
    reserve = FILL_RESERVE * line
    room = -overflow(compact)
    if room <= reserve:
        return 0.0, room / line
    pages, log = compile_once(typeface, font, margin, 1.0)
    roomy = measure(log, "END")
    if pages == 1 and roomy and -overflow(roomy) >= reserve:
        return 1.0, -overflow(roomy) / line
    # How much room the full step from compact to roomy takes up.
    slope = room + overflow(roomy) if roomy else 0.0
    fill = min(1.0, (room - reserve) / slope) if slope > 0 else 0.0
    pages, log = compile_once(typeface, font, margin, fill)
    end = measure(log, "END")
    if pages != 1 or not end:
        compile_once(typeface, font, margin)
        return 0.0, room / line
    return fill, -overflow(end) / line


def short_bullets(pdf, margin):
    """Return the bullets whose last line fills less than SHORT_LAST_LINE.

    It reads word positions with pdftotext. A bullet's line starts with the
    bullet mark, and its wrapped lines follow it in the same text block.
    """
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    page = re.search(r'<page width="([\d.]+)"', result.stdout)
    if not page:
        return []
    right = float(page.group(1)) - margin * 72
    lines = []
    for block in result.stdout.split("<block")[1:]:
        for line in re.findall(
            r'<line xMin="([\d.]+)"[^>]*xMax="([\d.]+)"[^>]*>'
            r"(.*?)</line>",
            block,
            re.S,
        ):
            words = re.findall(r"<word[^>]*>(.*?)</word>", line[2])
            lines.append((float(line[0]), float(line[1]), words, block))
    short = []
    for i, (_, _, words, block) in enumerate(lines):
        if not words or words[0] != "\u2022" or len(words) < 2:
            continue
        follow = []
        for x, x1, more, other in lines[i + 1 :]:
            if other is not block or not more or more[0] == "\u2022":
                break
            follow.append((x, x1))
        if not follow:
            continue
        x, x1 = follow[-1]
        if (x1 - x) / (right - x) < SHORT_LAST_LINE:
            short.append(plain(html.unescape(" ".join(words[1:6]))))
    return short


def report_layout(pdf, margin, free):
    """Print notes on what eeprep's resume page would change on the page."""
    if free > EMPTY_LINES_NOTE:
        print(
            f"Note: about {free:.0f} lines at the bottom are empty, even with "
            "roomy spacing. Fill the page with content: a class project, lab "
            "work, or another bullet.",
            file=sys.stderr,
        )
    if not shutil.which("pdftotext"):
        return
    for start in short_bullets(pdf, margin):
        print(
            f'Note: the bullet "{start}..." ends with a short second line. Cut '
            "it to one line, or add a detail that fills most of the second.",
            file=sys.stderr,
        )


def report_text(pdf, data):
    """Check the PDF's text layer when pdftotext is installed.

    Problems are warnings, unless RESUME_TEXT_CHECK=strict is set (as in CI),
    which makes them an error.
    """
    if not shutil.which("pdftotext"):
        return
    problems = check_text(pdf, data)
    if not problems:
        print(f"Text check: {pdf.name} extracts cleanly with pdftotext.")
        return
    strict = os.environ.get("RESUME_TEXT_CHECK") == "strict"
    print(
        f"{'Error' if strict else 'Warning'}: {pdf.name} doesn't extract cleanly, "
        "so an applicant tracking system may misread it:",
        file=sys.stderr,
    )
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    if strict:
        sys.exit(1)


def pdf_name(data, source):
    """Return the PDF name: [Name]-Resume.pdf, or Resume.pdf without a name.

    The input's file name is added ([Name]-Resume-[file].pdf) so two files for
    one person don't overwrite each other. resume.json and alex.json add
    nothing, because they are the main file and the starting example.
    """
    name = str((data.get("header") or {}).get("name") or "")
    words = re.sub(r"[^\w]+", " ", name).split()
    words.append("Resume")
    if source.stem not in PLAIN_STEMS:
        stem = re.sub(r"^resume[-_ ]+", "", source.stem, flags=re.I)
        words += re.sub(r"[^\w]+", " ", stem).split()
    return "-".join(words) + ".pdf"


def main():
    """Build the PDF, or exit with a message saying what to fix."""
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "resume.json"
    try:
        # utf-8-sig also reads a file that Windows Notepad saved with a BOM.
        data = json.loads(source.read_text(encoding="utf-8-sig"))
    except OSError as e:
        sys.exit(f"Can't read {source.name}: {e.strerror}")
    except UnicodeDecodeError:
        sys.exit(f"{source.name} isn't a UTF-8 text file. Save it as UTF-8 JSON.")
    except json.JSONDecodeError as e:
        sys.exit(f"{source.name} isn't valid JSON: {e}")
    try:
        validate(data)
        output = source.with_name(pdf_name(data, source))
        typeface = font_name(data)
        BUILD.mkdir(exist_ok=True)
        tex = body(data)
        (BUILD / "body.tex").write_text(tex, encoding="utf-8")
        layout, log = fit(typeface)
        lost = sorted(
            set(
                re.findall(
                    r"Missing character: There is no (\S+) \((U\+[0-9A-F]+)\)", log
                )
            )
        )
        if lost:
            names = " ".join(f"{char} ({code})" for char, code in lost)
            raise ResumeError(
                f"The {typeface} font has no glyph for: {names}\n"
                "These characters would be blank in the PDF. Rewrite them, "
                "or see the limits in the README."
            )
        if layout:
            font, margin, fill, free = layout
            shutil.copy(BUILD / "resume.pdf", output)
            print(
                f"Wrote {output.name} (1 page, {typeface}, {font:g} pt text, "
                f"{margin:g} in margins, line spacing "
                f"{grow(LINE_SPACING, fill):.2f}, section gap "
                f"{grow(SECTION_GAP, fill):.1f} pt)."
            )
            report_layout(output, margin, free)
            report_text(output, data)
            return
    except ResumeError as e:
        sys.exit(str(e))
    end = measure(log, "END")
    lines = 1
    if end:
        lines = max(1, round(overflow(end) / end[3] + 0.5))
    font, margin = LAYOUTS[-1]
    sys.exit(
        f"{source.name} doesn't fit on one page, even at {font:g} pt with "
        f"{margin:g} in margins.\n"
        f"Cut about {lines} line(s). "
        "Try dropping a coursework item first, then a bullet."
    )


if __name__ == "__main__":
    main()
