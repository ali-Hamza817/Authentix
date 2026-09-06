"""Office Open XML (.docx / .xlsx / .pptx) forensic evidence extraction.

An OOXML file is a ZIP of XML parts. The document's own account of its history
lives in ``docProps/core.xml`` and ``docProps/app.xml``; the ZIP directory itself
records when each part was last written. When those disagree, someone edited the
properties separately from the content.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

from .. import util

SEV_LABEL = {1: "Info", 2: "Low", 3: "Medium", 4: "High"}

_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
}
_EXT = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"

_MAIN_PARTS = ("word/document.xml", "xl/workbook.xml", "ppt/presentation.xml")


def _finding(code, severity, category, title, detail, evidence=None):
    return {
        "code": code, "severity": severity, "severity_label": SEV_LABEL[severity],
        "category": category, "title": title, "detail": detail, "evidence": evidence or {},
    }


def _txt(root, path):
    el = root.find(path, _NS)
    return el.text.strip() if el is not None and el.text else None


def analyze(data: bytes, subtype: str) -> dict:
    ev: dict = {"engine": "ooxml", "subtype": subtype, "findings": [], "timeline": [], "errors": []}
    F = ev["findings"]
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = set(zf.namelist())

    # ---- core.xml (author / dates / revision) -------------------------- #
    core: dict = {}
    if "docProps/core.xml" in names:
        try:
            r = ET.fromstring(zf.read("docProps/core.xml"))
            core = {
                "title": _txt(r, "dc:title"),
                "subject": _txt(r, "dc:subject"),
                "creator": _txt(r, "dc:creator"),
                "last_modified_by": _txt(r, "cp:lastModifiedBy"),
                "revision": _txt(r, "cp:revision"),
                "created": _txt(r, "dcterms:created"),
                "modified": _txt(r, "dcterms:modified"),
                "last_printed": _txt(r, "cp:lastPrinted"),
                "category": _txt(r, "cp:category"),
                "keywords": _txt(r, "cp:keywords"),
            }
        except Exception as e:
            ev["errors"].append({"stage": "core.xml", "error": f"{type(e).__name__}: {e}"})

    # ---- app.xml (application / editing time) -------------------------- #
    app: dict = {}
    if "docProps/app.xml" in names:
        try:
            r = ET.fromstring(zf.read("docProps/app.xml"))

            def a(tag):
                el = r.find(_EXT + tag)
                return el.text.strip() if el is not None and el.text else None

            app = {
                "application": a("Application"),
                "app_version": a("AppVersion"),
                "company": a("Company"),
                "manager": a("Manager"),
                "total_edit_time_min": a("TotalTime"),
                "template": a("Template"),
                "doc_security": a("DocSecurity"),
                "pages": a("Pages"),
                "words": a("Words"),
            }
        except Exception as e:
            ev["errors"].append({"stage": "app.xml", "error": f"{type(e).__name__}: {e}"})

    created = util.parse_iso_date(core.get("created"))
    modified = util.parse_iso_date(core.get("modified"))
    printed = util.parse_iso_date(core.get("last_printed"))
    now = util.now_utc()

    # ---- ZIP part timestamps ------------------------------------------ #
    parts = []
    for zi in zf.infolist():
        try:
            if zi.date_time[0] >= 1980:
                parts.append((zi.filename, datetime(*zi.date_time, tzinfo=timezone.utc)))
        except Exception:
            continue
    part_dates = [d for _, d in parts]
    zmin = min(part_dates) if part_dates else None
    zmax = max(part_dates) if part_dates else None
    core_part = next((d for n, d in parts if n == "docProps/core.xml"), None)
    body_part = next((d for n, d in parts if n in _MAIN_PARTS), None)

    # ---- settings / tracked changes / macros ------------------------- #
    tracked = False
    rsid_sessions = None
    protected = False
    if "word/settings.xml" in names:
        st = zf.read("word/settings.xml").decode("utf-8", "ignore")
        m = re.search(r"<w:trackChanges\b([^>]*)/?>", st)
        tracked = bool(m) and 'w:val="false"' not in (m.group(1) if m else "") and 'w:val="0"' not in (m.group(1) if m else "")
        rsid_sessions = len(re.findall(r"<w:rsid\b", st))
        protected = "<w:documentProtection" in st

    unaccepted = 0
    comments = 0
    for part in ("word/document.xml", "ppt/slides/slide1.xml"):
        if part in names:
            body = zf.read(part).decode("utf-8", "ignore")
            unaccepted += len(re.findall(r"<w:ins\b", body)) + len(re.findall(r"<w:del\b", body))
    if "word/comments.xml" in names:
        comments = len(re.findall(rb"<w:comment\b", zf.read("word/comments.xml")))

    has_macros = any(n.endswith("vbaProject.bin") for n in names)
    external_rels = 0
    for n in names:
        if n.endswith(".rels"):
            external_rels += zf.read(n).count(b'TargetMode="External"')
    embedded_objects = sum(1 for n in names if "/embeddings/" in n or "/oleObject" in n)

    revision = None
    try:
        revision = int((core.get("revision") or "").strip())
    except Exception:
        pass
    edit_min = None
    try:
        edit_min = int((app.get("total_edit_time_min") or "").strip())
    except Exception:
        pass

    # ---- findings --------------------------------------------------- #
    if created and modified and modified < created:
        F.append(_finding("modified_before_created", 4, "temporal",
            "The document was last saved before it was created",
            f"dcterms:modified ({core.get('modified')}) precedes dcterms:created ({core.get('created')}). "
            f"One of the two has been edited.",
            {"created": core.get("created"), "modified": core.get("modified")}))

    if created and (created - now).total_seconds() > 86400:
        F.append(_finding("future_created", 4, "temporal",
            "Creation date is in the future",
            f"dcterms:created is {core.get('created')}, after the moment of analysis.", {}))

    if revision is not None and revision <= 1 and edit_min and edit_min > 15:
        F.append(_finding("revision_editing_time_mismatch", 3, "temporal",
            "Revision count and total editing time disagree",
            f"The document reports {edit_min} minutes of accumulated editing but a revision count of {revision}. "
            f"A file created and saved once should not have that much editing time.",
            {"revision": revision, "total_edit_time_min": edit_min}))

    if core.get("creator") and core.get("last_modified_by") and core["creator"] != core["last_modified_by"]:
        F.append(_finding("author_changed", 2, "provenance",
            "Original author and last editor differ",
            f"Created by “{core['creator']}”, last saved by “{core['last_modified_by']}”. Expected for collaborative "
            f"work; recorded for the provenance trail.",
            {"creator": core["creator"], "last_modified_by": core["last_modified_by"]}))

    if core_part and body_part and (core_part - body_part).total_seconds() > 120:
        F.append(_finding("metadata_edited_separately", 3, "structure",
            "Metadata was written later than the document body",
            f"Inside the package, docProps/core.xml is dated {util.iso(core_part)} while the main content part is "
            f"dated {util.iso(body_part)}. The properties were re-written after the content — the signature of a "
            f"targeted metadata edit.",
            {"core_xml": util.iso(core_part), "content_part": util.iso(body_part)}))

    if zmin and zmax and (zmax - zmin).total_seconds() > 3600 and (revision is None or revision <= 1):
        F.append(_finding("inconsistent_part_timestamps", 2, "structure",
            "Package parts were written at widely different times",
            f"The ZIP parts span {round((zmax - zmin).total_seconds() / 3600, 1)} hours on a document that reports "
            f"one revision.",
            {"span_hours": round((zmax - zmin).total_seconds() / 3600, 1)}))

    if unaccepted:
        F.append(_finding("unaccepted_tracked_changes", 2, "content",
            "Document contains unresolved tracked changes",
            f"{unaccepted} insertion/deletion revision mark(s) remain in the body. Earlier wording may be "
            f"recoverable and the visible text is not the whole story.",
            {"marks": unaccepted}))

    if has_macros:
        F.append(_finding("contains_macros", 4, "structure",
            "Document contains a VBA macro project",
            "word/vbaProject.bin is present. Macros are executable code and the primary infection vector for "
            "Office documents.", {}))

    if external_rels:
        F.append(_finding("external_references", 2, "structure",
            "Document references external resources",
            f"{external_rels} relationship target(s) are external — remote templates, linked images or linked data "
            f"that load from another location when the file is opened.",
            {"count": external_rels}))

    if embedded_objects:
        F.append(_finding("embedded_objects", 1, "structure",
            "Document embeds other files/objects",
            f"{embedded_objects} embedded object(s) found inside the package.", {"count": embedded_objects}))

    if not core.get("creator") and not app.get("application"):
        F.append(_finding("metadata_scrubbed", 3, "provenance",
            "Authoring metadata is missing",
            "Neither an author (dc:creator) nor an application (app:Application) is recorded. The properties have "
            "been stripped.", {}))

    # ---- provenance confidence ----------------------------------- #
    codes = {f["code"] for f in F}
    prov_conf = 1.0
    if "metadata_scrubbed" in codes:
        prov_conf -= 0.4
    if "metadata_edited_separately" in codes:
        prov_conf -= 0.35
    if "revision_editing_time_mismatch" in codes:
        prov_conf -= 0.2
    if "author_changed" in codes:
        prov_conf -= 0.1

    # ---- timeline ---------------------------------------------- #
    tl = ev["timeline"]

    def add(when, label, source, conf="high", note=None):
        tl.append({
            "when": util.iso(when) if isinstance(when, datetime) else when,
            "label": label, "source": source, "confidence": conf, "note": note,
        })

    if created:
        add(created, f"Created by {core.get('creator') or 'unknown author'}", "docProps/core.xml — dcterms:created")
    if zmin and (not created or abs((zmin - created).total_seconds()) > 2):
        add(zmin, "Earliest package part written", "ZIP directory timestamp", "medium")
    if printed:
        add(printed, "Last printed", "docProps/core.xml — cp:lastPrinted", "medium")
    if core_part and body_part and abs((core_part - body_part).total_seconds()) > 2:
        add(body_part, "Document body written", "ZIP directory timestamp", "medium")
        add(core_part, "Document properties written", "ZIP directory timestamp", "medium")
    if modified:
        add(modified, f"Last saved by {core.get('last_modified_by') or 'unknown editor'}",
            "docProps/core.xml — dcterms:modified")
    tl.sort(key=lambda e: (0, e["when"]) if e["when"] else (1, ""))

    ev.update(
        core=core,
        app=app,
        structure={
            "parts": len(parts),
            "zip_part_span_seconds": round((zmax - zmin).total_seconds(), 1) if (zmin and zmax) else None,
            "tracked_changes_on": tracked,
            "rsid_edit_sessions": rsid_sessions,
            "document_protection": protected,
            "unaccepted_revisions": unaccepted,
            "comments": comments,
            "has_macros": has_macros,
            "external_references": external_rels,
            "embedded_objects": embedded_objects,
            "revisions": revision if revision is not None else 1,
            "part_dates": {n: util.iso(d) for n, d in parts},
        },
        provenance_confidence=round(util.clamp(prov_conf), 3),
        signature_integrity=None,
        _derived={
            "creation_dt": util.iso(created),
            "mod_dt": util.iso(modified),
            "creator": core.get("creator"),
            "producer": app.get("application"),
            "creator_tool": app.get("application"),
            "author": core.get("creator"),
            "last_modified_by": core.get("last_modified_by"),
            "title": core.get("title"),
        },
    )
    return ev
