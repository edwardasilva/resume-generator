#!/usr/bin/env python3
"""Build a one-page PDF resume, or a two-page CV, from a JSON file.

Usage: build.py [file.json]

The default input is resume.json. The PDF is written next to the input file
and named after the header name: resume.json becomes Alex-Doe-Resume.pdf.
Any other input adds its file name, so examples/new-grad.json becomes
examples/Alex-Doe-Resume-new-grad.pdf, and resume-firmware.json becomes
Alex-Doe-Resume-firmware.pdf. A file named alex.json keeps Alex-Doe-Resume.pdf.

A file with "settings": {"document": "cv"} builds a CV instead, from cv.tex:
up to two pages, every section and entry printed, and the extra sections for
honors, scholarships, activities, organizations and certifications. It is
named Alex-Doe-CV.pdf. Without that setting the file is a one-page resume.

The script reads the JSON file, writes the LaTeX body and layout settings into
build/, runs LuaLaTeX, and tries layouts from roomiest to tightest until one
fits within the page cap. It uses only the Python standard library. Run it
through ./run, which installs Python and TeX first if they are missing.
"""

import difflib
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
# How many times to build with less fill when the spacing that should fill the
# pages pushes content onto one more page.
FILL_TRIES = 4
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
# A CV adds sections of plain records: a title, who gave it or where, a date
# and optional bullets.
RECORD_SECTIONS = (
    "honors",
    "scholarships",
    "certifications",
    "activities",
    "organizations",
)
CV_SECTIONS = (
    "education",
    "honors",
    "scholarships",
    "experience",
    "projects",
    "skills",
    "certifications",
    "activities",
    "organizations",
)

# The two kinds of document. template is the TeX file, and its name is also
# the LaTeX job name, so a resume and a CV never share build files. cap is the
# most pages the document may take. A CV also prints every entry, bullets on
# any job included.
DOCUMENTS = {
    "resume": {"template": "resume.tex", "job": "resume", "cap": 1, "noun": "resume"},
    "cv": {"template": "cv.tex", "job": "cv", "cap": 2, "noun": "CV"},
}
PAGE_WORDS = {1: "one page", 2: "two pages"}
SEMESTER = re.compile(r"^(Expected )?(Spring|Summer|Fall|Winter) \d{4}$")
YEAR = re.compile(r"^(Expected )?\d{4}$")
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


def esc(text, start=True):
    """Escape text for LaTeX in a single pass.

    Runs of spaces, tabs and line breaks become one space, so a blank line
    pasted into a bullet can't start a new paragraph. Control characters are
    dropped. A no-break space is kept.

    A straight double quote becomes an opening or closing curly quote, or
    stays straight after a digit as an inch mark. start is False when the
    text follows a link, so a quote at its start closes. Runs of hyphens and of
    apostrophes stay as typed: LaTeX would otherwise join them into a dash or
    a double quote, and a search for --yes would not find it.
    """
    text = re.sub(r"[ \t\n\r\f\v]+", " ", CONTROL.sub("", str(text or "")))
    text = TEX_RE.sub(lambda m: TEX_SPECIAL[m.group()], text)
    text = re.sub(r"(?<=\d)\"", r"\\textquotedbl{}", text)
    opening = r"(?:^|(?<=[ \u00a0(]))\"" if start else r"(?<=[ \u00a0(])\""
    text = re.sub(opening, "\u201c", text).replace('"', "\u201d")
    return re.sub(r"([-'])(?=\1)", r"\1\\kern0pt{}", text)


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


# The example handles nobody can own. They print as text, never as links.
PLACEHOLDER_URL = re.compile(
    r"^(github\.com/your-username|linkedin\.com/in/your-name)(?:[/?#]|$)"
)


def link(url, text):
    """Wrap LaTeX text in a hyperlink to url.

    Returns the text alone if url is blank or is a placeholder such as
    github.com/your-username.
    """
    if not url or PLACEHOLDER_URL.match(short_url(url).lower()):
        return text
    return rf"\href{{{esc_url(url)}}}{{{text}}}"


