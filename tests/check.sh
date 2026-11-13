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

# A resume shows only gradDate on an education entry, so it notes a start or end it leaves out.
printf '%s' '{"header": {"name": "Alex Doe"}, "education": [{"degree": "B.S. Electrical Engineering", "start": "Fall 2023", "end": "Spring 2027"}]}' > "$tmp/edu.json"
out="$(python3 build.py "$tmp/edu.json" 2>&1)"
case "$out" in *"a resume leaves them out"*) ;; *) echo "Expected a note about education start and end, got: $out" >&2; exit 1 ;; esac

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

# A resume prints a non-engineering job's bullets unless it has an engineering
# job and the rest of the resume fills the page. Then that job drops to one line.
python3 -I -c '
import json, sys
cashier = {"title": "Cashier", "company": "Example Grocery", "start": "May 2025",
           "end": "Present", "engineering": False,
           "bullets": ["Balanced the cash drawer at close on [X] shifts"]}
intern = {"title": "Test Intern", "company": "Example Co", "start": "May 2026",
          "end": "Aug 2026", "engineering": True, "bullets": ["Wrote [X] test scripts"]}
# About 35 lines of engineering bullets fill most of the page, and 30 cashier
# lines cannot fit beside them at any text size.
busy = dict(intern, bullets=["Wrote test script %d for the board bring-up plan" % i
                             for i in range(35)])
crowded = dict(cashier, bullets=["Balanced the cash drawer at close, shift %d" % i
                                 for i in range(30)])
base = {"header": {"name": "Alex Doe"}, "settings": {"dateStyle": {"experience": "month"}}}
json.dump(dict(base, experience=[cashier]), open(sys.argv[1], "w"))
json.dump(dict(base, experience=[intern, cashier]), open(sys.argv[2], "w"))
json.dump(dict(base, experience=[busy, crowded]), open(sys.argv[3], "w"))
' "$tmp/nojob.json" "$tmp/withjob.json" "$tmp/fulljob.json"
python3 build.py "$tmp/nojob.json" 2>/dev/null
case "$(pdftotext "$tmp/Alex-Doe-Resume-nojob.pdf" -)" in
  *"Balanced the cash drawer"*) ;;
  *) echo "A resume with no engineering job left out the other job's bullets" >&2; exit 1 ;;
esac
python3 build.py "$tmp/withjob.json" 2>/dev/null
case "$(pdftotext "$tmp/Alex-Doe-Resume-withjob.pdf" -)" in
  *"Balanced the cash drawer"*) ;;
  *) echo "A resume with room left out the other job's bullets" >&2; exit 1 ;;
esac
out="$(python3 build.py "$tmp/fulljob.json" 2>&1)"
case "$(pdftotext "$tmp/Alex-Doe-Resume-fulljob.pdf" -)" in
  *"Balanced the cash drawer"*) echo "A full resume printed the other job's bullets" >&2; exit 1 ;;
esac
case "$(pdftotext "$tmp/Alex-Doe-Resume-fulljob.pdf" -)" in
  *"test script 34"*) ;;
  *) echo "A full resume left out an engineering bullet" >&2; exit 1 ;;
esac
case "$out" in *"the rest of the resume fills the page"*) ;; *) echo "Expected a note about the left-out bullets, got: $out" >&2; exit 1 ;; esac
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
