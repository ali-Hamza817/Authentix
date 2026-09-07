"""Evidence Reliability Assessment (ERA).

Not all forensic evidence is equally trustworthy. A signed byte range is
tamper-evident; a ``/Author`` string is whatever the last person typed. ERA
attaches a reliability score R(e) in [0, 1] to each class of evidence and to each
finding, so that:

* findings are ranked by *impact x reliability*, not raw severity;
* a contradiction between two low-reliability sources counts for less than one
  backed by cryptographic evidence (see ``weighted`` in ``decg``);
* the report can show an Evidence Matrix with a reliability column.

The tier scores below are documented defaults with a stated rationale. In the
thesis they are to be validated experimentally (calibration against a labelled
corpus); they are deliberately not presented as ground truth.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# reliability tiers
# --------------------------------------------------------------------------- #
TIERS: dict[str, dict] = {
    "cryptographic": {
        "score": 0.97,
        "label": "cryptographic",
        "rationale": "tamper-evident — forging it requires breaking the signature scheme or the CA",
    },
    "structural_binding": {
        "score": 0.88,
        "label": "structural",
        "rationale": "requires rewriting the file's physical structure consistently; hard to fake cleanly",
    },
    "internal_revision": {
        "score": 0.80,
        "label": "internal",
        "rationale": "written by the tool as a side effect of saving, not a user-facing field",
    },
    "toolchain_fingerprint": {
        "score": 0.66,
        "label": "fingerprint",
        "rationale": "inferred from a tool's structural habits; can be mimicked with effort",
    },
    "embedded_media": {
        "score": 0.60,
        "label": "media",
        "rationale": "EXIF is editable but usually left intact; describes the media, not the document",
    },
    "derived_uuid": {
        "score": 0.52,
        "label": "uuid-derived",
        "rationale": "a real artefact of the generating machine, but the node field may be randomised or tool-specific",
    },
    "declared_metadata": {
        "score": 0.25,
        "label": "declared",
        "rationale": "a free-text field any user or script can set to any value",
    },
    "absence": {
        "score": None,
        "label": "absence",
        "rationale": "absence of evidence is not evidence — interpreted as INSUFFICIENT, not as a score",
    },
}


def tier(name: str) -> dict:
    return TIERS.get(name, TIERS["declared_metadata"])


def score(name: str) -> float:
    s = tier(name)["score"]
    return 0.25 if s is None else s


# --------------------------------------------------------------------------- #
# stance model — SUPPORTED / CONTRADICTED / INSUFFICIENT / NEUTRAL
# --------------------------------------------------------------------------- #
STANCE_SUPPORTED = "supported"        # evidence supports authenticity
STANCE_CONTRADICTED = "contradicted"  # evidence contradicts the claimed origin/history
STANCE_INSUFFICIENT = "insufficient"  # evidence is missing / unknowable — NOT a pass
STANCE_NEUTRAL = "neutral"            # recorded for context; not an authenticity signal (privacy, notes)

# code -> (stance, reliability, evidence basis).  reliability None => INSUFFICIENT.
FINDING_META: dict[str, tuple[str, float | None, str]] = {
    # ---- temporal / metadata (PDF) ----
    "future_creation_date":            (STANCE_CONTRADICTED, 0.55, "declared creation timestamp is logically impossible"),
    "modified_before_created":         (STANCE_CONTRADICTED, 0.55, "declared creation vs modification timestamps (ordering impossible)"),
    "timestamp_gap_no_edits":          (STANCE_CONTRADICTED, 0.45, "declared ModDate vs internal revision structure"),
    "xmp_docinfo_create_mismatch":     (STANCE_CONTRADICTED, 0.35, "DocInfo vs XMP creation dates"),
    "xmp_docinfo_modify_mismatch":     (STANCE_CONTRADICTED, 0.30, "DocInfo vs XMP modification dates"),
    "trailer_id_changed_single_revision": (STANCE_CONTRADICTED, 0.80, "PDF /ID pair vs single-revision structure"),
    # ---- provenance ----
    "producer_creator_mismatch":       (STANCE_CONTRADICTED, 0.62, "authoring-application vs producer toolchain fingerprint"),
    "multiple_producers":              (STANCE_NEUTRAL, 0.80, "distinct /Producer strings across revisions"),
    "metadata_scrubbed":               (STANCE_INSUFFICIENT, None, "no authoring metadata is present at all"),
    "origin_metadata_absent":          (STANCE_INSUFFICIENT, None, "no author and no creation date are present"),
    "programmatic_rewrite":            (STANCE_INSUFFICIENT, 0.68, "producer classified as a PDF manipulation library"),
    "machine_generated":               (STANCE_INSUFFICIENT, 0.66, "producer classified as a document generator"),
    # ---- structure ----
    "active_content":                  (STANCE_NEUTRAL, 0.92, "structural scan for /JS /OpenAction /Launch"),
    "high_entropy_stream":             (STANCE_NEUTRAL, 0.85, "stream entropy measurement"),
    "encrypted":                       (STANCE_NEUTRAL, 0.95, "/Encrypt dictionary present"),
    # ---- signatures ----
    "modified_after_signing":          (STANCE_CONTRADICTED, 0.96, "signed /ByteRange vs actual file bytes"),
    "signature_superseded":            (STANCE_NEUTRAL, 0.95, "signature revision chain"),
    "self_signed_certificate":         (STANCE_NEUTRAL, 0.97, "X.509 issuer equals subject"),
    "signed_before_created":           (STANCE_CONTRADICTED, 0.60, "signing time vs declared creation date"),
    "certified_doc_changed":           (STANCE_CONTRADICTED, 0.92, "DocMDP permission level vs incremental updates"),
    # ---- OOXML ----
    "future_created":                  (STANCE_CONTRADICTED, 0.55, "declared creation timestamp is logically impossible"),
    "revision_editing_time_mismatch":  (STANCE_CONTRADICTED, 0.55, "cp:revision vs app:TotalTime"),
    "author_changed":                  (STANCE_NEUTRAL, 0.25, "dc:creator vs cp:lastModifiedBy"),
    "metadata_edited_separately":      (STANCE_CONTRADICTED, 0.78, "docProps/core.xml vs content-part ZIP timestamps"),
    "inconsistent_part_timestamps":    (STANCE_CONTRADICTED, 0.70, "ZIP part timestamp spread on a low-revision file"),
    "unaccepted_tracked_changes":      (STANCE_NEUTRAL, 0.85, "w:ins / w:del marks in the body"),
    "contains_macros":                 (STANCE_NEUTRAL, 0.95, "vbaProject.bin present"),
    "external_references":             (STANCE_NEUTRAL, 0.88, "relationship targets marked External"),
    "embedded_objects":                (STANCE_NEUTRAL, 0.90, "embedded package parts"),
    # ---- privacy (orthogonal to authenticity) ----
    "username_disclosed":              (STANCE_NEUTRAL, 0.55, "embedded \\Users\\ path"),
    "machine_name_disclosed":          (STANCE_NEUTRAL, 0.55, "embedded UNC host"),
    "mac_address_disclosed":           (STANCE_NEUTRAL, 0.50, "node field of a version-1 UUID"),
    "gps_in_embedded_image":           (STANCE_NEUTRAL, 0.60, "EXIF GPS IFD in an embedded image"),
    "camera_model_disclosed":          (STANCE_NEUTRAL, 0.60, "EXIF IFD0 in an embedded image"),
    "local_path_disclosed":            (STANCE_NEUTRAL, 0.55, "embedded absolute paths"),
    # ---- generic ----
    "legacy_format":                   (STANCE_INSUFFICIENT, None, "format cannot be fully parsed"),
    "unsupported_format":              (STANCE_INSUFFICIENT, None, "format is unrecognised"),
    "identifying_traces":              (STANCE_NEUTRAL, 0.5, "aggregate of device-trace findings"),
}

_IMPACT = {4: 1.0, 3: 0.7, 2: 0.4, 1: 0.15}


def confidence_bucket(value: float) -> str:
    if value >= 0.5:
        return "High"
    if value >= 0.22:
        return "Medium"
    return "Low"


def enrich_finding(f: dict) -> dict:
    """Stamp stance / reliability / confidence / reasoning onto a finding in place."""
    stance, rel, basis = FINDING_META.get(
        f["code"],
        (STANCE_CONTRADICTED if f.get("category") in ("temporal", "metadata", "signature") else STANCE_NEUTRAL,
         0.4, f.get("category", "unspecified") + " evidence"),
    )
    f["stance"] = stance
    f["reliability"] = rel
    if stance == STANCE_INSUFFICIENT or rel is None:
        f["confidence"] = "n/a"
        f["confidence_score"] = 0.0
    else:
        c = _IMPACT.get(f["severity"], 0.4) * rel
        f["confidence"] = confidence_bucket(c)
        f["confidence_score"] = round(c, 3)
    f.setdefault("reasoning", {
        "evidence": basis,
        "reasoning": f["detail"],
        "conclusion": _conclusion(stance, f["title"]),
    })
    return f


def _conclusion(stance: str, title: str) -> str:
    if stance == STANCE_CONTRADICTED:
        return "The observed evidence is inconsistent with the document's claimed origin or history."
    if stance == STANCE_INSUFFICIENT:
        return "The evidence needed to corroborate this is absent — this is not a sign of authenticity."
    if stance == STANCE_SUPPORTED:
        return "The observed evidence is consistent with the document's claimed origin or history."
    return "Recorded for context; not an authenticity signal on its own."


# --------------------------------------------------------------------------- #
# Evidence Matrix — the per-observation reliability table
# --------------------------------------------------------------------------- #
def build_matrix(ev: dict) -> list[dict]:
    """A flat list of the concrete observations behind the assessment, each tiered."""
    out: list[dict] = []

    def row(rid, label, value, tier_name, source, present=True):
        out.append({
            "id": rid, "label": label,
            "value": None if value in (None, "", []) else str(value),
            "present": bool(present and value not in (None, "", [])),
            "tier": tier_name,
            "reliability": score(tier_name),
            "reliability_label": tier(tier_name)["label"],
            "source": source,
        })

    md = ev.get("metadata") or {}
    xmp = ev.get("xmp") or {}
    core = ev.get("core") or {}
    app = ev.get("app") or {}
    st = ev.get("structure") or {}
    d = ev.get("_derived") or {}
    sigs = ev.get("signatures") or []

    if ev.get("engine") == "pdf":
        row("creation_date", "Creation date", md.get("creation_date") or xmp.get("create_date"),
            "declared_metadata", "/CreationDate · XMP xmp:CreateDate")
        row("mod_date", "Modification date", md.get("mod_date") or xmp.get("modify_date"),
            "declared_metadata", "/ModDate · XMP xmp:ModifyDate")
        row("author", "Author", md.get("author"), "declared_metadata", "/Author")
        row("creator", "Authoring application", d.get("creator") or xmp.get("creator_tool"),
            "declared_metadata", "/Creator · XMP CreatorTool")
        row("producer", "PDF producer", d.get("producer"), "toolchain_fingerprint", "/Producer + structural fingerprint")
        row("revisions", "Revision / incremental-update structure",
            f"{st.get('revisions', 1)} revision(s)", "structural_binding", "XRef + /Prev chain + %%EOF markers")
        tid = ev.get("trailer_id") or {}
        if tid:
            row("trailer_id", "File identifier (/ID)",
                "changed" if tid.get("changed") else "stable", "structural_binding", "trailer /ID pair")
        row("active_content", "Active content", ", ".join(st.get("active_content") or []) or "none",
            "structural_binding", "raw scan for /JS /OpenAction /Launch")
        for sg in sigs:
            row(f"sig_{sg.get('index')}_cert", f"Signature #{sg.get('index')} — signer certificate",
                sg.get("signer_subject") or sg.get("name"), "cryptographic",
                f"PKCS#7 SignedData (signature #{sg.get('index')})")
            row(f"sig_{sg.get('index')}_cov", f"Signature #{sg.get('index')} — byte-range coverage",
                "whole file" if sg.get("covers_whole_file") else f"{sg.get('bytes_after_signature')} bytes uncovered",
                "cryptographic", f"signed /ByteRange (signature #{sg.get('index')})")
            row(f"sig_{sg.get('index')}_time", f"Signature #{sg.get('index')} — signing time",
                sg.get("signing_time"), "cryptographic", "/M · PKCS#7 signingTime")
    else:
        row("creation_date", "Creation date", core.get("created"), "declared_metadata", "docProps/core.xml dcterms:created")
        row("mod_date", "Modification date", core.get("modified"), "declared_metadata", "docProps/core.xml dcterms:modified")
        row("author", "Author", core.get("creator"), "declared_metadata", "dc:creator")
        row("last_editor", "Last editor", core.get("last_modified_by"), "declared_metadata", "cp:lastModifiedBy")
        row("application", "Application", app.get("application"), "declared_metadata", "docProps/app.xml Application")
        row("revision", "Revision count", core.get("revision"), "declared_metadata", "cp:revision")
        row("edit_time", "Total editing time", app.get("total_edit_time_min"), "declared_metadata", "app:TotalTime")
        row("part_times", "Package part write times",
            f"{st.get('zip_part_span_seconds')} s span" if st.get("zip_part_span_seconds") is not None else None,
            "internal_revision", "ZIP central-directory timestamps")
        row("rsid", "Edit-session IDs (rsid)", st.get("rsid_edit_sessions"), "internal_revision", "word/settings.xml w:rsid")
        row("macros", "VBA macro project", "present" if st.get("has_macros") else "none",
            "structural_binding", "word/vbaProject.bin")

    return out
