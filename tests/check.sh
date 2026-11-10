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
fails 'header.name must be text in quotes' '{"header": {"name": 5}}'
fails 'settings.font must be one of' '{"settings": {"font": "comic"}}'
fails 'unknown section "awards"' '{"settings": {"sectionOrder": ["awards"]}}'
fails "doesn't match the semester date style" '{"projects": [{"title": "A", "start": "Sep 2025"}]}'
fails 'Links must use https://, http://, mailto: or tel:' '{"header": {"name": "Alex Doe", "website": "javascript:alert(1)"}}'
fails 'has no glyph for' '{"header": {"name": "张 Doe"}}'
echo "All checks passed."