# A Markdown-style inline link in bullet text: [text](url). The URL may hold
# balanced parentheses, as in en.wikipedia.org/wiki/Buck_(converter).
INLINE_LINK = re.compile(r"\[([^\[\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")


def rich(text):
    """Escape bullet text, turning each [text](url) into a hyperlink."""
    text, out, last = str(text or ""), [], 0
    for m in INLINE_LINK.finditer(text):
        before = esc(text[last : m.start()], last == 0)
        out += [before, link(m.group(2), esc(m.group(1)))]
        last = m.end()
    return "".join(out) + esc(text[last:], last == 0)


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
    pattern = {"semester": SEMESTER, "month": MONTH, "year": YEAR}[style]
    if not pattern.match(value):
        example = {"semester": "Fall 2025", "month": "Sep 2025", "year": "2025"}[style]
        raise ResumeError(
            f'{where}: "{value}" doesn\'t match the {style} date style '
            f'(like "{example}")'
        )


def date_parts(start, end):
    """Return the dates a range shows: Present for a blank end, one date if equal."""
    start, end = start or "", end or ""
    if start and not end:
        end = "Present"
    if not start or start == end:
        return [start or end]
    return [start, end]


def date_range(start, end):
    """Format a date range for LaTeX, joining two dates with an en dash."""
    return " -- ".join(esc(d) for d in date_parts(start, end))


def date_styles(data):
    """Return the date style for each section, checking that each one is valid."""
    styles = (data.get("settings") or {}).get("dateStyle") or {}
    if not isinstance(styles, dict):
        raise ResumeError(
            'settings.dateStyle must be an object, like {"projects": "semester"}'
        )
    for section, style in styles.items():
        if style not in ("semester", "month", "year"):
            raise ResumeError(
                f'settings.dateStyle.{section} must be "semester", "month" or "year"'
            )
    return styles


def is_cv(data):
    """Return True if the file asks for a CV with settings.document."""
    settings = data.get("settings") if isinstance(data, dict) else None
    return isinstance(settings, dict) and settings.get("document") == "cv"


def prints_bullets(job, data):
    """Return True if a job's bullets print.

    A CV prints every job's bullets. A resume prints an engineering job's
    bullets, and a non-engineering job's bullets only while the resume has no
    engineering job to show.
    """
    if is_cv(data) or job.get("engineering"):
        return True
    return not any(x.get("engineering") for x in shown(data.get("experience")))


def document(data):
    """Return the DOCUMENTS entry for the file: the resume unless it is a CV."""
    return DOCUMENTS["cv" if is_cv(data) else "resume"]


def sections_of(data):
    """Return the section names this kind of document knows, in default order."""
    return CV_SECTIONS if is_cv(data) else SECTIONS


# Default words printed in the PDF. A CV can replace them in settings.labels
# and settings.sectionTitles; a resume always uses these.
TITLES = {
    "education": "Education",
    "projects": "Projects",
    "experience": "Experience",
    "skills": "Skills",
    "honors": "Honors and Awards",
    "scholarships": "Scholarships",
    "certifications": "Certifications",
    "activities": "Activities",
    "organizations": "Organizations",
}
LABELS = {
    "gpa": "GPA",
    "coursework": "Relevant coursework",
    "activities": "Activities",
    "honors": "Honors",
    "thesis": "Thesis",
    "software": "Software",
    "hardwareLab": "Hardware/Lab",
    "skillsCertifications": "Certifications",
    "relocate": "Willing to relocate",
}


def settings_text(data, key, defaults):
    """Return defaults with the CV's own words from settings[key] laid over."""
    words = dict(defaults)
    if is_cv(data):
        given = (data.get("settings") or {}).get(key) or {}
        words.update({k: v for k, v in given.items() if v})
    return words


def titles(data):
    """Return the title of each section, from settings.sectionTitles in a CV."""
    return settings_text(data, "sectionTitles", TITLES)


