#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Jean-François Brisson / Spark AI NLP
"""Quantum Claims Evidence Passport: offline claims-audit CLI.

Validates the claim ledger in ``claims.json``, converts the reported
modeled frequency band with exact SI constants, and renders a static,
self-contained HTML report plus an original SVG evidence-class visual.

Standard library only. No network access at runtime: source URLs are
written into the report as links and are never fetched.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_LEDGER = ROOT / "claims.json"
DEFAULT_REPORT = ROOT / "report.html"
DEFAULT_SVG = ROOT / "assets" / "evidence-ladder.svg"

# Exact SI defining constants (2019 SI; see NIST CODATA).
SPEED_OF_LIGHT = 299_792_458  # m/s, exact
PLANCK = 6.626_070_15e-34  # J*s, exact
ELEMENTARY_CHARGE = 1.602_176_634e-19  # C, exact
THZ = 1e12

# Audit vocabulary: kind of record, NOT a quality score or ranking.
LABELS = {
    "announcement_planned": ("announcement/planned", "blue"),
    "computational_model": ("modelled/computational", "violet"),
    "animal_behavioral": ("animal-study behavioral result", "green"),
    "hypothesis": ("hypothesis", "amber"),
    "unsupported_inference": ("unsupported inference", "red"),
}

# Claim types this project fences: wherever these appear in a claim
# statement, the claim may only be labelled hypothesis or unsupported
# inference, and the assessment must say what is NOT established.
FENCED_TOPICS = re.compile(r"conscious|already operational|directly measured|proves", re.I)
FENCED_LABELS = {"hypothesis", "unsupported_inference"}
FENCE_WORDS = re.compile(r"\bnot\b|does not|do not|not established", re.I)

CLAIM_ID = re.compile(r"^[A-Z]{3}-\d{2}$")


class LedgerError(ValueError):
    """Raised when the claim ledger is inconsistent."""


# --------------------------------------------------------------------------
# Conversions
# --------------------------------------------------------------------------

def wavelength_nm(freq_thz: float) -> float:
    """Vacuum wavelength lambda = c / f, in nanometres."""
    if freq_thz <= 0:
        raise ValueError("frequency must be positive")
    return SPEED_OF_LIGHT / (freq_thz * THZ) * 1e9


def photon_energy_ev(freq_thz: float) -> float:
    """Photon energy E = h f, in electronvolts."""
    if freq_thz <= 0:
        raise ValueError("frequency must be positive")
    return PLANCK * freq_thz * THZ / ELEMENTARY_CHARGE


def wavenumber_cm(freq_thz: float) -> float:
    """Spectroscopic wavenumber f / c, in reciprocal centimetres."""
    if freq_thz <= 0:
        raise ValueError("frequency must be positive")
    return freq_thz * THZ / SPEED_OF_LIGHT / 100


def conversions(center_thz: float, half_width_thz: float) -> dict:
    """Equation-based conversions for a reported band (not measurements)."""
    if half_width_thz < 0 or half_width_thz >= center_thz:
        raise ValueError("half-width must be non-negative and below the centre")
    lo, hi = center_thz - half_width_thz, center_thz + half_width_thz
    out = {"band_thz": [lo, center_thz, hi]}
    for name, fn in (("wavelength_nm", wavelength_nm), ("photon_energy_ev", photon_energy_ev),
                     ("wavenumber_cm-1", wavenumber_cm)):
        vals = [fn(lo), fn(center_thz), fn(hi)]
        out[name] = {"at_center": vals[1], "range": [min(vals[0], vals[2]), max(vals[0], vals[2])]}
    out["note"] = ("Equation-based SI conversions for scale only; not measurements, "
                   "and not evidence of visible-light emission or a biological optical mode.")
    return out


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def load_ledger(path: pathlib.Path = DEFAULT_LEDGER) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate(data: dict) -> list[str]:
    """Return a list of problems; an empty list means the ledger is valid."""
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for key in ("title", "version", "snapshot_date", "non_affiliation"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"missing or empty top-level field: {key}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("snapshot_date", ""))):
        errors.append("snapshot_date must be YYYY-MM-DD")

    sources = data.get("sources") or []
    source_ids = set()
    for src in sources:
        sid = src.get("id")
        if not sid or sid in source_ids:
            errors.append(f"source id missing or duplicated: {sid!r}")
        source_ids.add(sid)
        if not str(src.get("url", "")).startswith("https://"):
            errors.append(f"source {sid}: url must be https")
        if not src.get("title"):
            errors.append(f"source {sid}: title required")

    claims = data.get("claims") or []
    if not claims:
        errors.append("ledger has no claims")
    seen = set()
    used_sources = set()
    for c in claims:
        cid = c.get("id", "")
        if not CLAIM_ID.match(cid):
            errors.append(f"claim id {cid!r} must look like ABC-01")
        if cid in seen:
            errors.append(f"duplicate claim id {cid}")
        seen.add(cid)
        label = c.get("label")
        if label not in LABELS:
            errors.append(f"{cid}: unknown evidence label {label!r}")
        for field in ("topic", "claim", "assessment"):
            if not isinstance(c.get(field), str) or not c[field].strip():
                errors.append(f"{cid}: {field} required")
        refs = c.get("sources") or []
        if not refs:
            errors.append(f"{cid}: at least one source is required")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{cid}: unknown source {ref!r}")
            used_sources.add(ref)
        text = c.get("claim", "")
        if FENCED_TOPICS.search(text) and label not in FENCED_LABELS:
            errors.append(f"{cid}: fenced claim type must be labelled hypothesis or unsupported_inference")
        if label in FENCED_LABELS and not FENCE_WORDS.search(c.get("assessment", "")):
            errors.append(f"{cid}: assessment must state what is not established")
    for sid in source_ids - used_sources:
        errors.append(f"source {sid} is never cited")

    band = data.get("frequency_band") or {}
    try:
        conversions(float(band["center_thz"]), float(band["half_width_thz"]))
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"frequency_band invalid: {exc}")
    if band.get("source") not in source_ids:
        errors.append("frequency_band.source must reference a source")
    rat = data.get("rat_study") or {}
    if rat.get("measured_613_thz") is not False:
        errors.append("rat_study.measured_613_thz must be false (the study did not measure it)")
    if rat.get("source") not in source_ids:
        errors.append("rat_study.source must reference a source")
    return errors


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def esc(text: str) -> str:
    return html.escape(text, quote=True)


SVG_CLASSES = [
    ("ANNOUNCEMENT / PLAN", "What an organization says", "Status and expected dates", "#dcecff", "#245a9b"),
    ("COMPUTATIONAL MODEL", "What a model predicts", "Not a biological measurement", "#e5e5ff", "#51459a"),
    ("ANIMAL BEHAVIOR", "What rats did in a test", "Not a 613 THz readout", "#dff4ef", "#176b5c"),
    ("HYPOTHESIS", "A proposed explanation", "Not a settled mechanism", "#fff0d7", "#946315"),
    ("UNSUPPORTED INFERENCE", "Claim exceeds its source", "Do not promote to fact", "#fde3e5", "#a53845"),
]


def render_svg() -> str:
    font = 'font-family="system-ui, sans-serif"'
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 300" role="img" aria-labelledby="ev-title ev-desc">',
        '<title id="ev-title">Evidence classes in the Quantum Claims Evidence Passport</title>',
        '<desc id="ev-desc">Five separate evidence classes are shown side by side. They are not a shared score or a single ranking.</desc>',
        '<rect width="1240" height="300" rx="24" fill="#f5f7fb"/>',
        f'<text x="32" y="39" fill="#12233f" {font} font-size="20" font-weight="700">Evidence classes are different kinds of records, not one score</text>',
    ]
    for i, (head, line1, line2, fill, stroke) in enumerate(SVG_CLASSES):
        x = 24 + i * 244
        parts.append(
            f'<g transform="translate({x},64)">'
            f'<rect width="224" height="204" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            f'<rect width="8" height="204" rx="4" fill="{stroke}"/>'
            f'<text x="22" y="38" fill="{stroke}" {font} font-size="13" font-weight="800">{esc(head)}</text>'
            f'<text x="22" y="83" fill="#12233f" {font} font-size="15" font-weight="650">{esc(line1)}</text>'
            f'<text x="22" y="116" fill="#35435a" {font} font-size="13">{esc(line2)}</text>'
            '</g>'
        )
    parts.append('</svg>')
    return "".join(parts)


def _fmt_range(lo: float, hi: float, spec: str) -> str:
    return f"{format(lo, spec)}–{format(hi, spec)}"


def render_conversion_rows(band: dict) -> str:
    conv = conversions(float(band["center_thz"]), float(band["half_width_thz"]))
    wl, ev, wn = conv["wavelength_nm"], conv["photon_energy_ev"], conv["wavenumber_cm-1"]
    rows = [
        ("Vacuum wavelength", f"{wl['at_center']:.1f} nm", _fmt_range(*wl["range"], ".1f") + " nm"),
        ("Photon energy", f"{ev['at_center']:.3f} eV", _fmt_range(*ev["range"], ".3f") + " eV"),
        ("Wavenumber", f"{wn['at_center']:,.0f} cm<sup>−1</sup>",
         _fmt_range(*wn["range"], ",.0f") + " cm<sup>−1</sup>"),
    ]
    return "\n".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)


def render_claims(data: dict) -> str:
    by_id = {s["id"]: s for s in data["sources"]}
    cards = []
    for c in data["claims"]:
        text, colour = LABELS[c["label"]]
        links = " ".join(
            f'<a href="{esc(by_id[r]["url"])}" rel="noreferrer">{esc(by_id[r]["title"])}</a>'
            for r in c["sources"]
        )
        cards.append(
            '<article class="claim-card"><div class="claim-meta">'
            f'<span class="claim-id">{esc(c["id"])}</span>'
            f'<span class="badge {colour}">{esc(text)}</span>'
            f'<span class="topic">{esc(c["topic"])}</span></div>'
            f'<h3>{esc(c["claim"])}</h3><p>{esc(c["assessment"])}</p>'
            f'<div class="sources"><strong>Source:</strong> {links}</div></article>'
        )
    return '<div class="claims">' + "".join(cards) + "</div>"


CSS = """:root { --ink:#14233d; --muted:#526176; --paper:#f4f6fa; --card:#fff; --line:#dce3ed; --blue:#245a9b; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink); font:16px/1.58 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { width:min(1040px,100% - 32px); margin:32px auto 64px; }
header { background:#112541; color:#fff; border-radius:22px; padding:32px clamp(22px,5vw,52px); }
.eyebrow { color:#bcd5fb; font-size:.78rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
h1 { margin:.45rem 0 .5rem; font-size:clamp(2rem,5vw,3.1rem); line-height:1.08; letter-spacing:-.035em; }
header p { max-width:760px; color:#e2eaf6; margin:.7rem 0 0; }
.snapshot { display:inline-block; margin-top:1rem; color:#d1def0; font-size:.9rem; }
section { margin-top:28px; }
h2 { font-size:1.4rem; letter-spacing:-.015em; margin:0 0 8px; }
.lede { color:var(--muted); margin:.25rem 0 16px; max-width:850px; }
.facts { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
.fact { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:18px; }
.fact strong { display:block; margin-bottom:6px; color:#1e477a; }
.fact p { margin:0; color:#33435a; font-size:.94rem; }
.visual-wrap { overflow-x:auto; background:#fff; border:1px solid var(--line); border-radius:18px; padding:10px; }
.visual-wrap svg { display:block; min-width:850px; width:100%; height:auto; }
.conversion { border-collapse:collapse; width:100%; background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden; }
.conversion th,.conversion td { border-bottom:1px solid var(--line); padding:12px 14px; text-align:left; vertical-align:top; }
.conversion th { background:#edf2f8; color:#293d5a; font-size:.88rem; }
.conversion tr:last-child td { border-bottom:0; }
.note { font-size:.91rem; color:var(--muted); margin:12px 0 0; }
.claims { display:grid; gap:12px; }
.claim-card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:18px 20px; }
.claim-meta { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; }
.claim-id { font:700 .79rem ui-monospace,SFMono-Regular,Consolas,monospace; color:#526176; }
.badge { border-radius:999px; padding:3px 9px; font-size:.77rem; font-weight:750; }
.badge.blue { background:#dcecff;color:#245a9b; } .badge.violet { background:#e5e5ff;color:#51459a; }
.badge.green { background:#dff4ef;color:#176b5c; } .badge.amber { background:#fff0d7;color:#80540e; }
.badge.red { background:#fde3e5;color:#a53845; }
.topic { color:var(--muted); font-size:.84rem; }
.claim-card h3 { font-size:1.03rem; line-height:1.43; margin:0 0 7px; }
.claim-card p { color:#3d4b61; margin:.35rem 0; }
.sources { margin-top:10px; color:#47566d; font-size:.85rem; }
a { color:#175b9e; text-underline-offset:2px; }
.sources a { margin-right:10px; }
.limits { background:#fff; border:1px solid var(--line); border-left:5px solid #7386a0; border-radius:12px; padding:16px 18px; color:#394960; }
footer { border-top:1px solid var(--line); margin-top:30px; padding-top:16px; color:#5a687b; font-size:.84rem; }
@media(max-width:700px) { main { width:min(100% - 20px,1040px); margin-top:12px; } header { border-radius:16px; padding:24px 20px; } .facts { grid-template-columns:1fr; } .conversion th,.conversion td { padding:10px 8px; font-size:.88rem; } .claim-card { padding:15px; } }
@media print { body { background:#fff; } main { width:100%; margin:0; } header { print-color-adjust:exact; } .visual-wrap { overflow:visible; } .visual-wrap svg { min-width:0; } }
"""


def render_report(data: dict) -> str:
    band = data["frequency_band"]
    lo = band["center_thz"] - band["half_width_thz"]
    hi = band["center_thz"] + band["half_width_thz"]
    snap = esc(data["snapshot_date"])
    version = esc(data["version"])
    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="color-scheme" content="light">',
        f"<title>{esc(data['title'])}</title>",
        "<style>",
        CSS + "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        f'<div class="eyebrow">Evidence passport · version {version}</div>',
        "<h1>Quantum Claims<br>Evidence Passport</h1>",
        "<p>A compact, source-linked check of two different stories: a planned Swiss quantum-computing hub and a modeled anesthetic/microtubule frequency. Evidence types stay separate; this page does not turn them into a single score.</p>",
        f'<span class="snapshot">Audit snapshot: <time datetime="{snap}">{snap}</time></span>',
        "</header>",
        '<section aria-labelledby="readout-title">',
        '<h2 id="readout-title">The short read</h2>',
        '<div class="facts">',
        '<div class="fact"><strong>System Two: planned</strong><p>The IBM/ETH announcements set an expected end-of-2026 deployment/operation date. They are not proof of current operation or an individual access entitlement.</p></div>',
        '<div class="fact"><strong>613 THz: modeled band</strong><p>The 2017 source is computational/theoretical: it models dipole modes in a tubulin model. Its reported band is not a direct measurement of a brain or tubulin oscillation.</p></div>',
        '<div class="fact"><strong>Rat study: behavior</strong><p>Within-subject N=8 male Long–Evans rats; 4% isoflurane; mean LORR delay about +69 s (p=0.0016). LORR was a behavioral proxy for unconsciousness. The study did not measure 613 THz or establish a quantum-consciousness mechanism.</p></div>',
        "</div>",
        "</section>",
        '<section aria-labelledby="visual-title">',
        '<h2 id="visual-title">Evidence ladder — classification, not ranking</h2>',
        '<p class="lede">A press announcement, a computation, an animal behavior result, and a hypothesis answer different questions. No combined evidence score is calculated.</p>',
        f'<div class="visual-wrap">{render_svg()}</div>',
        "</section>",
        '<section aria-labelledby="conversion-title">',
        f'<h2 id="conversion-title">What does {band["center_thz"]} THz convert to?</h2>',
        f'<p class="lede">For scale only: the 2017 computational/theoretical source reports a modeled frequency band centered near {band["center_thz"]} THz, using the notation {esc(band["notation"])}. The ±{band["half_width_thz"]} describes the reported band, not a statistical uncertainty estimate or confidence interval.</p>',
        '<table class="conversion">',
        f'<thead><tr><th>Quantity</th><th>At {band["center_thz"]} THz</th><th>Converted values across reported band ({lo}–{hi} THz)</th></tr></thead>',
        "<tbody>",
        render_conversion_rows(band),
        "</tbody></table>",
        '<p class="note">These are equation-based SI conversions from frequency, not new experimental findings. A wavelength near the visible range does not show that tubulin emits visible light or hosts a biologically active optical mode. Constants: <a href="https://physics.nist.gov/cuu/Constants/" rel="noreferrer">NIST fundamental physical constants</a>.</p>',
        "</section>",
        '<section aria-labelledby="ledger-title">',
        '<h2 id="ledger-title">Claim ledger</h2>',
        '<p class="lede">Each entry names what the cited source can support—and where the inference stops.</p>',
        render_claims(data),
        "</section>",
        '<section aria-labelledby="limits-title">',
        '<h2 id="limits-title">Use and limits</h2>',
        "<div class=\"limits\">This is a reproducible source audit, not scientific, clinical, or investment advice. It does not establish a causal mechanism, a human result, current quantum-computer availability, or the reader's eligibility for access. The microtubule/quantum-consciousness account remains a hypothesis; a review's advocacy is not proof of the specific 613 THz proposal.</div>",
        "</section>",
        "<footer>Generated locally from the included claim ledger. The HTML is self-contained and has no runtime network calls; source links require a connection when opened.</footer>",
        "</main>",
        "</body>",
        "</html>",
        "",
    ])


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _load_valid(path: pathlib.Path) -> dict:
    data = load_ledger(path)
    problems = validate(data)
    if problems:
        raise LedgerError("\n".join(problems))
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="passport.py", description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", type=pathlib.Path, default=DEFAULT_LEDGER, help="claim ledger JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check claim/source/label consistency")
    b = sub.add_parser("build", help="write the static HTML report and SVG")
    b.add_argument("--output", type=pathlib.Path, default=DEFAULT_REPORT)
    b.add_argument("--svg", type=pathlib.Path, default=DEFAULT_SVG)
    sub.add_parser("conversions", help="print the SI conversions as JSON")
    args = parser.parse_args(argv)

    try:
        data = _load_valid(args.ledger)
    except (OSError, json.JSONDecodeError, LedgerError) as exc:
        print(f"invalid ledger: {exc}", file=sys.stderr)
        return 1

    if args.command == "validate":
        counts: dict[str, int] = {}
        for c in data["claims"]:
            counts[c["label"]] = counts.get(c["label"], 0) + 1
        print(f"OK: {len(data['claims'])} claims, {len(data['sources'])} sources; labels: "
              + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    elif args.command == "build":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_report(data), encoding="utf-8")
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(render_svg() + "\n", encoding="utf-8")
        print(f"wrote {args.output} and {args.svg}")
    elif args.command == "conversions":
        band = data["frequency_band"]
        print(json.dumps(conversions(float(band["center_thz"]), float(band["half_width_thz"])), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
