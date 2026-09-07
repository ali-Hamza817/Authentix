"""EWDCA — Evidence-Weighted Document Credibility Assessment.

    Risk(D) = alpha*A + beta*K + gamma*(1-P) + delta*(1-S) + lambda*rho + mu*L
    Credibility(D) = round( 100 * clamp(1 - Risk(D), 0, 1) )

A  structural / behavioural anomaly score (active content, entropy, macros, ...)
K  aggregated contradiction magnitude from the DECG (max blended with mean)
P  provenance confidence (1 = fully corroborated origin)
S  signature integrity (1 = valid & full coverage; 0.6 = unsigned/neutral; 0 = broken)
rho contradiction density from the DECG
L  finding-severity load across every category

The six weights sum to 1 so Risk stays in [0, 1]. They are documented defaults —
in the thesis they are fit on a labelled development set and the score is
calibrated (isotonic regression).

Some findings are *dispositive*: a modification date that precedes creation, a
future timestamp, or content added after signing cannot be explained away, so
they cap the score regardless of everything else.
"""
from __future__ import annotations

from . import util

WEIGHTS = {"alpha": 0.17, "beta": 0.25, "gamma": 0.15, "delta": 0.10, "lambda": 0.13, "mu": 0.20}

BANDS = [(75, "Credible"), (50, "Guarded"), (25, "Suspicious"), (0, "Untrusted")]

# code -> hard ceiling on the credibility score
DISPOSITIVE_CAPS = {
    "modified_before_created": 28,
    "modified_after_signing": 22,
    "certified_doc_changed": 38,
    "future_creation_date": 33,
    "future_created": 33,
    "signed_before_created": 42,
}
SEVERITY_LOAD = {1: 0.03, 2: 0.08, 3: 0.18, 4: 0.40}


def _band(cred: int) -> str:
    return next(name for thr, name in BANDS if cred >= thr)


def _anomaly(ev: dict) -> float:
    st = ev.get("structure", {})
    a = 0.0
    if ev.get("engine") == "pdf":
        ac = st.get("active_content") or []
        if ac:
            a += 0.30 + 0.08 * min(3, len(ac))
            if any("Launch" in c for c in ac):
                a += 0.22
        if (st.get("max_stream_entropy") or 0) >= 7.95:
            a += 0.08
        if st.get("encrypted"):
            a += 0.06
        oc, pg = st.get("object_count") or 0, st.get("pages") or 1
        if pg and oc / max(pg, 1) > 400:
            a += 0.12
    else:
        if st.get("has_macros"):
            a += 0.40
        if st.get("external_references"):
            a += 0.12
        if st.get("unaccepted_revisions"):
            a += 0.08
        if st.get("embedded_objects"):
            a += 0.05
    return util.clamp(a)


def _contradiction_term(decg: dict) -> float:
    """Reliability-weighted contradiction magnitude K.

    A contradiction between two low-reliability sources moves the score less than
    one anchored in cryptographic or structural evidence.
    """
    edges = decg.get("edges", []) or []
    hot = [e for e in edges if e["status"] in ("contradiction", "weak")]
    if not hot:
        return 0.0
    weighted = [e["kappa"] * (0.30 + 0.70 * e.get("reliability", 0.4)) for e in hot]
    peak = max(e["kappa"] * e.get("reliability", 0.4) for e in hot)
    return util.clamp(0.55 * max(weighted) + 0.30 * (sum(weighted) / len(weighted)) + 0.35 * peak)


def _finding_load(ev: dict) -> float:
    return util.clamp(sum(SEVERITY_LOAD[f["severity"]] for f in ev.get("findings", [])))


def _unknown(ev: dict) -> dict:
    return {
        "credibility_score": None,
        "band": "Unknown",
        "confidence": "n/a",
        "confidence_basis": "file could not be analysed",
        "risk": None,
        "score_capped_at": None,
        "cap_reason": None,
        "components": {},
        "weights": WEIGHTS,
        "signed": bool(ev.get("signatures")),
        "primary_drivers": ["file format not analysable"],
        "risk_factors": [],
    }


