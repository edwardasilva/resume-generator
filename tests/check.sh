#!/usr/bin/env bash
# Checks the build beyond the examples: LaTeX special characters, symbols and accents in
# every font, exact link targets, and the message for each kind of bad input.
# Needs LuaLaTeX and poppler-utils (pdfinfo, pdftotext).
set -euo pipefail
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for font in libertinus times arial; do
  sed "s/\"font\": \"[a-z]*\"/\"font\": \"$font\"/" tests/special.json > "$tmp/special.json"
  RESUME_TEXT_CHECK=strict python3 build.py "$tmp/special.json"
  pdfinfo -url "$tmp/Alex-Doe-Resume-special.pdf" | awk 'NR > 1 {print $3}' | diff - tests/special.urls
done

# Each bad input must stop the build with a message that names the problem.
fails() {
  printf '%s' "$2" > "$tmp/bad.json"
  if out="$(python3 build.py "$tmp/bad.json" 2>&1)"; then
    echo "Expected a failure for: $2" >&2; exit 1
  fi
  case "$out" in *"$1"*) ;; *) echo "Expected \"$1\", got: $out" >&2; exit 1 ;; esac
}
fails "isn't valid JSON" '{"header": '
fails 'settings.document must be "resume" or "cv"' '{"settings": {"document": "letter"}}'
# The extra CV sections belong to a CV only: a resume keeps its four.
fails 'unknown section "honors"' '{"settings": {"sectionOrder": ["honors"]}}'
fails 'header.name must be text in quotes' '{"header": {"name": 5}}'
fails 'settings.font must be one of' '{"settings": {"font": "comic"}}'
fails 'unknown section "awards"' '{"settings": {"sectionOrder": ["awards"]}}'
fails "doesn't match the semester date style" '{"projects": [{"title": "A", "start": "Sep 2025"}]}'
fails 'Links must use https://, http://, mailto: or tel:' '{"header": {"name": "Alex Doe", "website": "javascript:alert(1)"}}'
fails 'has no glyph for' '{"header": {"name": "张 Doe"}}'
fails "doesn't match the year date style" '{"settings": {"document": "cv", "dateStyle": {"honors": "year"}}, "honors": [{"title": "A", "date": "Fall 2025"}]}'
fails 'Use one date, or a range, not both' '{"settings": {"document": "cv"}, "honors": [{"title": "A", "date": "Fall 2025", "start": "Fall 2024"}]}'

# A CV builds to two pages, with every section from the JSON in the text. A job
# with "engineering": false still prints its bullets.
cp examples/alex-cv.json "$tmp/cv.json"
RESUME_TEXT_CHECK=strict python3 build.py "$tmp/cv.json"
[ "$(pdfinfo "$tmp/Alex-Doe-CV.pdf" | awk '/^Pages:/ {print $2}')" = 2 ]
cv_text="$(pdftotext "$tmp/Alex-Doe-CV.pdf" -)"
for want in "Honors and Awards" "Example Foundation Engineering Scholarship" "Selected coursework" \
  "Fundamentals of Engineering" "Professional Organizations" "Activities and Service" \
  "Handled about [X] customers"; do
  case "$cv_text" in *"$want"*) ;; *) echo "The CV text is missing: $want" >&2; exit 1 ;; esac
done

# A CV that cannot fit on two pages stops the build and names the page cap.
python3 -I -c '
import json, sys
bullets = ["Wrote a line of text that fills most of one line of a bullet in the CV"] * 6
entry = {"title": "Role", "company": "Example Co", "bullets": bullets}
doc = {"settings": {"document": "cv"}, "header": {"name": "Alex Doe"},
       "experience": [dict(entry) for _ in range(30)]}
json.dump(doc, open(sys.argv[1], "w"))
' "$tmp/long.json"
if out="$(python3 build.py "$tmp/long.json" 2>&1)"; then
  echo "Expected the long CV to fail" >&2; exit 1
fi
case "$out" in *"doesn't fit on two pages"*) ;; *) echo "Expected the two-page message, got: $out" >&2; exit 1 ;; esac
echo "All checks passed."
