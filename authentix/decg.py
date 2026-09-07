"""Document Evidence Consistency Graph (DECG).

Turns the extracted evidence into a small graph whose edges are *forensic
expectations* — relationships that should hold if the document's history is
honest. An edge whose observed value diverges from its expected value is a
contradiction; the density of contradictions feeds the EWDCA score.
"""
from __future__ import annotations

from . import reliability as _rel
from . import util

# reliability of each side of an edge, by the kind of evidence it names
_R_DECLARED = _rel.score("declared_metadata")       # ~0.25 — soft timestamps / free text
_R_INTERNAL = _rel.score("internal_revision")        # ~0.80 — revision structure, ZIP part times
_R_STRUCT = _rel.score("structural_binding")         # ~0.88 — /ID, XRef, byte offsets
_R_FINGERPRINT = _rel.score("toolchain_fingerprint")  # ~0.66 — producer inference
_R_CRYPTO = _rel.score("cryptographic")              # ~0.97 — signature / ByteRange


def _edge(eid, a, b, relation, status, kappa, expected, observed, reliability=0.4):
    return {
        "id": eid, "a": a, "b": b, "relation": relation,
        "status": status, "kappa": round(util.clamp(kappa), 3),
        "reliability": round(util.clamp(reliability), 3),
        "expected": expected, "observed": observed,
    }


def _has(findings, code, min_sev=1):
    return any(f["code"] == code and f["severity"] >= min_sev for f in findings)


def build(ev: dict) -> dict:
    edges: list = []
    d = ev.get("_derived", {})
    st = ev.get("structure", {})
    F = ev.get("findings", [])
    c = util.parse_iso_date(d.get("creation_dt"))
    m = util.parse_iso_date(d.get("mod_dt"))

    # --- universal: creation precedes modification --- #
    if c and m:
        bad = _has(F, "modified_before_created")
        edges.append(_edge(
            "time_order", "CreationDate", "ModDate",
            "modification must not precede creation",
            "contradiction" if bad else "consistent", 1.0 if bad else 0.0,
            "ModDate >= CreationDate",
            "ModDate < CreationDate" if bad else "ModDate >= CreationDate",
            reliability=_R_DECLARED,  # two soft timestamps
        ))

    # --- universal: nothing dated in the future --- #
    if _has(F, "future_creation_date") or _has(F, "future_created"):
        edges.append(_edge(
            "not_future", "document dates", "time of analysis",
            "no timestamp lies in the future",
            "contradiction", 1.0, "all dates <= now", "a date is in the future",
            reliability=0.55,  # which field is wrong is uncertain, but a future date can't be legitimate
        ))

    if ev.get("engine") == "pdf":
        _pdf_edges(ev, edges, c, m, st, F)
    elif ev.get("engine") == "ooxml":
        _ooxml_edges(ev, edges, st, F)

    contradictions = [e for e in edges if e["status"] == "contradiction"]
    weak = [e for e in edges if e["status"] == "weak"]
    rho = (len(contradictions) + 0.5 * len(weak)) / len(edges) if edges else 0.0
    mean_kappa = sum(e["kappa"] for e in edges) / len(edges) if edges else 0.0

    # --- reliability-weighted view (ERA): a contradiction between two weak
    #     sources counts for less than one backed by cryptographic evidence.
    def w(e):
        return 0.30 + 0.70 * e["reliability"]

    wsum = sum(w(e) for e in edges) or 1.0
    weighted_kappa = sum(e["kappa"] * w(e) for e in edges) / wsum
    weighted_density = (
        sum(w(e) for e in contradictions) + 0.5 * sum(w(e) for e in weak)
    ) / wsum
    top = max(
        ((e["kappa"] * e["reliability"], e) for e in contradictions),
        default=(0.0, None),
    )

    return {
        "nodes": _nodes(edges),
        "edges": edges,
        "edge_count": len(edges),
        "contradiction_count": len(contradictions),
        "weak_count": len(weak),
        "contradiction_density": round(rho, 3),
        "mean_kappa": round(mean_kappa, 3),
        "weighted_kappa": round(weighted_kappa, 3),
        "weighted_density": round(weighted_density, 3),
        "strongest_contradiction": (
            {"edge": top[1]["id"], "reliability": top[1]["reliability"], "kappa": top[1]["kappa"]}
            if top[1] else None
        ),
    }


