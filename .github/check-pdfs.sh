#!/usr/bin/env bash
# Fail unless each resume PDF is one page, each CV PDF is one or two pages, the example CV
# is exactly two, and every PDF embeds only fonts from fonts/. A CV is a PDF named
# [Name]-CV.pdf, [Name]-CV-[file].pdf, CV.pdf or CV-[file].pdf.
set -euo pipefail
for pdf in "$@"; do
  pages="$(pdfinfo "$pdf" | awk '/^Pages:/ {print $2}')"
  fonts="$(pdffonts "$pdf" | tail -n +3 | awk '{print $1}' | sed 's/^[A-Z]*+//' | sort -u | tr '\n' ' ')"
  echo "$pdf: $pages page(s), fonts: $fonts"
  case "$(basename "$pdf")" in
    *-CV.pdf|*-CV-*.pdf|CV.pdf|CV-*.pdf)
      [ "$pages" = "1" ] || [ "$pages" = "2" ] || { echo "$pdf is not one or two pages" >&2; exit 1; }
      if [ "$(basename "$pdf")" = "Alex-Doe-CV.pdf" ]; then
        [ "$pages" = "2" ] || { echo "$pdf must be exactly two pages" >&2; exit 1; }
      fi ;;
    *) [ "$pages" = "1" ] || { echo "$pdf is not one page" >&2; exit 1; } ;;
  esac
  for font in $fonts; do
    [[ "$font" =~ ^(LibertinusSerif|TeXGyreTermes|TeXGyreHeros)- ]] || { echo "$pdf uses $font, which isn't in fonts/" >&2; exit 1; }
  done
  [ -n "$fonts" ] || { echo "$pdf embeds no fonts" >&2; exit 1; }
done
