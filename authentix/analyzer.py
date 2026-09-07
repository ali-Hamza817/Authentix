"""Top-level orchestrator: bytes/path in, Authentix report out.

Every stage is wrapped so a malformed file degrades to a partial report instead
of raising.
"""
from __future__ import annotations

import os
import traceback

from . import attribution as _attribution
from . import decg as _decg
from . import ewdca as _ewdca
from . import intake as _intake
from . import reliability as _reliability
from . import report as _report
from .evidence import ooxml as _ooxml
from .evidence import pdf as _pdf


def analyze_bytes(data: bytes, filename: str = "document") -> dict:
    ik = _intake.build_intake(data, filename)
    errors: list = []

    if ik.fmt == "pdf":
        ev = _run(lambda: _pdf.analyze(data), "pdf", errors)
    elif ik.fmt in ("docx", "xlsx", "pptx", "ooxml"):
        ev = _run(lambda: _ooxml.analyze(data, ik.fmt), "ooxml", errors)
    elif ik.fmt == "ole":
        ev = _empty("ole")
        ev["findings"].append(_note(
            "legacy_format", 2, "provenance", "Legacy binary Office format",
            "This is a pre-2007 OLE2 document (.doc / .xls / .ppt). Authentix performs only limited analysis on "
            "this format — ask the sender for a PDF or a modern Office file (.docx / .xlsx / .pptx).",
        ))
    else:
        ev = _empty(ik.fmt)
        ev["findings"].append(_note(
            "unsupported_format", 1, "provenance", "Unsupported or unrecognised format",
            f"Authentix could not identify this file as PDF or Office Open XML ({ik.fmt_detail}).",
        ))

    ev.setdefault("errors", []).extend(errors)

    try:
        attr = _attribution.extract(data, ev, ik.fmt)
        ev["attribution"] = attr["block"]
        ev.setdefault("findings", []).extend(attr["findings"])
    except Exception as e:  # pragma: no cover - defensive
        ev["attribution"] = {
            "summary": {"people": [], "verified_people": [], "has_device_traces": False, "signals": 0},
            "identities": [], "device": {}, "network": {}, "geolocation": {}, "notes": [],
        }
        ev["errors"].append(_err("attribution", e))

    # ---- Evidence Reliability Assessment: stamp stance / reliability / confidence
    for _f in ev.get("findings", []):
        _reliability.enrich_finding(_f)
    ev["findings"].sort(key=lambda x: (-x.get("confidence_score", 0.0), -x["severity"]))
    try:
        ev["evidence_matrix"] = _reliability.build_matrix(ev)
    except Exception as e:  # pragma: no cover - defensive
        ev["evidence_matrix"] = []
        ev["errors"].append(_err("evidence-matrix", e))

    try:
        graph = _decg.build(ev)
    except Exception as e:  # pragma: no cover
        graph = _empty_graph()
        ev["errors"].append(_err("decg", e))

    try:
        sc = _ewdca.score(ev, graph)
    except Exception as e:  # pragma: no cover
        sc = {
            "credibility_score": None, "band": "Unknown", "risk": None,
            "components": {}, "weights": _ewdca.WEIGHTS,
            "signed": bool(ev.get("signatures")), "primary_drivers": [], "risk_factors": [],
        }
        ev["errors"].append(_err("ewdca", e))

    return _report.build(ik, ev, graph, sc)


def analyze_path(path: str) -> dict:
    with open(path, "rb") as fh:
        data = fh.read()
    return analyze_bytes(data, os.path.basename(path))


# --------------------------------------------------------------------------- #
def _run(fn, engine, errors):
    try:
        return fn()
    except Exception as e:
        errors.append(_err(f"{engine}-analyzer", e))
        return _empty(engine)


def _empty(engine):
    return {"engine": engine, "findings": [], "timeline": [], "structure": {}, "_derived": {}, "errors": []}


def _empty_graph():
    return {
        "nodes": [], "edges": [], "edge_count": 0, "contradiction_count": 0,
        "weak_count": 0, "contradiction_density": 0.0, "mean_kappa": 0.0,
    }


def _note(code, sev, cat, title, detail):
    return {
        "code": code, "severity": sev, "severity_label": {1: "Info", 2: "Low", 3: "Medium", 4: "High"}[sev],
        "category": cat, "title": title, "detail": detail, "evidence": {},
    }


def _err(stage, e):
    return {"stage": stage, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1600:]}
