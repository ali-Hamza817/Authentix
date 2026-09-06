"""File intake: identify the format and compute file-level identifiers."""
from __future__ import annotations

import io
import zipfile
from dataclasses import asdict, dataclass

from . import util


@dataclass
class Intake:
    filename: str
    size: int
    sha256: str
    md5: str
    fmt: str          # pdf | docx | xlsx | pptx | ooxml | ole | rtf | zip | unknown
    fmt_detail: str

    def as_dict(self) -> dict:
        return asdict(self)


def detect(data: bytes, filename: str = "") -> tuple[str, str]:
    if data[:5] == b"%PDF-":
        ver = data[5:8].decode("latin-1", "ignore").strip()
        return "pdf", f"PDF {ver}"
    if data[:4] == b"PK\x03\x04":
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
            names = set(zf.namelist())
            if any(n.startswith("word/") for n in names):
                return "docx", "Office Open XML — WordprocessingML (.docx)"
            if any(n.startswith("xl/") for n in names):
                return "xlsx", "Office Open XML — SpreadsheetML (.xlsx)"
            if any(n.startswith("ppt/") for n in names):
                return "pptx", "Office Open XML — PresentationML (.pptx)"
            if "[Content_Types].xml" in names:
                return "ooxml", "Office Open XML — unknown part layout"
            return "zip", "ZIP archive"
        except Exception:
            return "zip", "ZIP archive (unreadable)"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "ole", "Legacy OLE2 compound document (.doc / .xls / .ppt)"
    if data[:5] == b"{\\rtf":
        return "rtf", "Rich Text Format"
    return "unknown", "Unrecognised format"


def build_intake(data: bytes, filename: str = "") -> Intake:
    fmt, detail = detect(data, filename)
    return Intake(
        filename=filename or "document",
        size=len(data),
        sha256=util.sha256_hex(data),
        md5=util.md5_hex(data),
        fmt=fmt,
        fmt_detail=detail,
    )