def score(ev: dict, decg: dict) -> dict:
    if ev.get("engine") not in ("pdf", "ooxml"):
        return _unknown(ev)

    A = _anomaly(ev)
    K = _contradiction_term(decg)
    P = util.clamp(float(ev.get("provenance_confidence", 1.0) or 1.0))
    rho = util.clamp(float(decg.get("weighted_density", decg.get("contradiction_density", 0.0)) or 0.0))
    L = _finding_load(ev)

    si = ev.get("signature_integrity", None)
    if si is None:
        S, signed = 0.6, False
    else:
        S, signed = util.clamp(float(si)), True

    w = WEIGHTS
    risk = util.clamp(
        w["alpha"] * A + w["beta"] * K + w["gamma"] * (1 - P)
        + w["delta"] * (1 - S) + w["lambda"] * rho + w["mu"] * L
    )
    cred = round(100 * (1 - risk))

    # ---- dispositive caps ------------------------------------------------- #
    codes = [f["code"] for f in ev.get("findings", [])]
    material = [f for f in ev.get("findings", []) if f["severity"] >= 3]
    cap, cap_reason = 100, None
    for c in codes:
        if c in DISPOSITIVE_CAPS and DISPOSITIVE_CAPS[c] < cap:
            cap, cap_reason = DISPOSITIVE_CAPS[c], c.replace("_", " ")
    if len(material) >= 2 and cap > 45:
        cap, cap_reason = 45, f"{len(material)} independent material findings"
    if any(f["severity"] == 4 for f in ev.get("findings", [])) and cap > 72:
        high = next(f for f in ev["findings"] if f["severity"] == 4)
        cap, cap_reason = 72, f"a high-severity finding ({high['title'].lower()})"
    if P <= 0.5 and cap > 70:
        # If we cannot establish where the document came from, it cannot be "Credible",
        # however internally consistent the bytes are.
        cap, cap_reason = 70, "provenance could not be established"

    capped = None
    if cred > cap:
        capped = cap
        cred = cap
    band = _band(cred)

    risk_factors = []
    for f in sorted(ev.get("findings", []), key=lambda x: -x.get("confidence_score", 0.0)):
        if f["severity"] >= 2 and f.get("stance") != "neutral":
            risk_factors.append({
                "title": f["title"],
                "severity": f["severity_label"],
                "stance": f.get("stance"),
                "confidence": f.get("confidence"),
                "category": f["category"],
                "detail": f["detail"],
            })

    drivers = []
    if capped is not None:
        drivers.append(f"score capped at {capped} — {cap_reason}")
    if K >= 0.30:
        drivers.append("cross-evidence contradictions in the consistency graph")
    if rho >= 0.25:
        drivers.append(f"contradiction density {rho:.2f}")
    if P <= 0.60:
        drivers.append("low provenance confidence — origin not corroborated")
    if signed and S <= 0.20:
        drivers.append("signature does not cover the visible document")
    if A >= 0.40:
        drivers.append("structural anomalies / active content")
    if L >= 0.35:
        drivers.append("multiple findings across several evidence categories")
    if not drivers:
        drivers.append("no material inconsistencies")

    # ---- how confident are we in this verdict? (impact x reliability) ----- #
    contradicted = [f for f in ev.get("findings", []) if f.get("stance") == "contradicted"]
    insufficient = [f for f in ev.get("findings", []) if f.get("stance") == "insufficient"]
    if contradicted:
        peak = max(f.get("confidence_score", 0.0) for f in contradicted)
        verdict_conf = "High" if peak >= 0.5 else ("Medium" if peak >= 0.22 else "Low")
        conf_basis = "backed by " + max(contradicted, key=lambda f: f.get("confidence_score", 0.0))["reasoning"]["evidence"]
    elif band in ("Credible", "Guarded") and not insufficient:
        verdict_conf = "Medium" if band == "Guarded" else "High"
        conf_basis = "no contradictions across the reliable evidence"
    else:
        verdict_conf = "Low"
        conf_basis = "key corroborating evidence is absent"

    return {
        "credibility_score": cred,
        "band": band,
        "confidence": verdict_conf,
        "confidence_basis": conf_basis,
        "risk": round(risk, 3),
        "score_capped_at": capped,
        "cap_reason": cap_reason if capped is not None else None,
        "components": {
            "A_anomaly": round(A, 3),
            "K_contradiction": round(K, 3),
            "P_provenance_confidence": round(P, 3),
            "S_signature_integrity": round(S, 3),
            "rho_contradiction_density": round(rho, 3),
            "L_finding_load": round(L, 3),
        },
        "weights": w,
        "signed": signed,
        "primary_drivers": drivers,
        "risk_factors": risk_factors[:8],
    }