def labels(data):
    """Return the label words, from settings.labels in a CV."""
    return settings_text(data, "labels", LABELS)


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
# The fields a CV reads: the same entries as a resume, plus a few more on an
# education entry, and the record sections.
RECORD_FIELDS = {
    **dict.fromkeys(
        ("title", "organization", "location", "url", "date", "start", "end"), "text"
    ),
    "bullets": "lines",
    "hide": "flag",
}
CV_FIELDS = {
    **ENTRY_FIELDS,
    "education": {
        **ENTRY_FIELDS["education"],
        **dict.fromkeys(("location", "thesis"), "text"),
        "honors": "items",
    },
    **dict.fromkeys(RECORD_SECTIONS, RECORD_FIELDS),
}


def entry_fields(data):
    """Return the entry fields of each section for this kind of document."""
    return CV_FIELDS if is_cv(data) else ENTRY_FIELDS


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
                note_unknown(x, ("name", "url"), f"{where}[{i}].")
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


def note_unknown(value, known, where=""):
    """Print a note for each key of a JSON object that this tool doesn't read.

    A misspelled key is otherwise skipped in silence, and what it holds never
    reaches the page. The note suggests the closest known key, if one is near.
    """
    if not isinstance(value, dict):
        return
    lowered = {name.lower(): name for name in known}
    for key in value:
        if key in known:
            continue
        close = difflib.get_close_matches(key.lower(), lowered, n=1)
        hint = f" Did you mean {lowered[close[0]]}?" if close else ""
        print(
            f"Note: {where}{key} isn't a field this tool reads.{hint}",
            file=sys.stderr,
        )


def check_types(data):
    """Check that every field has the type the layout expects.

    A key this tool doesn't read gets a note, not an error.
    """
    if not isinstance(data, dict):
        raise ResumeError("The resume file must hold one object in braces, {...}")
    settings = data.get("settings")
    check_object(settings, "settings")
    settings = settings or {}
    check_field(settings.get("document"), "text", "settings.document")
    if settings.get("document") not in (None, "resume", "cv"):
        raise ResumeError(
            f'settings.document must be "resume" or "cv", not "{settings["document"]}"'
        )
    cv = is_cv(data)
    fields = entry_fields(data)
    note_unknown(data, ("settings", "header", *sections_of(data)))
    own = ("document", "sectionOrder", "font", "dateStyle")
    note_unknown(
        settings, own + (("sectionTitles", "labels") if cv else ()), "settings."
    )
    note_unknown(settings.get("dateStyle"), fields, "settings.dateStyle.")
    if cv:
        for key, known in (("sectionTitles", TITLES), ("labels", LABELS)):
            check_object(settings.get(key), f"settings.{key}")
            note_unknown(settings.get(key), known, f"settings.{key}.")
            for name, value in (settings.get(key) or {}).items():
                check_field(value, "text", f"settings.{key}.{name}")
    check_field(settings.get("font"), "text", "settings.font")
    order = settings.get("sectionOrder")
    check_field(order, "lines", "settings.sectionOrder")
    for name in order or []:
        if name not in sections_of(data):
            raise ResumeError(f'settings.sectionOrder: unknown section "{name}"')
        if order.count(name) > 1:
            raise ResumeError(f'settings.sectionOrder lists "{name}" twice')
    check_object(data.get("header"), "header")
    note_unknown(data.get("header"), HEADER_FIELDS, "header.")
    for key, kind in HEADER_FIELDS.items():
        check_field((data.get("header") or {}).get(key), kind, f"header.{key}")
    check_object(data.get("skills"), "skills")
    note_unknown(data.get("skills"), SKILL_FIELDS, "skills.")
    for key, kind in SKILL_FIELDS.items():
        check_field((data.get("skills") or {}).get(key), kind, f"skills.{key}")
    for section, section_fields in fields.items():
        entries = data.get(section)
        if entries is not None and not isinstance(entries, list):
            raise ResumeError(f"{section} must be a list in brackets, like [{{...}}]")
        for i, entry in enumerate(entries or []):
            check_object(entry, f"{section}[{i}]")
            note_unknown(entry, section_fields, f"{section}[{i}].")
            for key, kind in section_fields.items():
                check_field((entry or {}).get(key), kind, f"{section}[{i}].{key}")


