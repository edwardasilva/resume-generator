#!/usr/bin/env bash
# Fail unless each PDF is one page and embeds only fonts from fonts/.
set -euo pipefail
for pdf in "$@"; do
  pages="$(pdfinfo "$pdf" | awk '/^Pages:/ {print $2}')"
  fonts="$(pdffonts "$pdf" | tail -n +3 | awk '{print $1}' | sed 's/^[A-Z]*+//' | sort -u | tr '\n' ' ')"
  echo "$pdf: $pages page(s), fonts: $fonts"
  [ "$pages" = "1" ] || { echo "$pdf is not one page" >&2; exit 1; }
  for font in $fonts; do
    [[ "$font" =~ ^(LibertinusSerif|TeXGyreTermes|TeXGyreHeros)- ]] || { echo "$pdf uses $font, which isn't in fonts/" >&2; exit 1; }
  done
  [ -n "$fonts" ] || { echo "$pdf embeds no fonts" >&2; exit 1; }
done
