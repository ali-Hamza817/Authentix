"""PDF forensic evidence extraction.

Pulls metadata (DocInfo + XMP), physical structure, incremental-revision history
and digital-signature coverage out of a PDF, then raises findings wherever those
accounts disagree with each other.
"""
from __future__ import annotations

import binascii
import io
import re
from datetime import datetime, timedelta

from .. import util

try:  # pypdf is the only hard dependency of the analyzer
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


SEV_LABEL = {1: "Info", 2: "Low", 3: "Medium", 4: "High"}

# Raw byte markers for active / high-risk constructs.
ACTIVE_KEYS = [
    (b"/JavaScript", "JavaScript"),
    (b"/JS", "JavaScript action (/JS)"),
    (b"/OpenAction", "OpenAction — runs when the file opens"),
    (b"/AA", "Additional Actions (/AA)"),
    (b"/Launch", "Launch action — starts an external program"),
    (b"/EmbeddedFile", "Embedded file"),
    (b"/RichMedia", "RichMedia / Flash object"),
    (b"/XFA", "XFA dynamic form"),
    (b"/SubmitForm", "SubmitForm action"),
    (b"/ImportData", "ImportData action"),
    (b"/GoToR", "Remote go-to action"),
]

# Tool-family fingerprints for the provenance / toolchain check.
_FAMILIES = {
    "Microsoft Word": ["microsoft word", "microsoft office word", "word for", "microsoft 365"],
    "Microsoft Print to PDF": ["microsoft: print to pdf", "print to pdf"],
    "LibreOffice / OpenOffice": ["libreoffice", "openoffice", "staroffice"],
    "Adobe": ["adobe", "acrobat", "pdf library", "indesign", "distiller", "framemaker", "livecycle"],
    "Chromium (Skia)": ["skia/pdf", "chrome", "chromium", "microsoft edge", "headlesschrome"],
    "TeX": ["tex", "pdftex", "xetex", "luatex", "dvips", "dvipdfm"],
    "Ghostscript": ["ghostscript"],
    "iText": ["itext", "lowagie"],
    "ReportLab": ["reportlab"],
    "Apple Quartz": ["quartz", "mac os x", "coregraphics", "cairo quartz"],
    "wkhtmltopdf / Qt": ["wkhtmltopdf", "qt "],
    "Cairo": ["cairo "],
    "PDFsharp / MigraDoc": ["pdfsharp", "migradoc"],
    "Ghostscript/GPL": ["gpl ghostscript"],
    "Scanner / Image": ["scan", "paperport", "kofax", "twain"],
}

# Editor-family -> exporter-family pairs that are common and usually benign.
_SOFT_EXPORT_PAIRS = {
    ("Microsoft Word", "Adobe"),
    ("Microsoft Word", "Chromium (Skia)"),
    ("Microsoft Word", "Ghostscript"),
    ("Microsoft Word", "Microsoft Print to PDF"),
    ("LibreOffice / OpenOffice", "Adobe"),
    ("TeX", "Ghostscript"),
}


def _finding(code, severity, category, title, detail, evidence=None):
    return {
        "code": code,
        "severity": severity,
        "severity_label": SEV_LABEL[severity],
        "category": category,
        "title": title,
        "detail": detail,
        "evidence": evidence or {},
    }


# --------------------------------------------------------------------------- #
# extraction helpers
# --------------------------------------------------------------------------- #
def _docinfo(reader) -> dict:
    out: dict = {}
    md = getattr(reader, "metadata", None)
    if not md:
        return out

    def g(key):
        try:
            v = md.get(key)
            return str(v) if v is not None else None
        except Exception:
            return None

    out["title"] = g("/Title")
    out["author"] = g("/Author")
    out["subject"] = g("/Subject")
    out["keywords"] = g("/Keywords")
    out["creator"] = g("/Creator")
    out["producer"] = g("/Producer")
    out["trapped"] = g("/Trapped")
    out["creation_date_raw"] = g("/CreationDate")
    out["mod_date_raw"] = g("/ModDate")
    out["creation_date"] = util.iso(util.parse_pdf_date(out["creation_date_raw"]))
    out["mod_date"] = util.iso(util.parse_pdf_date(out["mod_date_raw"]))
    # any custom info keys
    try:
        known = {
            "/Title", "/Author", "/Subject", "/Keywords", "/Creator", "/Producer",
            "/CreationDate", "/ModDate", "/Trapped",
        }
        out["custom_keys"] = sorted(str(k) for k in md.keys() if str(k) not in known)
    except Exception:
        out["custom_keys"] = []
    return out