def note_left_out(data):
    """Print a note for each section with content that sectionOrder leaves out."""
    order = (data.get("settings") or {}).get("sectionOrder")
    if not order:
        return
    skills = data.get("skills") or {}
    for section in sections_of(data):
        if section in order:
            continue
        if section == "skills":
            filled = any(present(skills.get(key)) for key in SKILL_FIELDS)
        else:
            filled = bool(shown(data.get(section)))
        if filled:
            print(
                f"Note: {section} has content, but it's left off the page "
                "because settings.sectionOrder doesn't list it.",
                file=sys.stderr,
            )


def validate(data):
    """Check field types, the font, and each visible date against its style."""
    check_types(data)
    note_left_out(data)
    font_name(data)
    styles = date_styles(data)
    cv = is_cv(data)
    dated = ("education", "projects", "experience") + (RECORD_SECTIONS if cv else ())
    for section in dated:
        style = styles.get(section, "semester")
        for i, entry in enumerate(data.get(section) or []):
            if not entry or entry.get("hide"):
                continue
            if cv and entry.get("date") and (entry.get("start") or entry.get("end")):
                raise ResumeError(
                    f'{section}[{i}] has "date" and "start" or "end". '
                    "Use one date, or a range, not both."
                )
            for key in ("gradDate", "start", "end") + (("date",) if cv else ()):
                check_date(entry.get(key), style, f"{section}[{i}].{key}")
            # A non-engineering job loses its bullets once the resume has an
            # engineering job. A CV prints the bullets of every job.
            if section == "experience" and present(entry.get("bullets")):
                if not prints_bullets(entry, data):
                    print(
                        f"Note: experience[{i}] has bullets, but they're left out "
                        'because it doesn\'t have "engineering": true and the '
                        "resume already has an engineering job.",
                        file=sys.stderr,
                    )


def header(h, relocate="Willing to relocate"):
    """Return LaTeX lines for the centered name, contact line and status line."""
    out = [
        r"\begin{resumeheader}",
        rf"  {{\resumename {esc(h.get('name'))}}}\par\vspace{{3pt}}",
    ]
    contact = []
    if h.get("phone"):
        # Dial only the number: drop a trailing extension such as "ext. 12".
        number = re.split(r"(?i)\s*(?:ext\.?|x|#)\s*\d+\s*$", h["phone"])[0]
        digits = re.sub(r"[^\d+]", "", number)
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
        esc(relocate) if h.get("relocate") else "",
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
    cv, lab = is_cv(data), labels(data)
    # A CV also prints the thesis and honors, and the school's location.
    lists = [(lab["coursework"], "coursework"), (lab["activities"], "activities")]
    if cv:
        lists.insert(0, (lab["honors"], "honors"))
    for e in shown(data.get("education")):
        title = rf"\textbf{{{esc(e.get('degree'))}}}"
        if e.get("gpa"):
            title += f", {esc(lab['gpa'])} {esc(e['gpa'])}"
        school = link(e.get("url"), esc(e["school"])) if e.get("school") else ""
        if cv and e.get("location"):
            school = ", ".join(p for p in (school, esc(e["location"])) if p)
        date = esc(e.get("gradDate"))
        if cv and not date:
            # A CV also shows a range of dates for study that has no graduation.
            date = date_range(e.get("start"), e.get("end"))
        if school:
            out.append(rf"\eduentry{{{title}}}{{{date}}}{{{school}}}")
        else:
            out.append(rf"\entry{{{title}}}{{{date}}}")
        if cv and e.get("thesis"):
            out.append(rf"\textbf{{{esc(lab['thesis'])}:}} {esc(e['thesis'])}\par")
        for label, key in lists:
            if present(e.get(key)):
                out.append(rf"\textbf{{{esc(label)}:}} {joined(e[key])}\par")
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
    """Return LaTeX lines for experience, with bullets where prints_bullets allows."""
    out = []
    for x in shown(data.get("experience")):
        title = esc(x.get("title"))
        if x.get("company"):
            company = link(x.get("url"), esc(x["company"]))
            name = ", ".join(p for p in (title, company) if p)
        else:
            name = link(x.get("url"), title)
        place = f", {esc(x['location'])}" if x.get("location") else ""
        dates = date_range(x.get("start"), x.get("end"))
        out.append(rf"\entry{{\textbf{{{name}}}{place}}}{{{dates}}}")
        if prints_bullets(x, data):
            out += bullets(x.get("bullets"))
        out.append(r"\entrygap")
    return out


