"""Small shared helpers: hashing, entropy, date parsing."""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timedelta, timezone


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits/byte (0..8)."""
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    ent = 0.0
    for c in freq:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


_PDF_DATE_RE = re.compile(
    r"D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz+\-]?)(\d{2})?'?(\d{2})?'?"
)


def parse_pdf_date(value):
    """Parse a PDF ``D:YYYYMMDDHHmmSS+HH'mm'`` date into an aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _aware(value)
    s = str(value).strip()
    if not s:
        return None
    m = _PDF_DATE_RE.match(s)
    if not m or not m.group(1):
        return parse_iso_date(s)
    y = int(m.group(1))
    mo = int(m.group(2) or 1)
    d = int(m.group(3) or 1)
    hh = int(m.group(4) or 0)
    mm = int(m.group(5) or 0)
    ss = int(m.group(6) or 0)
    sign = m.group(7)
    oh = int(m.group(8) or 0)
    om = int(m.group(9) or 0)
    try:
        dt = datetime(y, mo, d, hh, min(mm, 59), min(ss, 59))
    except ValueError:
        return None
    if sign in ("+", "-"):
        off = timedelta(hours=oh, minutes=om)
        if sign == "-":
            off = -off
        try:
            return dt.replace(tzinfo=timezone(off)).astimezone(timezone.utc)
        except ValueError:
            return dt.replace(tzinfo=timezone.utc)
    return dt.replace(tzinfo=timezone.utc)


def parse_iso_date(s):
    if s is None:
        return None
    if isinstance(s, datetime):
        return _aware(s)
    s = str(s).strip()
    if not s:
        return None
    try:  # dateutil handles the many XMP / ISO-8601 variants
        from dateutil import parser as _p

        return _aware(_p.parse(s))
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return _aware(datetime.strptime(s, fmt))
        except ValueError:
            continue
    return None


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt):
    return dt.isoformat() if isinstance(dt, datetime) else (dt if isinstance(dt, str) else None)


def days_between(a, b):
    """Signed days between two datetimes (a - b), or None."""
    if not isinstance(a, datetime) or not isinstance(b, datetime):
        return None
    return (a - b).total_seconds() / 86400.0


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# PDF tooling that isn't an application a person authors in.
#
# GENERATORS build a PDF from scratch or from HTML — often the legitimate origin of
# a machine-made document (an invoice, a report). Worth noting, not alarming.
_PDF_GENERATORS = (
    "reportlab", "wkhtmltopdf", "weasyprint", "prince", "tcpdf", "mpdf", "dompdf", "fpdf",
    "jspdf", "pdfmake", "pdfkit", "gofpdf", "apache fop", "prawn", "rinohtype", "typst",
    "laravel-dompdf", "playwright", "puppeteer", "chrome headless", "chromium",
)
# MANIPULATORS take an existing PDF and rewrite it — merge, split, stamp, fill, strip,
# linearise. A file last written by one of these has been through an automated step
# that commonly drops author/dates/XMP and can alter page content.
_PDF_MANIPULATORS = (
    "pypdf", "pypdf2", "pdf-lib", "itext", "itextsharp", "pdfbox", "pdfsharp", "pikepdf",
    "qpdf", "mutool", "mupdf", "pymupdf", "ghostscript", "cpdf", "pdftk", "sejda", "hexapdf",
    "ilovepdf", "smallpdf", "pdf24", "aspose", "spire.pdf", "openpdf", "lowagie", "pdfrw",
    "borb", "pdf::api2", "cam::pdf", "unidoc", "unipdf", "pdf-writer", "coherentpdf",
)


def pdf_tool_kind(s: str | None) -> str | None:
    """Classify a producer/creator string: ``"generator"``, ``"manipulator"`` or ``None``."""
    if not s:
        return None
    low = s.lower()
    if any(t in low for t in _PDF_MANIPULATORS):
        return "manipulator"
    if any(t in low for t in _PDF_GENERATORS):
        return "generator"
    return None


def pdf_library_name(s: str | None) -> str | None:
    """Return the library token if ``s`` names any known PDF library/tool, else ``None``."""
    if not s:
        return None
    low = s.lower()
    for tok in (*_PDF_MANIPULATORS, *_PDF_GENERATORS):
        if tok in low:
            return tok
    return None
