"""Generate synthetic documents that exercise every Authentix code path.

    python tests/make_samples.py            # writes to ./samples

These are hand-built minimal files: a clean PDF, several tampered PDFs, and a
handful of DOCX files whose metadata contradicts their structure.
"""
from __future__ import annotations

import io
import os
import zipfile

SAMPLES = os.path.join(os.path.dirname(__file__), os.pardir, "samples")


# --------------------------------------------------------------------------- #
# minimal PDF writer
# --------------------------------------------------------------------------- #
def build_pdf(
    creation="D:20240104120000Z",
    mod=None,
    creator="Microsoft Word",
    producer="Microsoft Word",
    author="Jane Doe",
    extra_catalog=b"",
    id0="31313131313131313131313131313131",
    id1=None,
    second_revision_moddate=None,
):
    mod = mod or creation
    id1 = id1 or id0

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R" + extra_catalog + b" >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>",
    ]
    stream = b"BT /F1 12 Tf 72 720 Td (Authentix sample document) Tj ET"
    objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    info = (
        "<< /Title (Authentix Sample) /Author (%s) /Creator (%s) /Producer (%s) "
        "/CreationDate (%s) /ModDate (%s) >>" % (author, creator, producer, creation, mod)
    ).encode("latin-1")
    objs.append(info)  # object 5 == /Info

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"

    xref_pos = len(out)
    n = len(objs) + 1
    out += b"xref\n0 %d\n" % n
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (
        b"trailer\n<< /Size %d /Root 1 0 R /Info 5 0 R /ID [<%s> <%s>] >>\n"
        % (n, id0.encode(), id1.encode())
    )
    out += b"startxref\n%d\n%%%%EOF\n" % xref_pos

    if second_revision_moddate:
        base = bytes(out)
        add = bytearray(b"\n")
        obj_off = len(base) + len(add)
        info2 = (
            "<< /Title (Authentix Sample) /Author (%s) /Creator (%s) /Producer (%s) "
            "/CreationDate (%s) /ModDate (%s) >>"
            % (author, creator, producer, creation, second_revision_moddate)
        ).encode("latin-1")
        add += b"5 0 obj\n" + info2 + b"\nendobj\n"
        xref2 = len(base) + len(add)
        add += b"xref\n5 1\n%010d 00000 n \n" % obj_off
        add += (
            b"trailer\n<< /Size %d /Root 1 0 R /Info 5 0 R /Prev %d /ID [<%s> <%s>] >>\n"
            % (n, xref_pos, id0.encode(), id1.encode())
        )
        add += b"startxref\n%d\n%%%%EOF\n" % xref2
        out = bytearray(base + bytes(add))

    return bytes(out)


def build_signed_then_modified():
    base = build_pdf(creation="D:20240101120000Z", mod="D:20240101120000Z")
    sig = (
        b"\n9 0 obj\n<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /adbe.pkcs7.detached "
        b"/Name (Test Signer) /M (D:20240102120000Z) /ByteRange [0 200 900 100] /Contents <00> >>\nendobj\n"
    )
    tail = b"\n% ---- content appended AFTER the signature was applied ----\n" + b"A" * 600 + b"\n%%EOF\n"
    return base + sig + tail


# --------------------------------------------------------------------------- #
# minimal DOCX writer
# --------------------------------------------------------------------------- #
_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
    "</Types>"
)
_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
    "</Relationships>"
)
_DOCUMENT_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body><w:p><w:r><w:t>Authentix sample document.</w:t></w:r></w:p></w:body></w:document>"
)


def build_docx(
    created="2024-02-01T09:00:00Z",
    modified="2024-02-01T09:20:00Z",
    creator="Jane Doe",
    last_modified_by="Jane Doe",
    application="Microsoft Office Word",
    total_time="12",
    revision="3",
    body_time=(2024, 2, 1, 9, 0, 0),
    core_time=None,
    with_macro=False,
):
    core_time = core_time or body_time
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>Authentix Sample</dc:title><dc:creator>{creator}</dc:creator>"
        f"<cp:lastModifiedBy>{last_modified_by}</cp:lastModifiedBy><cp:revision>{revision}</cp:revision>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified>'
        "</cp:coreProperties>"
    )
    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        f"<Application>{application}</Application><AppVersion>16.0000</AppVersion>"
        f"<TotalTime>{total_time}</TotalTime><Company>Example Corp</Company><Pages>1</Pages><Words>4</Words>"
        "</Properties>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        def w(name, data, when):
            zi = zipfile.ZipInfo(name, date_time=when)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)

        w("[Content_Types].xml", _CONTENT_TYPES, body_time)
        w("_rels/.rels", _ROOT_RELS, body_time)
        w("word/document.xml", _DOCUMENT_XML, body_time)
        w("docProps/app.xml", app_xml, body_time)
        w("docProps/core.xml", core_xml, core_time)
        if with_macro:
            w("word/vbaProject.bin", b"\x00VBA\x00stub", body_time)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
SAMPLE_SET = {
    # a coherent document: dates equal, one tool, single revision, matching ID
    "clean.pdf": lambda: build_pdf(
        creation="D:20240104120000Z", mod="D:20240104120000Z",
        creator="Microsoft Word", producer="Microsoft Word",
    ),
    # backdated: ModDate 7 years after CreationDate, no revisions, changed ID,
    # authored-in-Word but produced-by-Adobe with no history bridge
    "tampered_dates.pdf": lambda: build_pdf(
        creation="D:20190104120000Z", mod="D:20260904120000Z",
        creator="Microsoft Word", producer="Adobe PDF Library 15.0",
        id0="31313131313131313131313131313131",
        id1="99999999999999999999999999999999",
    ),
    # future creation date
    "future_dated.pdf": lambda: build_pdf(
        creation="D:20990101000000Z", mod="D:20990101000000Z",
    ),
    # genuine incremental update -> two revisions
    "incremental.pdf": lambda: build_pdf(
        creation="D:20240104120000Z", mod="D:20240104120000Z",
        second_revision_moddate="D:20260101120000Z",
    ),
    # active content: OpenAction runs JavaScript on open
    "active_content.pdf": lambda: build_pdf(
        creation="D:20240104120000Z",
        extra_catalog=b" /OpenAction << /S /JavaScript /JS (app.alert\\(1\\)) >>",
    ),
    # content appended after a signature
    "signed_then_modified.pdf": build_signed_then_modified,
    # ---- DOCX ----
    "clean.docx": lambda: build_docx(),
    "docx_modified_before_created.docx": lambda: build_docx(
        created="2024-05-10T10:00:00Z", modified="2024-05-09T18:00:00Z",
    ),
    "docx_metadata_edited_later.docx": lambda: build_docx(
        created="2024-03-01T09:00:00Z", modified="2024-03-01T09:05:00Z",
        revision="1", total_time="1",
        body_time=(2024, 3, 1, 9, 0, 0), core_time=(2024, 3, 1, 15, 30, 0),
    ),
    "docx_revision_time_mismatch.docx": lambda: build_docx(
        revision="1", total_time="240",
    ),
    "docx_with_macro.docx": lambda: build_docx(with_macro=True),
}


def main():
    os.makedirs(SAMPLES, exist_ok=True)
    for name, factory in SAMPLE_SET.items():
        path = os.path.join(SAMPLES, name)
        with open(path, "wb") as fh:
            fh.write(factory())
        print(f"  wrote {os.path.relpath(path)}  ({os.path.getsize(path):,} bytes)")


if __name__ == "__main__":
    main()
