# Fonts

These are the regular and bold weights of the three fonts `settings.font` allows, unmodified from their upstream releases. `build.py` loads them from this folder, so the build doesn't depend on the fonts installed on the system.

| Files | Font | Version | Source | License |
| --- | --- | --- | --- | --- |
| `LibertinusSerif-Regular.otf`, `LibertinusSerif-Bold.otf` | Libertinus Serif | 7.051 | [Libertinus releases](https://github.com/alerque/libertinus/releases/tag/v7.051) | SIL Open Font License 1.1, [OFL.txt](OFL.txt) |
| `texgyretermes-regular.otf`, `texgyretermes-bold.otf` | TeX Gyre Termes | 2.004 | [CTAN tex-gyre](https://ctan.org/pkg/tex-gyre) | GUST Font License, [GUST-FONT-LICENSE.txt](GUST-FONT-LICENSE.txt), which is the LaTeX Project Public License 1.3c or later, [lppl.txt](lppl.txt) |
| `texgyreheros-regular.otf`, `texgyreheros-bold.otf` | TeX Gyre Heros | 2.004 | [CTAN tex-gyre](https://ctan.org/pkg/tex-gyre) | GUST Font License, [GUST-FONT-LICENSE.txt](GUST-FONT-LICENSE.txt), which is the LaTeX Project Public License 1.3c or later, [lppl.txt](lppl.txt) |

## Copyright

- Libertinus Serif: Copyright 2012-2024 The Libertinus Project Authors. The full notice is at the top of [OFL.txt](OFL.txt).
- TeX Gyre Termes and TeX Gyre Heros: Copyright 2006-2009 (Termes) and 2007-2009 (Heros) for TeX Gyre extensions by B. Jackowski and J.M. Nowacki (on behalf of TeX Users Groups). Vietnamese characters were added by Han The Thanh. The upstream notices are in [README-TeX-Gyre-Termes.txt](README-TeX-Gyre-Termes.txt) and [README-TeX-Gyre-Heros.txt](README-TeX-Gyre-Heros.txt).

The four TeX Gyre `.otf` files here are part of the TeX Gyre collection, not all of it. The complete, unmodified collection, with the MANIFEST files the two READMEs refer to, is in the [tex-gyre package on CTAN](https://ctan.org/pkg/tex-gyre).

`GUST-FONT-LICENSE.txt`, `README-TeX-Gyre-Termes.txt` and `README-TeX-Gyre-Heros.txt` are copied unmodified from the `doc` folder of the CTAN tex-gyre package. `lppl.txt` is LPPL version 1.3c, copied unmodified from [latex-project.org](https://www.latex-project.org/lppl.txt).