def _xmp(reader) -> dict:
    out: dict = {}
    try:
        x = reader.xmp_metadata
    except Exception:
        x = None
    if not x:
        return out

    def gv(attr):
        try:
            v = getattr(x, attr, None)
        except Exception:
            return None
        if isinstance(v, datetime):
            return util.iso(v)
        if isinstance(v, (list, tuple)):
            return ", ".join(str(i) for i in v) or None
        return str(v) if v else None

    out["create_date"] = gv("xmp_create_date")
    out["modify_date"] = gv("xmp_modify_date")
    out["metadata_date"] = gv("xmp_metadata_date")
    out["creator_tool"] = gv("xmp_creator_tool")
    out["producer"] = gv("pdf_producer")
    out["title"] = gv("dc_title")

    try:
        xml = x.stream.get_data()
        out["raw_present"] = True
        out["history"] = _xmp_history(xml)
        did = re.search(rb"xmpMM:DocumentID>([^<]+)<", xml) or re.search(rb'xmpMM:DocumentID="([^"]+)"', xml)
        iid = re.search(rb"xmpMM:InstanceID>([^<]+)<", xml) or re.search(rb'xmpMM:InstanceID="([^"]+)"', xml)
        oid = re.search(rb"xmpMM:OriginalDocumentID>([^<]+)<", xml)
        out["document_id"] = did.group(1).decode("latin-1", "ignore") if did else None
        out["instance_id"] = iid.group(1).decode("latin-1", "ignore") if iid else None
        out["original_document_id"] = oid.group(1).decode("latin-1", "ignore") if oid else None
    except Exception:
        out.setdefault("history", [])
    return out


def _xmp_history(xml: bytes) -> list:
    events = []
    blocks = re.findall(rb"<rdf:li[^>]*>(.*?)</rdf:li>", xml, re.S)
    blocks += re.findall(rb"<rdf:li\b([^>]*stEvt:[^>]*)/>", xml, re.S)
    for li in blocks:
        def f(tag):
            m = re.search(rb"stEvt:%s>([^<]+)<" % tag, li) or re.search(rb'stEvt:%s="([^"]+)"' % tag, li)
            return m.group(1).decode("latin-1", "ignore").strip() if m else None

        action, when, agent, inst = f(b"action"), f(b"when"), f(b"softwareAgent"), f(b"instanceID")
        if action or when or agent:
            events.append({
                "action": action,
                "when": util.iso(util.parse_iso_date(when)) if when else None,
                "software_agent": agent,
                "instance_id": inst,
            })
    return events


def _structure(data: bytes, reader) -> dict:
    s: dict = {}
    s["pdf_version"] = data[1:8].decode("latin-1", "ignore").strip()
    s["file_size"] = len(data)
    s["eof_markers"] = data.count(b"%%EOF")
    s["startxref_count"] = data.count(b"startxref")
    prevs = re.findall(rb"/Prev\s+\d+", data)
    s["prev_pointers"] = len(prevs)
    s["incremental_updates"] = max(0, max(s["eof_markers"], len(prevs) + 1) - 1)
    s["revisions"] = s["incremental_updates"] + 1
    s["object_count"] = len(re.findall(rb"[\r\n]\d+[ \t]+\d+[ \t]+obj\b", b"\n" + data))
    s["uses_object_streams"] = b"/ObjStm" in data
    s["uses_xref_streams"] = b"/Type/XRef" in data or b"/Type /XRef" in data
    s["linearized"] = b"/Linearized" in data[:4096]
    s["encrypted"] = bool(getattr(reader, "is_encrypted", False)) if reader else (b"/Encrypt" in data)
    try:
        s["pages"] = len(reader.pages) if reader else None
    except Exception:
        s["pages"] = None

    active = [label for key, label in ACTIVE_KEYS if key in data]
    s["active_content"] = sorted(set(active))
    s["has_acroform"] = b"/AcroForm" in data
    s["has_docmdp"] = b"/DocMDP" in data

    producers = {m.decode("latin-1", "ignore").strip()
                 for m in re.findall(rb"/Producer\s*\(([^)\\]{0,240})\)", data)}
    creators = {m.decode("latin-1", "ignore").strip()
                for m in re.findall(rb"/Creator\s*\(([^)\\]{0,240})\)", data)}
    moddates = {m.decode("latin-1", "ignore").strip()
                for m in re.findall(rb"/ModDate\s*\(([^)]{0,80})\)", data)}
    s["producers_seen"] = sorted(p for p in producers if p)
    s["creators_seen"] = sorted(c for c in creators if c)
    s["moddates_seen"] = sorted(d for d in moddates if d)

    ents = []
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end == -1 or end - start <= 64:
            continue
        ents.append(util.shannon_entropy(data[start:min(end, start + 20000)]))
        if len(ents) >= 80:
            break
    s["stream_sample_count"] = len(ents)
    s["avg_stream_entropy"] = round(sum(ents) / len(ents), 3) if ents else None
    s["max_stream_entropy"] = round(max(ents), 3) if ents else None
    return s


