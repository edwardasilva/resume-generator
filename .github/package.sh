#!/usr/bin/env bash
# Build the release zip: .github/package.sh <name> writes <name>.zip with a <name>/ folder.
# CI uses this one file list for the release and for the check that the zip runs on its own,
# so the two cannot drift. The zip's resume.json is the Alex example, as ./run makes it.
set -euo pipefail
name="$1"
rm -rf "$name" "$name.zip"
mkdir "$name"
cp -r run build.py resume.tex cv.tex README.md LICENSE LICENSE-CONTENT examples fonts "$name/"
# README.md shows the logo from docs/brand/, so the zip carries that folder too.
mkdir "$name/docs"
cp -r docs/brand "$name/docs/"
cp examples/alex.json "$name/resume.json"
echo "$name" > "$name/VERSION"
zip -qr "$name.zip" "$name"
rm -rf "$name"
