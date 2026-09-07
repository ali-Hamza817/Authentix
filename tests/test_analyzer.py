"""Behavioural tests for the Authentix analyzer.

Runs with pytest, or standalone:  python tests/test_analyzer.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from authentix.analyzer import analyze_bytes  # noqa: E402
from tests.make_samples import (  # noqa: E402
    build_docx,
    build_pdf,
    build_pypdf_rewrite,
    build_signed_then_modified,
)


def _codes(rep):
    return {f["code"] for f in rep["findings"]}


# --------------------------------------------------------------------------- #
def test_clean_pdf_is_credible():
    rep = analyze_bytes(build_pdf(creation="D:20240104120000Z", mod="D:20240104120000Z"), "clean.pdf")
    assert rep["summary"]["band"] in ("Credible", "Guarded")
    assert rep["summary"]["credibility_score"] >= 70
    assert rep["summary"]["tampering_detected"] is False
    assert rep["consistency_graph"]["contradiction_count"] == 0


def test_backdated_pdf_is_flagged():
    data = build_pdf(
        creation="D:20190104120000Z", mod="D:20260904120000Z",
        creator="Microsoft Word", producer="Adobe PDF Library 15.0",
        id0="31" * 16, id1="99" * 16,
    )
    rep = analyze_bytes(data, "tampered_dates.pdf")
    codes = _codes(rep)
    assert "timestamp_gap_no_edits" in codes
    assert "trailer_id_changed_single_revision" in codes
    assert "producer_creator_mismatch" in codes
    assert rep["summary"]["band"] in ("Suspicious", "Untrusted")
    assert rep["summary"]["credibility_score"] < 60
    assert rep["consistency_graph"]["contradiction_count"] >= 2


def test_future_dated_pdf():
    rep = analyze_bytes(build_pdf(creation="D:20990101000000Z", mod="D:20990101000000Z"), "future.pdf")
    assert "future_creation_date" in _codes(rep)
    assert rep["summary"]["band"] in ("Suspicious", "Untrusted", "Guarded")


def test_incremental_update_detected():
    data = build_pdf(
        creation="D:20240104120000Z", mod="D:20240104120000Z",
        second_revision_moddate="D:20260101120000Z",
    )
    rep = analyze_bytes(data, "incremental.pdf")
    assert rep["summary"]["revisions"] >= 2
    labels = " ".join(e["label"] for e in rep["timeline"])
    assert "Incremental update" in labels


def test_active_content_detected():
    data = build_pdf(
        creation="D:20240104120000Z",
        extra_catalog=b" /OpenAction << /S /JavaScript /JS (app.alert\\(1\\)) >>",
    )
    rep = analyze_bytes(data, "active.pdf")
    assert "active_content" in _codes(rep)
    assert rep["ewdca"]["components"]["A_anomaly"] > 0.2


def test_modified_after_signing():
    rep = analyze_bytes(build_signed_then_modified(), "signed_then_modified.pdf")
    codes = _codes(rep)
    assert "modified_after_signing" in codes
    assert rep["summary"]["signed"] is True
    assert any(
        e["status"] == "contradiction" and e["id"].startswith("sig_coverage")
        for e in rep["consistency_graph"]["edges"]
    )
    assert rep["summary"]["band"] in ("Suspicious", "Untrusted")


def test_pypdf_rewrite_stripped_is_flagged():
    rep = analyze_bytes(build_pypdf_rewrite(keep_metadata=False), "rewrite.pdf")
    codes = _codes(rep)
    assert "programmatic_rewrite" in codes
    assert rep["summary"]["origin_known"] is False
    assert rep["origin"]["tool_kind"] == "manipulator"
    assert rep["summary"]["band"] in ("Guarded", "Suspicious")
    assert rep["summary"]["credibility_score"] < 80
    assert rep["origin"]["toolchain_inference"]  # never empty
    assert "origin cannot be established" in rep["summary"]["verdict"]


def test_pypdf_rewrite_with_metadata_stays_credible():
    rep = analyze_bytes(build_pypdf_rewrite(keep_metadata=True), "rewrite2.pdf")
    assert "programmatic_rewrite" in _codes(rep)
    assert rep["summary"]["origin_known"] is True
    assert rep["summary"]["band"] in ("Credible", "Guarded")


def test_clean_docx_is_credible():
    rep = analyze_bytes(build_docx(), "clean.docx")
    assert rep["evidence"]["engine"] == "ooxml"
    assert rep["summary"]["band"] in ("Credible", "Guarded")
    assert rep["summary"]["created"]["by"] == "Jane Doe"


def test_docx_modified_before_created():
    rep = analyze_bytes(
        build_docx(created="2024-05-10T10:00:00Z", modified="2024-05-09T18:00:00Z"),
        "bad.docx",
    )
    assert "modified_before_created" in _codes(rep)
    assert rep["summary"]["band"] in ("Suspicious", "Untrusted")


def test_docx_metadata_edited_later():
    rep = analyze_bytes(
        build_docx(
            created="2024-03-01T09:00:00Z", modified="2024-03-01T09:05:00Z",
            revision="1", total_time="1",
            body_time=(2024, 3, 1, 9, 0, 0), core_time=(2024, 3, 1, 15, 30, 0),
        ),
        "meta_later.docx",
    )
    assert "metadata_edited_separately" in _codes(rep)


def test_docx_macro_flagged():
    rep = analyze_bytes(build_docx(with_macro=True), "macro.docx")
    assert "contains_macros" in _codes(rep)


def test_unsupported_format_does_not_crash():
    rep = analyze_bytes(b"just some plain text, not a document", "note.txt")
    assert rep["summary"]["band"] in ("Guarded", "Suspicious", "Credible", "Untrusted", "Unknown")
    assert "unsupported_format" in _codes(rep)


def test_report_shape():
    rep = analyze_bytes(build_pdf(), "shape.pdf")
    for key in ("product", "file", "summary", "origin", "timeline", "findings",
                "signatures", "consistency_graph", "ewdca", "evidence"):
        assert key in rep, f"missing top-level key: {key}"
    assert rep["product"] == "Authentix"
    import json
    json.dumps(rep)  # must be JSON-serialisable


# --------------------------------------------------------------------------- #
def _run_standalone():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n  {len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
