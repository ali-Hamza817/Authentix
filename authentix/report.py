"""Assemble the final Authentix report from the pipeline stages."""
from __future__ import annotations

from datetime import datetime, timezone

from . import __version__

VERDICTS = {
    "Credible": (
        "The document's metadata, structure and history are mutually consistent. "
        "No evidence of tampering was found."
    ),
    "Guarded": (
        "The document is broadly consistent, but some evidence does not line up. "
        "Review the findings before relying on it."
    ),
    "Suspicious": (
        "Several independent pieces of evidence contradict the document's claimed history. "
        "Treat it as unverified until the discrepancies are explained."
    ),
    "Untrusted": (
        "The document's stated origin and history are contradicted by its own forensic evidence. "
        "Do not rely on it without independent confirmation."
    ),
    "Unknown": (
        "This file is not a PDF or Office Open XML document, so Authentix could not assess its authenticity."
    ),
}


def _verdict(band: str, findings: list, origin_known: bool = True) -> str:
    highs = [f for f in findings if f["severity"] >= 3]

    if band in ("Credible", "Guarded") and not origin_known:
        return (
            "The file itself is internally consistent, but its origin cannot be established — the author and "
            "dates are missing or belong only to a later automated re-save. Authenticity of the original "
            "document is unverifiable from this copy."
        )
    if band == "Credible" and not findings:
        return "Metadata, structure and history are mutually consistent. No evidence of tampering was found."
    if band == "Credible":
        n = len(highs) or len(findings)
        return (f"The document's history is internally consistent, but {n} finding(s) warrant attention — "
                f"see the findings below.")
    return VERDICTS.get(band, VERDICTS["Unknown"])


def build(intake, ev: dict, decg: dict, sc: dict) -> dict:
    d = ev.get("_derived", {})
    findings = sorted(ev.get("findings", []), key=lambda x: -x["severity"])
    material = [f for f in findings if f["severity"] >= 3]
    origin_known = bool(d.get("origin_known", d.get("creation_dt") or d.get("author")))

    sig_status = "not signed"
    sigs = ev.get("signatures", []) or []
    if sigs:
        n = len(sigs)
        if any(f["code"] == "modified_after_signing" for f in findings):
            sig_status = f"{n} signature(s) — content changed after signing"
        elif ev.get("signature_integrity") == 1.0:
            sig_status = f"{n} signature(s) — structurally intact, full coverage"
        else:
            sig_status = f"{n} signature(s) — partial coverage / chain not validated"

    created = {
        "when": d.get("creation_dt"),
        "by": d.get("author") or None,
        "tool": d.get("creator_tool") or d.get("creator") or d.get("producer"),
    }
    last_modified = {
        "when": d.get("mod_dt"),
        "by": d.get("last_modified_by") or d.get("author"),
        "tool": d.get("producer") or d.get("creator_tool"),
    }

    band = sc.get("band", "Unknown")
    return {
        "product": "Authentix",
        "version": __version__,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "file": {
            "name": intake.filename,
            "size_bytes": intake.size,
            "sha256": intake.sha256,
            "md5": intake.md5,
            "format": intake.fmt,
            "format_detail": intake.fmt_detail,
        },
        "summary": {
            "credibility_score": sc.get("credibility_score"),
            "band": band,
            "confidence": sc.get("confidence", "n/a"),
            "confidence_basis": sc.get("confidence_basis"),
            "verdict": _verdict(band, findings, origin_known),
            "title": d.get("title"),
            "created": created,
            "last_modified": last_modified,
            "revisions": ev.get("structure", {}).get("revisions", 1),
            "signed": bool(sigs),
            "signature_status": sig_status,
            "tampering_detected": bool(material),
            "tampering_count": len(material),
            "findings_total": len(findings),
            "origin_known": origin_known,
            "attribution_signals": (ev.get("attribution", {}).get("summary", {}) or {}).get("signals", 0),
        },
        "origin": {
            "author": d.get("author"),
            "last_modified_by": d.get("last_modified_by"),
            "creator_application": d.get("creator"),
            "producer": d.get("producer"),
            "creator_tool_xmp": d.get("creator_tool"),
            "creation_date": d.get("creation_dt"),
            "modification_date": d.get("mod_dt"),
            "tool_kind": d.get("tool_kind"),
            "library": d.get("library"),
            "toolchain_inference": _toolchain_story(ev, d),
        },
        "timeline": ev.get("timeline", []),
        "findings": findings,          # ranked by impact x reliability; each carries stance + reasoning
        "evidence_matrix": ev.get("evidence_matrix", []),
        "attribution": ev.get("attribution", {
            "summary": {"people": [], "verified_people": [], "has_device_traces": False, "signals": 0},
            "identities": [], "device": {}, "network": {}, "geolocation": {}, "notes": [],
        }),
        "signatures": sigs,
        "consistency_graph": decg,
        "ewdca": sc,
        "evidence": {
            "engine": ev.get("engine"),
            "metadata": ev.get("metadata"),
            "xmp": ev.get("xmp"),
            "core_properties": ev.get("core"),
            "app_properties": ev.get("app"),
            "structure": ev.get("structure"),
            "trailer_id": ev.get("trailer_id"),
            "provenance_confidence": ev.get("provenance_confidence"),
            "signature_integrity": ev.get("signature_integrity"),
        },
        "errors": ev.get("errors", []),
    }


def _toolchain_story(ev: dict, d: dict) -> str:
    st = ev.get("structure", {})
    if ev.get("engine") == "pdf":
        seen = st.get("producers_seen") or []
        prod = d.get("producer")
        kind = d.get("tool_kind")
        parts = []
        if d.get("creator") and kind != "generator":
            parts.append(f"authored in {d['creator']}")
        if prod and kind == "manipulator":
            parts.append(f"last written by {prod} — a PDF manipulation library, i.e. an automated re-save step")
        elif prod and kind == "generator":
            parts.append(f"generated by {prod} (a from-scratch / HTML-to-PDF tool, not a human-authoring app)")
        elif prod:
            parts.append(f"rendered to PDF by {prod}")
        extra = [p for p in seen if p and p != prod]
        if extra:
            parts.append("earlier producer(s): " + ", ".join(extra))
        if st.get("incremental_updates"):
            parts.append(f"{st['incremental_updates']} incremental update(s) appended after the first save")
        if not d.get("creator") and not d.get("author") and not d.get("creation_dt"):
            parts.append("original authoring application, author and creation date were not carried through")
        return "; ".join(parts) or "no toolchain metadata is present in this file"
    parts = []
    if ev.get("app", {}).get("application"):
        parts.append(f"produced by {ev['app']['application']}")
    if d.get("creator"):
        parts.append(f"first authored by {d['creator']}")
    if d.get("last_modified_by") and d.get("last_modified_by") != d.get("creator"):
        parts.append(f"last edited by {d['last_modified_by']}")
    return "; ".join(parts) or "no application metadata present"
