#!/usr/bin/env python3
"""Check that schema/resume.schema.json matches the fields build.py reads.

The schema is made from the field tables in build.py, so the two can't drift.
Run it from the repository root:

    python3 tests/schema.py          # fail if the schema is out of date
    python3 tests/schema.py --write  # rewrite the schema from build.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

SCHEMA = ROOT / "schema" / "resume.schema.json"
RAW = "https://raw.githubusercontent.com/edwardasilva/resume-generator/main/"

# The kinds of field in build.py, each defined once under $defs. null counts as
# blank for any field.
TEXT = {"type": ["string", "null"]}
DEFS = {
    "text": TEXT,
    "flag": {"type": ["boolean", "null"]},
    "lines": {"type": ["array", "null"], "items": TEXT},
    "items": {
        "type": ["array", "null"],
        "items": {
            "anyOf": [
                TEXT,
                {
                    "type": "object",
                    "properties": {"name": TEXT, "url": TEXT},
                    "additionalProperties": False,
                },
            ]
        },
    },
}
KINDS = {kind: {"$ref": f"#/$defs/{kind}"} for kind in DEFS}


def fields(table):
    """Return an object schema for a table of field kinds from build.py."""
    return {
        "type": ["object", "null"],
        "properties": {key: KINDS[kind] for key, kind in table.items()},
        "additionalProperties": False,
    }


def words(defaults):
    """Return an object schema for settings.sectionTitles or settings.labels."""
    return {
        "type": ["object", "null"],
        "description": "CV only. A name left out keeps its default.",
        "properties": {
            key: dict(TEXT, default=value) for key, value in defaults.items()
        },
        "additionalProperties": False,
    }


def schema():
    """Return the JSON Schema for the input file, from build.py's tables."""
    styles = list(build.DATE_STYLES)
    style = {"enum": styles, "default": styles[0]}
    dated = build.DATED_SECTIONS + build.RECORD_SECTIONS
    kinds = list(build.DOCUMENTS)
    settings = {
        "document": {"enum": [*kinds, None], "default": kinds[0]},
        "sectionOrder": {
            "type": ["array", "null"],
            "description": (
                "A resume reads only " + ", ".join(build.SECTIONS) + ". "
                "A section left out is left off the page."
            ),
            "items": {"enum": list(build.CV_SECTIONS)},
            "uniqueItems": True,
        },
        "font": {"enum": [*build.FONTS, None], "default": next(iter(build.FONTS))},
        "dateStyle": {
            "type": ["object", "null"],
            "properties": {name: style for name in dated},
            "additionalProperties": False,
        },
        **{key: words(table) for key, table in build.CV_SETTINGS_KEYS.items()},
    }
    # Each key build.py reads, in its order. A key without a schema here fails
    # with a KeyError, so the two can't drift.
    top = {
        "$schema": {"type": "string"},
        "settings": {
            "type": ["object", "null"],
            "properties": {
                key: settings[key]
                for key in build.SETTINGS_KEYS + tuple(build.CV_SETTINGS_KEYS)
            },
            "additionalProperties": False,
        },
        "header": fields(build.HEADER_FIELDS),
    }
    properties = {key: top[key] for key in build.TOP_KEYS}
    properties["skills"] = fields(build.SKILL_FIELDS)
    for section, table in build.CV_FIELDS.items():
        properties[section] = {"type": ["array", "null"], "items": fields(table)}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": RAW + "schema/resume.schema.json",
        "title": "resume-generator input",
        "description": (
            "One resume or CV for build.py. A blank field or an empty list is "
            "left out of the PDF. A resume reads the education, projects, "
            "experience and skills sections. A CV, with settings.document set "
            "to cv, also reads the record sections, an education entry's "
            "location, thesis and honors, and settings.sectionTitles and "
            "settings.labels. The build checks each date against its "
            "section's date style. It notes a field it doesn't read and "
            "doesn't stop for it. The README field guide explains each field."
        ),
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
        "$defs": DEFS,
    }


def main():
    """Write the schema, or exit 1 if the committed one is out of date."""
    text = json.dumps(schema(), indent=2, ensure_ascii=False) + "\n"
    if "--write" in sys.argv[1:]:
        SCHEMA.parent.mkdir(exist_ok=True)
        SCHEMA.write_text(text, encoding="utf-8")
        return
    if not SCHEMA.is_file() or SCHEMA.read_text(encoding="utf-8") != text:
        sys.exit(
            f"{SCHEMA.relative_to(ROOT)} doesn't match the fields in build.py. "
            "Run python3 tests/schema.py --write and commit the result."
        )
    print(f"{SCHEMA.relative_to(ROOT)} matches build.py.")


if __name__ == "__main__":
    main()