def _pdf_edges(ev, edges, c, m, st, F):
    gap = util.days_between(m, c) if (c and m) else None
    updates = st.get("incremental_updates", 0) or 0

    # ModDate change should leave a revision behind
    if gap is not None:
        if gap > 30 and updates == 0:
            edges.append(_edge(
                "edit_evidence", "ModDate", "revision structure",
                "a later modification leaves a new revision",
                "contradiction", 0.85,
                "incremental update present", f"single revision, {round(gap)}d gap",
                reliability=0.60,
            ))
        elif abs(gap) < 1 and updates > 0:
            edges.append(_edge(
                "edit_evidence", "ModDate", "revision structure",
                "appended revisions move the modification date",
                "weak", 0.5,
                "ModDate later than creation", f"{updates} update(s), ModDate unchanged",
                reliability=0.45,
            ))
        else:
            edges.append(_edge(
                "edit_evidence", "ModDate", "revision structure",
                "modification date and revision count agree",
                "consistent", 0.0, "consistent",
                f"{updates} update(s), gap {round(gap, 1)}d",
                reliability=0.60,
            ))

    # trailer /ID stability
    tid = ev.get("trailer_id") or {}
    if tid:
        bad = bool(tid.get("changed")) and (st.get("incremental_updates", 0) or 0) == 0
        edges.append(_edge(
            "id_stability", "trailer /ID[0]", "trailer /ID[1]",
            "identifier halves match on an unmodified file",
            "contradiction" if bad else "consistent", 1.0 if bad else 0.0,
            "ID[0] == ID[1] on a single revision",
            "ID pair differs" if tid.get("changed") else "ID pair matches",
            reliability=_R_STRUCT,
        ))

    # toolchain: authoring app vs producer
    hard = _has(F, "producer_creator_mismatch", 3)
    soft = _has(F, "producer_creator_mismatch", 2) and not hard
    lib = bool(ev.get("_derived", {}).get("library"))
    if hard or soft or lib or ev.get("_derived", {}).get("producer"):
        if hard:
            status, k, obs = "contradiction", 0.9, "mismatch, no history bridge"
        elif soft:
            status, k, obs = "weak", 0.5, "mismatch, no history bridge"
        elif lib:
            status, k, obs = "weak", 0.5, "producer is a library — cannot corroborate the authoring app"
        else:
            status, k, obs = "consistent", 0.0, "consistent"
        edges.append(_edge(
            "toolchain", "Creator / CreatorTool", "Producer",
            "producer is consistent with the authoring application",
            status, k, "same tool family or a recorded export step", obs,
            reliability=_R_FINGERPRINT,
        ))

    # XMP vs DocInfo creation instant
    for f in F:
        if f["code"] == "xmp_docinfo_create_mismatch":
            dd = f["evidence"].get("delta_days", 0)
            edges.append(_edge(
                "xmp_docinfo", "DocInfo /CreationDate", "XMP xmp:CreateDate",
                "the same creation instant in both metadata stores",
                "contradiction" if dd > 3 else "weak", util.clamp(dd / 30.0),
                "identical timestamps", f"{dd} days apart",
                reliability=0.35,
            ))

    # signature coverage
    for sg in ev.get("signatures", []):
        if sg.get("covers_whole_file"):
            status, k = "consistent", 0.0
            obs = "byte range spans the file"
        elif sg.get("superseded_by_later_revision"):
            status, k = "weak", 0.4
            obs = "superseded by a later signed revision"
        else:
            status, k = "contradiction", 1.0
            obs = f"{sg.get('bytes_after_signature', 0)} bytes after the signed range"
        edges.append(_edge(
            f"sig_coverage_{sg.get('index', 1)}",
            f"Signature #{sg.get('index', 1)} /ByteRange", "file bytes",
            "the signature covers the whole visible document",
            status, k, "byte range spans the file", obs,
            reliability=_R_CRYPTO,
        ))
        st_dt = util.parse_iso_date(sg.get("signing_time"))
        if st_dt and c:
            bad = _has(F, "signed_before_created")
            edges.append(_edge(
                f"sig_time_{sg.get('index', 1)}",
                f"Signature #{sg.get('index', 1)} time", "CreationDate",
                "a signature is applied at or after creation",
                "contradiction" if bad else "consistent", 1.0 if bad else 0.0,
                "signing time >= CreationDate",
                "signing time < CreationDate" if bad else "signing time >= CreationDate",
                reliability=0.55,
            ))


def _ooxml_edges(ev, edges, st, F):
    sep = _has(F, "metadata_edited_separately")
    edges.append(_edge(
        "part_time_coherence", "docProps/core.xml", "content part",
        "properties and content are written together",
        "contradiction" if sep else "consistent", 0.8 if sep else 0.0,
        "written within seconds of each other",
        "properties written much later" if sep else "coherent",
        reliability=0.78,
    ))

    rev_mm = _has(F, "revision_editing_time_mismatch")
    edges.append(_edge(
        "revision_time", "cp:revision", "app:TotalTime",
        "editing time is plausible for the revision count",
        "contradiction" if rev_mm else "consistent", 0.75 if rev_mm else 0.0,
        "proportionate", "disproportionate" if rev_mm else "proportionate",
        reliability=0.45,
    ))

    span = _has(F, "inconsistent_part_timestamps")
    if span:
        edges.append(_edge(
            "part_span", "earliest package part", "latest package part",
            "all parts of one save share a write time",
            "weak", 0.5, "parts written together", "parts span hours",
            reliability=0.70,
        ))


def _nodes(edges):
    s: set = set()
    for e in edges:
        s.add(e["a"])
        s.add(e["b"])
    return sorted(s)