def skills(data):
    """Return one LaTeX line for each non-empty skill group."""
    s, lab = data.get("skills") or {}, labels(data)
    groups = (
        (lab["software"], "software"),
        (lab["hardwareLab"], "hardwareLab"),
        (lab["skillsCertifications"], "certifications"),
    )
    return [
        rf"\textbf{{{esc(label)}:}} {joined(s.get(key))}\par"
        for label, key in groups
        if present(s.get(key))
    ]


def records(section):
    """Return the renderer for a CV section of plain records.

    Each record is a bold title, then who gave it and where, with the date at
    the right and optional bullets below. The date is one value in "date", or a
    range in "start" and "end".
    """

    def render(data):
        out = []
        for r in shown(data.get(section)):
            title = link(r.get("url"), esc(r.get("title"))) if r.get("title") else ""
            parts = [rf"\textbf{{{title}}}"] if title else []
            parts += [esc(r[k]) for k in ("organization", "location") if r.get(k)]
            dates = (
                esc(r["date"])
                if r.get("date")
                else date_range(r.get("start"), r.get("end"))
            )
            out.append(rf"\entry{{{', '.join(parts)}}}{{{dates}}}")
            out += bullets(r.get("bullets"))
            out.append(r"\entrygap")
        return out

    return render


RENDER = {
    "education": education,
    "projects": projects,
    "experience": experience,
    "skills": skills,
    **{name: records(name) for name in RECORD_SECTIONS},
}


def metadata(data):
    """Return a hypersetup line for the PDF's document properties.

    The title is "<name> Resume" (or "<name> CV") and the author is the name,
    as eeprep's resume page suggests. The subject is "Resume" or "Curriculum
    Vitae". A blank name leaves out the title and author.
    """
    name = esc((data.get("header") or {}).get("name"))
    noun, subject = ("CV", "Curriculum Vitae") if is_cv(data) else ("Resume",) * 2
    fields = [("pdfsubject", subject)]
    if name:
        fields = [("pdftitle", f"{name} {noun}"), ("pdfauthor", name)] + fields
    return [r"\hypersetup{" + ", ".join(f"{k}={{{v}}}" for k, v in fields) + "}"]


def body(data):
    """Return the LaTeX body: PDF properties, the header, then each section."""
    lab, words = labels(data), titles(data)
    out = metadata(data) + header(data.get("header") or {}, lab["relocate"])
    order = (data.get("settings") or {}).get("sectionOrder") or list(sections_of(data))
    for name in order:
        lines = RENDER[name](data)
        if lines:
            if lines[-1] == r"\entrygap":
                lines.pop()
            out += [rf"\resumesection{{{esc(words[name])}}}"] + lines
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
    text = CONTROL.sub("", str(text or "")).translate(TEXT_PLAIN)
    return " ".join(text.split())


def expected_text(data):
    """Return the strings the PDF must contain, in reading order."""
    out = []
    cv, lab, words = is_cv(data), labels(data), titles(data)
    h = data.get("header") or {}
    out.append(h.get("name"))
    out += [h.get("phone"), h.get("email")]
    out += [short_url(h[k]) for k in ("linkedin", "github", "website") if h.get(k)]
    out.append(h.get("location"))
    out.append(lab["relocate"] if h.get("relocate") else "")

    def names(items):
        return [x.get("name") if isinstance(x, dict) else x for x in present(items)]

    def lines(items):
        return [INLINE_LINK.sub(r"\1", str(b)) for b in present(items)]

    order = (data.get("settings") or {}).get("sectionOrder") or list(sections_of(data))
    for name in order:
        before = len(out)
        if name == "education":
            for e in shown(data.get("education")):
                gpa = f", {lab['gpa']} {e['gpa']}" if e.get("gpa") else ""
                out += [f"{e.get('degree') or ''}{gpa}", e.get("school")]
                if cv:
                    out += [e.get("location"), e.get("thesis")]
                    out += names(e.get("honors"))
                out += names(e.get("coursework")) + names(e.get("activities"))
        elif name == "projects":
            for p in shown(data.get("projects")):
                out += [p.get("title")] + names(p.get("tools"))
                out += lines(p.get("bullets"))
        elif name == "experience":
            for x in shown(data.get("experience")):
                out += [x.get("title"), x.get("company"), x.get("location")]
                if prints_bullets(x, data):
                    out += lines(x.get("bullets"))
        elif name == "skills":
            for key in ("software", "hardwareLab", "certifications"):
                out += names((data.get("skills") or {}).get(key))
        elif name in RECORD_SECTIONS:
            for r in shown(data.get(name)):
                out += [r.get("title"), r.get("organization"), r.get("location")]
                out += lines(r.get("bullets"))
        if any(out[before:]):
            out.insert(before, words[name])
    return [plain(x) for x in out if plain(x)]


