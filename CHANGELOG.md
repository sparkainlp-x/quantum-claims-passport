# Changelog

All notable changes to this project. The claim ledger carries an audit snapshot date; source pages may change after that date.

## Unreleased

## 0.1.0 — 2026-10-05

### Added
- `passport.py`: offline, standard-library CLI with `validate`, `build`, and `conversions`.
- `claims.json`: nine-claim ledger (HUB, THZ, RAT, HYP) with five cited sources and a 2026-10-05 snapshot date.
- Five-label audit vocabulary (announcement/planned, computational model, animal behavioral result, hypothesis, unsupported inference); a classification, not a score.
- Fail-closed fencing: claims about consciousness mechanisms, current operation, direct measurement, or proof must be labelled hypothesis or unsupported inference.
- Exact-SI conversions of the reported 613 ± 8 THz modeled band (wavelength, photon energy, wavenumber) for scale only.
- Static, self-contained `docs/report.html` (GitHub Pages) and original `assets/evidence-ladder.svg`; CI checks both byte for byte against a fresh build.
- Standard-library unit tests (Python 3.10–3.13 in CI).
- `CITATION.cff`, `.zenodo.json`, `ZENODO_METADATA.md`, AGPL-3.0-only `LICENSE`, `COMMERCIAL-LICENSE.md`, `SECURITY.md`.
- Zenodo deposit: concept DOI `10.5281/zenodo.23167801`, version DOI `10.5281/zenodo.23167802`.

### Notes
- An earlier local draft suggested the MIT License; the published project uses AGPL-3.0-only (with a commercial option) for consistency with the other Spark AI NLP research repositories.
