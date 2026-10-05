# SPDX-License-Identifier: AGPL-3.0-only
"""Standard-library tests for the Quantum Claims Evidence Passport."""
from __future__ import annotations

import copy
import io
import json
import pathlib
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import passport  # noqa: E402


def ledger() -> dict:
    return passport.load_ledger(ROOT / "claims.json")


class TestConversions(unittest.TestCase):
    def test_constants_are_exact_si_values(self):
        self.assertEqual(passport.SPEED_OF_LIGHT, 299792458)
        self.assertEqual(passport.PLANCK, 6.62607015e-34)
        self.assertEqual(passport.ELEMENTARY_CHARGE, 1.602176634e-19)

    def test_wavelength_at_613_thz(self):
        self.assertAlmostEqual(passport.wavelength_nm(613), 489.0579, places=3)
        self.assertEqual(f"{passport.wavelength_nm(613):.1f}", "489.1")

    def test_photon_energy_at_613_thz(self):
        self.assertEqual(f"{passport.photon_energy_ev(613):.3f}", "2.535")

    def test_wavenumber_at_613_thz(self):
        self.assertEqual(f"{passport.wavenumber_cm(613):,.0f}", "20,447")

    def test_equations_are_mutually_consistent(self):
        # E[eV] * lambda[nm] = h c / e * 1e9  (~1239.84 eV nm)
        hc_over_e = passport.PLANCK * passport.SPEED_OF_LIGHT / passport.ELEMENTARY_CHARGE * 1e9
        for f in (605, 613, 621):
            self.assertAlmostEqual(passport.photon_energy_ev(f) * passport.wavelength_nm(f), hc_over_e, places=9)
            # wavenumber [cm^-1] = 1e7 / lambda [nm]
            self.assertAlmostEqual(passport.wavenumber_cm(f), 1e7 / passport.wavelength_nm(f), places=6)

    def test_band_endpoints_and_ordering(self):
        conv = passport.conversions(613, 8)
        self.assertEqual(conv["band_thz"], [605, 613, 621])
        for key in ("wavelength_nm", "photon_energy_ev", "wavenumber_cm-1"):
            lo, hi = conv[key]["range"]
            self.assertLess(lo, conv[key]["at_center"])
            self.assertLess(conv[key]["at_center"], hi)
        # wavelength decreases with frequency, so the 621 THz end is the short one
        self.assertEqual(f"{conv['wavelength_nm']['range'][0]:.1f}", "482.8")
        self.assertEqual(f"{conv['wavelength_nm']['range'][1]:.1f}", "495.5")
        self.assertEqual(f"{conv['photon_energy_ev']['range'][0]:.3f}", "2.502")
        self.assertEqual(f"{conv['photon_energy_ev']['range'][1]:.3f}", "2.568")
        self.assertEqual(f"{conv['wavenumber_cm-1']['range'][0]:,.0f}", "20,181")
        self.assertEqual(f"{conv['wavenumber_cm-1']['range'][1]:,.0f}", "20,714")

    def test_invalid_inputs_rejected(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                passport.wavelength_nm(bad)
        with self.assertRaises(ValueError):
            passport.conversions(613, 700)
        with self.assertRaises(ValueError):
            passport.conversions(613, -1)


class TestLedger(unittest.TestCase):
    def test_bundled_ledger_is_valid(self):
        self.assertEqual(passport.validate(ledger()), [])

    def test_expected_labels(self):
        labels = {c["id"]: c["label"] for c in ledger()["claims"]}
        self.assertEqual(labels, {
            "HUB-01": "announcement_planned",
            "HUB-02": "unsupported_inference",
            "HUB-03": "unsupported_inference",
            "THZ-01": "computational_model",
            "THZ-02": "unsupported_inference",
            "THZ-03": "unsupported_inference",
            "RAT-01": "animal_behavioral",
            "RAT-02": "unsupported_inference",
            "HYP-01": "hypothesis",
        })

    def test_every_label_class_is_used_and_not_a_score(self):
        used = {c["label"] for c in ledger()["claims"]}
        self.assertEqual(used, set(passport.LABELS))
        for c in ledger()["claims"]:
            self.assertNotIn("score", c)

    def test_consciousness_claims_are_fenced(self):
        for c in ledger()["claims"]:
            if re.search(r"conscious", c["claim"], re.I):
                self.assertIn(c["label"], {"hypothesis", "unsupported_inference"}, c["id"])

    def test_every_claim_cites_a_known_https_source(self):
        data = ledger()
        urls = {s["id"]: s["url"] for s in data["sources"]}
        for c in data["claims"]:
            self.assertTrue(c["sources"])
            for ref in c["sources"]:
                self.assertTrue(urls[ref].startswith("https://"))

    def test_reported_study_details(self):
        data = ledger()
        rat = data["rat_study"]
        self.assertEqual((rat["n"], rat["isoflurane_percent"], rat["mean_delay_s"], rat["p_value"]), (8, 4, 69, 0.0016))
        self.assertIs(rat["measured_613_thz"], False)
        self.assertEqual(rat["design"], "within-subject")
        band = data["frequency_band"]
        self.assertEqual((band["center_thz"], band["half_width_thz"]), (613, 8))
        self.assertIn("not a statistical", band["meaning"])
        rat01 = next(c for c in data["claims"] if c["id"] == "RAT-01")
        for needle in ("N=8", "+69 s", "p=0.0016", "4% isoflurane"):
            self.assertIn(needle, rat01["claim"])
        self.assertIn("did not measure 613 THz", rat01["assessment"])
        self.assertIn("not clinical advice", rat01["assessment"])

    def test_hub_claim_is_planned_not_operational(self):
        data = ledger()
        hub = next(c for c in data["claims"] if c["id"] == "HUB-01")
        self.assertIn("expected by the end of 2026", hub["claim"])
        self.assertIn("not confirmation", hub["assessment"])
        self.assertIn("does not imply affiliation", data["non_affiliation"])


class TestValidationFailsClosed(unittest.TestCase):
    def mutate(self, fn) -> list[str]:
        data = copy.deepcopy(ledger())
        fn(data)
        return passport.validate(data)

    def test_unknown_label(self):
        self.assertTrue(self.mutate(lambda d: d["claims"][0].__setitem__("label", "proven")))

    def test_unknown_source(self):
        self.assertTrue(self.mutate(lambda d: d["claims"][0].__setitem__("sources", ["nope"])))

    def test_missing_source(self):
        self.assertTrue(self.mutate(lambda d: d["claims"][0].__setitem__("sources", [])))

    def test_duplicate_id(self):
        self.assertTrue(self.mutate(lambda d: d["claims"][1].__setitem__("id", d["claims"][0]["id"])))

    def test_promoting_a_fenced_claim_fails(self):
        def promote(d):
            hyp = next(c for c in d["claims"] if c["id"] == "HYP-01")
            hyp["label"] = "animal_behavioral"
        self.assertTrue(self.mutate(promote))

    def test_rat_study_cannot_claim_613_measurement(self):
        self.assertTrue(self.mutate(lambda d: d["rat_study"].__setitem__("measured_613_thz", True)))

    def test_http_url_rejected(self):
        self.assertTrue(self.mutate(lambda d: d["sources"][0].__setitem__("url", "http://example.com")))

    def test_cli_rejects_invalid_ledger(self):
        data = copy.deepcopy(ledger())
        data["claims"][0]["label"] = "proven"
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "bad.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(passport.main(["--ledger", str(p), "validate"]), 1)


class TestStaticOutput(unittest.TestCase):
    def build(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "r.html"
            svg = pathlib.Path(tmp) / "e.svg"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(passport.main(["build", "--output", str(out), "--svg", str(svg)]), 0)
            self.svg_text = svg.read_text(encoding="utf-8")
            return out.read_text(encoding="utf-8")

    def test_committed_report_matches_build(self):
        self.assertEqual(self.build(), (ROOT / "docs" / "report.html").read_text(encoding="utf-8"))

    def test_committed_svg_matches_build(self):
        self.build()
        self.assertEqual(self.svg_text, (ROOT / "assets" / "evidence-ladder.svg").read_text(encoding="utf-8"))

    def test_report_is_self_contained(self):
        html = self.build()
        self.assertNotIn("<script", html)
        self.assertNotRegex(html, r'<(?:img|link|iframe)\b')
        self.assertNotRegex(html, r'src\s*=')
        self.assertNotIn("@import", html)
        self.assertNotRegex(html, r'url\(')

    def test_report_contains_every_claim_and_limits(self):
        html = self.build()
        for c in ledger()["claims"]:
            self.assertIn(f'<span class="claim-id">{c["id"]}</span>', html)
        for needle in ("489.1 nm", "2.535 eV", "20,447 cm", "605–621 THz", "not a statistical uncertainty",
                       "not scientific, clinical, or investment advice", "No combined evidence score"):
            self.assertIn(needle, html)

    def test_ledger_text_is_html_escaped(self):
        data = copy.deepcopy(ledger())
        data["claims"][0]["claim"] = '<script>alert("x")</script>'
        html = passport.render_report(data)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_conversions_command_is_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(passport.main(["conversions"]), 0)
        self.assertEqual(json.loads(buf.getvalue())["band_thz"], [605, 613, 621])


if __name__ == "__main__":
    unittest.main()