def expected_dates(data):
    """Return every date and date range the PDF must contain."""
    cv = is_cv(data)
    out = []
    for e in shown(data.get("education")):
        if cv and not e.get("gradDate"):
            out.append(" - ".join(date_parts(e.get("start"), e.get("end"))))
        else:
            out.append(e.get("gradDate"))
    for section in ("projects", "experience") + (RECORD_SECTIONS if cv else ()):
        for x in shown(data.get(section)):
            if cv and x.get("date"):
                out.append(x["date"])
            else:
                out.append(" - ".join(date_parts(x.get("start"), x.get("end"))))
    return [plain(x) for x in out if plain(x)]


def check_text(pdf, data):
    """Return problems with the PDF's text layer, or [] if it reads cleanly.

    It extracts the text the way an applicant tracking system does, with
    pdftotext, and checks that every heading, header item, entry and bullet
    is there in reading order, that every date is there, and that there are
    no broken ligatures or unmapped glyphs.
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
    # Dates sit at the right margin, so their place in the text varies. Check
    # only that each one is there.
    for want in expected_dates(data):
        if want not in text:
            problems.append(f'missing or garbled date: "{want}"')
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


def compile_once(doc, typeface, font, margin, fill=0.0):
    """Build the PDF at one layout and return the page count and the log text."""
    (BUILD / "settings.tex").write_text(
        settings(typeface, font, margin, fill), encoding="utf-8"
    )
    env = dict(os.environ, SOURCE_DATE_EPOCH="0", FORCE_SOURCE_DATE="1")
    log_file = BUILD / f"{doc['job']}.log"
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
                doc["template"],
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
        raise ResumeError(latex_error(log, log_file))
    pages = re.search(r"Output written on .*?\((\d+) pages?", log, re.S)
    if not pages:
        raise ResumeError(
            f"The {doc['noun']} has nothing to print. Fill in at least the header name."
        )
    return int(pages.group(1)), log


def latex_error(log, log_file):
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
    return f"LaTeX failed: {error}\n{hint}\nThe full log is in {log_file}"


def measure(log, key):
    """Read a measurement written by resume.tex or cv.tex from the log.

    Returns (page, used, goal, line) in points, or None if it is missing.
    """
    pattern = (
        rf"RESUME-{key} page=(\d+) used=([\d.]+)pt "
        rf"goal=([\d.]+)pt line=([\d.]+)pt"
    )
    m = re.search(pattern, log)
    return (int(m.group(1)), *map(float, m.groups()[1:])) if m else None


def overflow(end, cap=1):
    """Return how many points of content don't fit in cap pages (negative: room).

    The measurement can come before or after LaTeX breaks the page: on the last
    page the overflow is used minus goal, and on the page after it's what landed
    there. used + (page - cap - 1) * goal covers both, and an earlier page too.
    """
    page, used, goal, _ = end
    return used + (page - cap - 1) * goal


def fit(doc, typeface):
    """Find the roomiest layout that fits the page cap, then fill the pages.

    Returns (font, margin, fill, free lines, pages), or None and the log of
    the tightest try when nothing fits.
    """
    for font, margin in LAYOUTS:
        pages, log = compile_once(doc, typeface, font, margin)
        if pages <= doc["cap"]:
            fill, free = fill_page(doc, typeface, font, margin, log, pages)
            return (font, margin, fill, free, pages), log
    return None, log


def fill_page(doc, typeface, font, margin, compact_log, pages):
    """Grow the spacing to fill the used pages, and return (fill, free lines).

    pages is how many pages the compact layout takes. The fill never adds a
    page, so a CV that fits on one page stays on one.

    Line breaks don't depend on vertical spacing, so the height of the pages
    grows in a straight line with fill. One build at the roomy end gives the
    slope, and one more lands on full pages. A page break can still move when
    the spacing grows, so a try that adds a page is retried with less fill.
    """
    compact = measure(compact_log, "END")
    if not compact:
        return 0.0, 0.0
    line = compact[3]
    reserve = FILL_RESERVE * line
    room = -overflow(compact, pages)
    if room <= reserve:
        return 0.0, room / line
    roomy_pages, log = compile_once(doc, typeface, font, margin, 1.0)
    roomy = measure(log, "END")
    if roomy_pages == pages and roomy and -overflow(roomy, pages) >= reserve:
        return 1.0, -overflow(roomy, pages) / line
    # How much room the full step from compact to roomy takes up.
    slope = room + overflow(roomy, pages) if roomy else 0.0
    fill = min(1.0, (room - reserve) / slope) if slope > 0 else 0.0
    for _ in range(FILL_TRIES if fill > 0 else 0):
        built, log = compile_once(doc, typeface, font, margin, fill)
        end = measure(log, "END")
        if built <= pages and end:
            return fill, -overflow(end, pages) / line
        fill *= 0.75
    compile_once(doc, typeface, font, margin)
    return 0.0, room / line


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
    if is_cv(data):
        # [Name]-CV.pdf. The words "cv" and "resume" in the file name add
        # nothing, so alex-cv.json and cv.json both write [Name]-CV.pdf.
        words.append("CV")
        stem = re.sub(r"[^\w]+", " ", source.stem).split()
        stem = [w for w in stem if w.lower() not in ("cv", "resume")]
        if stem != ["alex"]:
            words += stem
        return "-".join(words) + ".pdf"
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
        doc = document(data)
        output = source.with_name(pdf_name(data, source))
        typeface = font_name(data)
        BUILD.mkdir(exist_ok=True)
        tex = body(data)
        (BUILD / "body.tex").write_text(tex, encoding="utf-8")
        layout, log = fit(doc, typeface)
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
            font, margin, fill, free, pages = layout
            shutil.copy(BUILD / f"{doc['job']}.pdf", output)
            count = f"{pages} page{'s' if pages != 1 else ''}"
            print(
                f"Wrote {output.name} ({count}, {typeface}, {font:g} pt text, "
                f"{margin:g} in margins, line spacing "
                f"{grow(LINE_SPACING, fill):.2f}, section gap "
                f"{grow(SECTION_GAP, fill):.1f} pt)."
            )
            report_layout(output, margin, free)
            report_text(output, data)
            return
    except ResumeError as e:
        sys.exit(str(e))
    except OSError as e:
        # A folder that can't be written to, or a full disk.
        sys.exit(f"Can't write {e.filename or 'the PDF'}: {e.strerror or e}")
    except UnicodeEncodeError:
        # A lone surrogate, such as "\ud800" in the JSON, can't be saved as UTF-8.
        sys.exit(
            f"{source.name} holds a character that isn't valid text. "
            "Retype the field near it."
        )
    end = measure(log, "END")
    lines = 1
    if end:
        lines = max(1, round(overflow(end, doc["cap"]) / end[3] + 0.5))
    font, margin = LAYOUTS[-1]
    advice = "Try dropping a coursework item first, then a bullet."
    if doc["cap"] > 1:
        advice = (
            'A CV prints everything in the file, so add "hide": true to the '
            "weakest entry, or cut a bullet."
        )
    sys.exit(
        f"{source.name} doesn't fit on {PAGE_WORDS[doc['cap']]}, even at "
        f"{font:g} pt with {margin:g} in margins.\n"
        f"Cut about {lines} line(s). {advice}"
    )


if __name__ == "__main__":
    main()