def _raw_bytes(x) -> bytes:
    """Best-effort raw bytes from a pypdf string/bytes object of any flavour."""
    ob = getattr(x, "original_bytes", None)
    if isinstance(ob, (bytes, bytearray)):
        return bytes(ob)
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    if isinstance(x, str):
        return x.encode("latin-1", "ignore")
    return str(x).encode("latin-1", "ignore")


def _trailer_id(reader) -> dict | None:
    try:
        ids = reader.trailer.get("/ID")
        if not ids or len(ids) < 2:
            return None
        a, b = _raw_bytes(ids[0]), _raw_bytes(ids[1])
        return {"id0": a.hex(), "id1": b.hex(), "changed": a != b}
    except Exception:
        return None


def _family(s: str | None) -> str | None:
    s = (s or "").lower()
    if not s:
        return None
    for fam, keys in _FAMILIES.items():
        if any(k in s for k in keys):
            return fam
    return None


def _toolchain_mismatch(creator, producer, ctool, history):
    """Return (severity, message) when the authoring tool and PDF producer disagree."""
    fam_c = _family(creator) or _family(ctool)
    fam_p = _family(producer)
    if not fam_c or not fam_p or fam_c == fam_p:
        return None
    has_bridge = bool(history)
    if (fam_c, fam_p) in _SOFT_EXPORT_PAIRS:
        if has_bridge:
            return None
        return (2, (
            f"Metadata says the document was authored in “{creator or ctool}” but the PDF itself was "
            f"written by “{producer}”. Exporting from an editor to a different PDF engine is common, but "
            f"there is no XMP history entry recording that step."
        ))
    return (3, (
        f"The document claims it was authored in “{creator or ctool}” ({fam_c}) while the PDF was produced "
        f"by an unrelated tool, “{producer}” ({fam_p}), with no linking history. The stated origin is doubtful."
    ))


def _signatures(data: bytes) -> list:
    sigs = []
    for idx, m in enumerate(re.finditer(
        rb"/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]", data
    )):
        s1, l1, s2, l2 = (int(x) for x in m.groups())
        region = data[max(0, m.start() - 1200): m.start() + 8000]
        covered_end = s2 + l2
        bytes_after = len(data) - covered_end
        later_has_sig = b"/ByteRange" in data[covered_end:]

        sig = {
            "index": idx + 1,
            "byte_range": [s1, l1, s2, l2],
            "covered_bytes": l1 + l2,
            "bytes_after_signature": bytes_after,
            "covers_whole_file": bytes_after <= 3,
            "superseded_by_later_revision": bytes_after > 3 and later_has_sig,
        }

        def rx(pat):
            mm = re.search(pat, region)
            return mm.group(1).decode("latin-1", "ignore").strip() if mm else None

        sig["sub_filter"] = rx(rb"/SubFilter\s*/([A-Za-z0-9.+\-]+)")
        sig["filter"] = rx(rb"/Filter\s*/([A-Za-z0-9.+\-]+)")
        sig["name"] = rx(rb"/Name\s*\(([^)]{0,240})\)")
        sig["reason"] = rx(rb"/Reason\s*\(([^)]{0,240})\)")
        sig["location"] = rx(rb"/Location\s*\(([^)]{0,240})\)")
        sig["contact_info"] = rx(rb"/ContactInfo\s*\(([^)]{0,240})\)")
        m_dt = rx(rb"/M\s*\(([^)]{0,80})\)")
        sig["signing_time"] = util.iso(util.parse_pdf_date(m_dt)) if m_dt else None
        sig["is_certification"] = b"/DocMDP" in region
        p_perm = re.search(rb"/DocMDP.{0,120}?/P\s+(\d)", region, re.S)
        sig["docmdp_permission"] = int(p_perm.group(1)) if p_perm else None

        _enrich_from_pkcs7(data, s1, l1, s2, sig)

        if sig["covers_whole_file"]:
            sig["integrity"] = "structure-intact"
        elif sig["superseded_by_later_revision"]:
            sig["integrity"] = "superseded"
        else:
            sig["integrity"] = "modified-after-signing"
        sigs.append(sig)
    return sigs


