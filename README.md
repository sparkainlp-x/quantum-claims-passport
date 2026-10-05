# Quantum Claims Evidence Passport

[![CI](https://github.com/sparkainlp-x/quantum-claims-passport/actions/workflows/ci.yml/badge.svg)](https://github.com/sparkainlp-x/quantum-claims-passport/actions/workflows/ci.yml)
[![License: AGPL-3.0-only](https://img.shields.io/badge/license-AGPL--3.0--only-blue.svg)](LICENSE)
[![Report](https://img.shields.io/badge/report-GitHub%20Pages-245a9b.svg)](https://sparkainlp-x.github.io/quantum-claims-passport/report.html)

**A claims audit for scientific communication.** This is a compact, reproducible audit of public claims about (1) the announced IBM/Lockheed Martin/ETH Zurich/CSCS quantum hub and (2) a modeled/reported 613 THz anesthetic–microtubule frequency band. The project keeps announcements, computational/theoretical predictions, animal behavioral results, hypotheses, and unsupported inferences in separate categories rather than blending unlike evidence into a score.

**Rendered report:** <https://sparkainlp-x.github.io/quantum-claims-passport/report.html>

> This project does not imply affiliation with IBM, Lockheed Martin, ETH Zurich, or CSCS. It audits claim types (current quantum-computer availability, consciousness mechanisms, clinical relevance); it does not make those claims.

## Quick start

Requires Python 3.10 or newer (CI runs 3.10–3.13); there are no third-party packages and no network calls at runtime.

```bash
git clone https://github.com/sparkainlp-x/quantum-claims-passport.git
cd quantum-claims-passport
python3 passport.py validate
python3 -m unittest discover -s tests -v
python3 passport.py build
```

Open `report.html` in any browser. The report is static and self-contained; the original vector visual is also available at `assets/evidence-ladder.svg`. Clicking a citation requires an internet connection. The CLI can print the conversion data as JSON with `python3 passport.py conversions` or build to another path with `python3 passport.py build --output /path/to/report.html`. The committed copy at `docs/report.html` (served by GitHub Pages) is checked byte for byte against a fresh build in CI.

## What the audit says

As of the 2026-10-05 audit snapshot, IBM and ETH Zurich describe the System Two at CSCS in Lugano as planned, with deployment/operation expected by the end of 2026; that is not proof that it is already operational or that any particular reader has access ([IBM announcement](https://newsroom.ibm.com/2026-09-10-ibm,-lockheed-martin-announce-swiss-quantum-innovation-hub-at-eth-zurich,-anchored-by-switzerlands-first-ibm-quantum-computer); [ETH Zurich announcement](https://ethz.ch/en/news-and-events/eth-news/news/2026/09/eth-zurich-to-host-a-new-ibm-quantum-computer.html)). This project does not imply affiliation with IBM, Lockheed Martin, ETH Zurich, or CSCS.

The 2017 paper is computational/theoretical: it models collective dipole modes in a tubulin-related model and reports an anesthetic-associated shift in a modeled frequency band around 613 THz (the paper's notation is 613 ± 8 THz). That notation describes the reported modeled band, not a statistical uncertainty estimate or confidence interval; it is not a direct measurement of a brain or tubulin oscillation. The authors say the band's biological significance and relevance to anesthetic action require further investigation ([Craddock et al., *Scientific Reports*](https://www.nature.com/articles/s41598-017-09992-7)). For scale only, conversions from 613 THz give roughly 489 nm vacuum wavelength, 2.535 eV photon energy, and 20,447 cm⁻¹ wavenumber; band-endpoint conversions use 605–621 THz. These are equation-based conversions, not measurements, and do not show that tubulin emits visible light or hosts a biologically active mode. Constants use exact SI values for the speed of light, Planck constant, and elementary charge ([NIST constants](https://physics.nist.gov/cuu/Constants/)).

The 2024 primary study used a within-subject design in eight male Long–Evans rats (N=8). It used latency to loss of righting reflex (LORR) as a behavioral proxy for becoming unconscious; under 4% isoflurane, the reported mean LORR latency increased by about +69 seconds after epothilone B treatment (two-tailed permutation t test, p=0.0016). The study did not measure 613 THz and does not establish a quantum-consciousness mechanism. This animal result does not establish human outcomes and is not clinical advice ([Khan et al., *eNeuro*](https://www.eneuro.org/content/11/8/ENEURO.0291-24.2024)). A 2025 review argues for a broader quantum-microtubule account, but that is the review author's synthesis and does not independently validate this specific modeled frequency band ([Wiest, *Neuroscience of Consciousness*](https://pmc.ncbi.nlm.nih.gov/articles/PMC12060853/)).

### Evidence labels

| Label | What it records | What it is not |
|---|---|---|
| `announcement_planned` | What an organization says, with status and expected dates | Proof of current operation or access |
| `computational_model` | What a model predicts | A biological measurement |
| `animal_behavioral` | What animals did in a test | A readout of the modeled band; a human outcome |
| `hypothesis` | A proposed explanation | A settled mechanism |
| `unsupported_inference` | A claim that exceeds its source | Something to promote to fact |

The labels are a classification, not a ranking or score. `passport.py validate` fails closed if a claim statement about consciousness, current operation, direct measurement, or proof is labelled as anything other than `hypothesis` or `unsupported_inference`, or if a fenced claim's assessment does not say what is not established.

## Intended audience and limits

Designed for non-specialist reviewers, research communicators, and finance/operations readers who need a fast way to distinguish an announced project from a scientific result or an extrapolation. The labels are an audit vocabulary, not a quality score or a consensus rating. The project does not establish clinical relevance, a causal or consciousness mechanism, human outcomes, current device availability, or individual access. It is not medical, scientific, or investment advice.

## Data and reproduction

`claims.json` is the machine-readable claim ledger. Each claim has a stable ID, its evidence label, an assessment, and one or more source IDs; source records hold the exact URLs (and DOIs where available). `passport.py` validates those relationships, converts the modeled/reported frequency band using SI constants, and renders an offline report plus an original SVG. Tests cover the conversion equations and band-endpoint ordering, expected evidence labels, required claim classifications, citations, reported study details, fail-closed validation, and static output. No claim text or web content is fetched at runtime.

No paper text or figure, screenshot, logo, or third-party image is copied into this project. The Python code, report layout, and SVG visual are original. Source descriptions use original factual summaries with direct citations.

## Related tools

- [**evidence-passport**](https://github.com/sparkainlp-x/evidence-passport) ([DOI 10.5281/zenodo.23165143](https://doi.org/10.5281/zenodo.23165143)): a sibling audit tool that turns one experiment-run manifest into a static evidence passport with fail-closed SHA-256 checks. Evidence Passport audits *one run's declared evidence*; this project audits *public claims against their sources*.

## License

Copyright (C) 2026 Jean-François Brisson / Spark AI NLP. The Python code and the original SVG/HTML design are released under the GNU Affero General Public License v3.0 only (AGPL-3.0-only); see [LICENSE](LICENSE). For proprietary use without AGPL obligations, see [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

Source descriptions are written in original language and point to the source publishers; external pages remain governed by their owners' terms. No third-party artwork, logos, article text, or images are bundled. This project is not legal advice.

## Cite

See [`CITATION.cff`](CITATION.cff) (GitHub's "Cite this repository" button). No Zenodo DOI has been minted yet; the draft metadata is in [`ZENODO_METADATA.md`](ZENODO_METADATA.md) and [`.zenodo.json`](.zenodo.json). A DOI will be added only after a release is archived.

Author: Jean-François Brisson, Spark AI NLP · ORCID [0009-0000-9778-5374](https://orcid.org/0009-0000-9778-5374)

## Security

See [SECURITY.md](SECURITY.md).