def _enrich_from_pkcs7(data, s1, l1, s2, sig):
    try:
        from cryptography.hazmat.primitives.serialization import pkcs7
        from cryptography.x509.oid import NameOID
    except Exception:
        sig["pkcs7"] = "cryptography not installed"
        return
    try:
        gap = data[s1 + l1: s2]
        hexs = re.sub(rb"[^0-9A-Fa-f]", b"", gap)
        der = binascii.unhexlify(hexs[: len(hexs) // 2 * 2]).rstrip(b"\x00")
        certs = list(pkcs7.load_der_pkcs7_certificates(der))
        if not certs:
            return

        def name(n):
            try:
                cn = n.get_attributes_for_oid(NameOID.COMMON_NAME)
                org = n.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
                parts = [a[0].value for a in (cn, org) if a]
                return " / ".join(parts) if parts else n.rfc4514_string()
            except Exception:
                return None

        ee = certs[0]
        sig["signer_subject"] = name(ee.subject)
        sig["signer_issuer"] = name(ee.issuer)
        try:
            sig["cert_not_before"] = util.iso(ee.not_valid_before_utc)
            sig["cert_not_after"] = util.iso(ee.not_valid_after_utc)
        except AttributeError:
            sig["cert_not_before"] = util.iso(ee.not_valid_before)
            sig["cert_not_after"] = util.iso(ee.not_valid_after)
        sig["self_signed"] = ee.subject == ee.issuer
        sig["cert_chain_length"] = len(certs)
    except Exception as e:
        sig["pkcs7"] = f"unparsable ({type(e).__name__})"


# --------------------------------------------------------------------------- #
# main entry point
# --------------------------------------------------------------------------- #
def analyze(data: bytes) -> dict:
    ev: dict = {"engine": "pdf", "findings": [], "timeline": [], "errors": []}
    reader = None
    if PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(data), strict=False)
        except Exception as e:
            ev["errors"].append({"stage": "pypdf-open", "error": f"{type(e).__name__}: {e}"})

    docinfo = _docinfo(reader) if reader else {}
    xmp = _xmp(reader) if reader else {}
    structure = _structure(data, reader)
    trailer_id = _trailer_id(reader) if reader else None
    sigs = _signatures(data)
    ev.update(metadata=docinfo, xmp=xmp, structure=structure, trailer_id=trailer_id, signatures=sigs)

    c_dt = util.parse_pdf_date(docinfo.get("creation_date_raw")) or util.parse_iso_date(xmp.get("create_date"))
    m_dt = util.parse_pdf_date(docinfo.get("mod_date_raw")) or util.parse_iso_date(xmp.get("modify_date"))
    x_c = util.parse_iso_date(xmp.get("create_date"))
    x_m = util.parse_iso_date(xmp.get("modify_date"))
    now = util.now_utc()
    F = ev["findings"]

    # ---- temporal consistency ---------------------------------------------- #
    if c_dt and c_dt - now > timedelta(days=1):
        F.append(_finding("future_creation_date", 4, "temporal",
            "Creation date is in the future",
            f"The document claims it was created on {util.iso(c_dt)}, after the moment of analysis "
            f"({util.iso(now)}). A real creation timestamp cannot be in the future.",
            {"creation_date": util.iso(c_dt)}))

    if c_dt and m_dt and (c_dt - m_dt) > timedelta(minutes=5):
        F.append(_finding("modified_before_created", 4, "temporal",
            "The document was “modified” before it was “created”",
            f"ModDate ({util.iso(m_dt)}) precedes CreationDate ({util.iso(c_dt)}). At least one of the two "
            f"timestamps has been edited.",
            {"creation_date": util.iso(c_dt), "mod_date": util.iso(m_dt)}))

    if c_dt and m_dt:
        gap = util.days_between(m_dt, c_dt)
        if gap and gap > 30 and structure["revisions"] == 1:
            F.append(_finding("timestamp_gap_no_edits", 3, "temporal",
                "Large edit gap with no structural sign of editing",
                f"ModDate is {round(gap)} days after CreationDate, yet the file has a single revision and no "
                f"incremental updates. A genuine later edit normally appends a new revision.",
                {"gap_days": round(gap, 1), "revisions": 1}))

    if x_c and c_dt:
        d = abs(util.days_between(x_c, c_dt) or 0)
        if d > 1:
            F.append(_finding("xmp_docinfo_create_mismatch", 3, "metadata",
                "XMP and Document Info creation dates disagree",
                f"DocInfo /CreationDate is {util.iso(c_dt)} but XMP xmp:CreateDate is {util.iso(x_c)} "
                f"({round(d, 1)} days apart). A single consistent tool writes the same value to both.",
                {"docinfo": util.iso(c_dt), "xmp": util.iso(x_c), "delta_days": round(d, 1)}))

    if x_m and m_dt:
        d = abs(util.days_between(x_m, m_dt) or 0)
        if d > 2:
            F.append(_finding("xmp_docinfo_modify_mismatch", 2, "metadata",
                "XMP and Document Info modification dates disagree",
                f"DocInfo /ModDate is {util.iso(m_dt)} but XMP xmp:ModifyDate is {util.iso(x_m)} "
                f"({round(d, 1)} days apart).",
                {"docinfo": util.iso(m_dt), "xmp": util.iso(x_m), "delta_days": round(d, 1)}))

    # ---- trailer identifier --------------------------------------------------#
    if trailer_id and trailer_id.get("changed") and structure["incremental_updates"] == 0:
        F.append(_finding("trailer_id_changed_single_revision", 3, "structure",
            "File identifier changed on a single-revision document",
            "The permanent and changing halves of the PDF /ID differ, which means the file was re-written after its "
            "original creation — even though only one revision is present. Re-saving through an editor does this.",
            trailer_id))

    # ---- provenance / toolchain ------------------------------------------- #
    creator = (docinfo.get("creator") or "").strip()
    producer = (docinfo.get("producer") or "").strip()
    ctool = (xmp.get("creator_tool") or "").strip()
    history = xmp.get("history") or []
    prov_conf = 1.0

    if not creator and not producer and not ctool:
        prov_conf -= 0.4
        F.append(_finding("metadata_scrubbed", 3, "provenance",
            "Authoring metadata is missing",
            "No /Creator, /Producer or XMP CreatorTool is present. Metadata has been stripped, or the file was "
            "produced by a tool that deliberately omits it. Either way, the origin cannot be corroborated.",
            {}))
    else:
        mm = _toolchain_mismatch(creator, producer, ctool, history)
        if mm:
            sev, msg = mm
            prov_conf -= 0.25 if sev == 2 else 0.45
            F.append(_finding("producer_creator_mismatch", sev, "provenance",
                "Authoring application and PDF producer are inconsistent", msg,
                {"creator": creator or None, "producer": producer or None, "xmp_creator_tool": ctool or None}))

    if len(structure["producers_seen"]) > 1:
        prov_conf -= 0.12
        F.append(_finding("multiple_producers", 2, "provenance",
            "The file was written by more than one tool",
            "Distinct /Producer strings appear across revisions: "
            + "; ".join(structure["producers_seen"])
            + ". Normal for a reviewed document; recorded for the provenance trail.",
            {"producers": structure["producers_seen"]}))

    # ---- structure / active content ------------------------------------- #
    if structure["active_content"]:
        launch = any("Launch" in c for c in structure["active_content"])
        openact = any("OpenAction" in c for c in structure["active_content"])
        sev = 4 if (launch or (openact and any("JavaScript" in c for c in structure["active_content"]))) else 3
        F.append(_finding("active_content", sev, "structure",
            "Document contains active / executable content",
            "Detected: " + ", ".join(structure["active_content"])
            + ". Active content is not proof of malice, but it is the primary vehicle for weaponised documents.",
            {"constructs": structure["active_content"]}))

    if (structure["max_stream_entropy"] or 0) >= 7.95 and not structure["encrypted"]:
        F.append(_finding("high_entropy_stream", 2, "structure",
            "A near-random high-entropy stream is present",
            f"Peak stream entropy is {structure['max_stream_entropy']} bits/byte. Expected for compressed images, "
            f"but also what a packed or concealed payload looks like.",
            {"max_entropy": structure["max_stream_entropy"]}))

    if structure["encrypted"]:
        F.append(_finding("encrypted", 1, "structure",
            "Document is encrypted",
            "The PDF carries an /Encrypt dictionary. Some evidence (page content, embedded metadata) may be "
            "unavailable without the password.", {}))

    # ---- signatures ----------------------------------------------------- #
    sig_integrity = None
    for sg in sigs:
        st = util.parse_iso_date(sg.get("signing_time"))
        if sg["integrity"] == "modified-after-signing":
            sig_integrity = 0.0
            F.append(_finding("modified_after_signing", 4, "signature",
                f"Content was added after signature #{sg['index']} was applied",
                f"The signature covers {sg['covered_bytes']} bytes, but {sg['bytes_after_signature']} bytes follow "
                f"the signed range and are not another signature revision. The document you see is not the document "
                f"that was signed.",
                {"bytes_after_signature": sg["bytes_after_signature"], "byte_range": sg["byte_range"]}))
        elif sg["integrity"] == "superseded":
            F.append(_finding("signature_superseded", 1, "signature",
                f"Signature #{sg['index']} was superseded by a later revision",
                "A later signed revision follows this one — normal for a document signed by several parties.",
                {}))
        if sg.get("self_signed"):
            F.append(_finding("self_signed_certificate", 2, "signature",
                f"Signature #{sg['index']} uses a self-signed certificate",
                "The signing certificate is its own issuer, so it is not vouched for by any recognised certificate "
                "authority. The signature proves key ownership, not identity.",
                {"subject": sg.get("signer_subject")}))
        if st and c_dt and st < c_dt - timedelta(minutes=5):
            F.append(_finding("signed_before_created", 3, "signature",
                f"Signature #{sg['index']} predates the document's creation date",
                f"Signing time {util.iso(st)} is earlier than CreationDate {util.iso(c_dt)}.",
                {"signing_time": util.iso(st), "creation_date": util.iso(c_dt)}))
        if sg.get("is_certification") and sg.get("docmdp_permission") == 1 and structure["incremental_updates"] > 0:
            F.append(_finding("certified_doc_changed", 3, "signature",
                f"Certified document (signature #{sg['index']}) changed after certification",
                "A DocMDP certification with permission level 1 forbids any later change, but incremental updates "
                "follow it. The certification is broken.", {}))

    if sigs and sig_integrity is None:
        sig_integrity = 1.0 if all(s["covers_whole_file"] or s["superseded_by_later_revision"] for s in sigs) else 0.5

    ev["provenance_confidence"] = round(util.clamp(prov_conf), 3)
    ev["signature_integrity"] = sig_integrity

    # ---- timeline ------------------------------------------------------- #
    tl = ev["timeline"]

    def add(when, label, source, conf="high", note=None):
        tl.append({
            "when": util.iso(when) if isinstance(when, datetime) else when,
            "label": label, "source": source, "confidence": conf, "note": note,
        })

    if c_dt:
        add(c_dt, "Document created", "DocInfo /CreationDate" if docinfo.get("creation_date_raw") else "XMP xmp:CreateDate")
    if x_c and (not c_dt or abs(util.days_between(x_c, c_dt) or 0) > 0.02):
        add(x_c, "Creation time recorded in XMP", "XMP xmp:CreateDate", "medium")
    for h in history:
        lbl = f"XMP history — {h.get('action') or 'event'}"
        if h.get("software_agent"):
            lbl += f" ({h['software_agent']})"
        add(h.get("when"), lbl, "XMP xmpMM:History", "medium")
    for i in range(1, structure["incremental_updates"] + 1):
        add(None, f"Incremental update #{i} appended", "PDF revision structure", "high",
            "Timestamp not recoverable from the revision alone")
    for sg in sigs:
        who = sg.get("signer_subject") or sg.get("name")
        add(sg.get("signing_time"), "Digitally signed" + (f" by {who}" if who else ""),
            f"Signature #{sg['index']} /M", "high" if sg.get("signing_time") else "low")
    if m_dt:
        add(m_dt, "Document last modified", "DocInfo /ModDate" if docinfo.get("mod_date_raw") else "XMP xmp:ModifyDate")
    if x_m and (not m_dt or abs(util.days_between(x_m, m_dt) or 0) > 0.02):
        add(x_m, "Metadata last modified", "XMP xmp:ModifyDate", "medium")

    tl.sort(key=lambda e: (0, e["when"]) if e["when"] else (1, ""))

    ev["_derived"] = {
        "creation_dt": util.iso(c_dt),
        "mod_dt": util.iso(m_dt),
        "creator": creator or None,
        "producer": producer or None,
        "creator_tool": ctool or None,
        "author": docinfo.get("author"),
        "title": docinfo.get("title") or xmp.get("title"),
    }
    return ev
