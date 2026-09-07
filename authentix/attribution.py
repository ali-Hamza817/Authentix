"""Attribution & device traces.

What a file leaks about *who* and *what* produced it:

* named identities (author, last editor, comment authors, and — the only
  cryptographically verified one — a digital-signature subject);
* an embedded Windows **username** or **machine / UNC host** from leaked file paths;
* a hardware **MAC address** recoverable from a version-1 UUID the tool generated;
* the **timezone** the creating machine was set to;
* **printer** names;
* **GPS coordinates** and **camera make/model** from EXIF inside embedded photos;
* e-mail addresses and external URLs referenced by the file.

A document does **not** contain the author's public IP address — there is no field
for it and no tool writes one. Everything here is only present when the creating
software happened to leave it, and names are self-reported unless marked verified.
"""
from __future__ import annotations

import re
import struct
import zipfile
from io import BytesIO

_SEV = {1: "Info", 2: "Low", 3: "Medium", 4: "High"}

_UUID_RE = re.compile(
    rb"([0-9a-fA-F]{8})-([0-9a-fA-F]{4})-([0-9a-fA-F])([0-9a-fA-F]{3})-"
    rb"([0-9a-fA-F]{4})-([0-9a-fA-F]{12})"
)
_USERS_RE = re.compile(r"[\\/]Users[\\/]([^\\/\r\n\"'<>|]{1,40})[\\/]", re.I)
_DOCSET_RE = re.compile(r"Documents and Settings[\\/]([^\\/\r\n\"'<>|]{1,40})[\\/]", re.I)
_NIX_USER_RE = re.compile(r"/home/([A-Za-z0-9._-]{2,32})/")
_WIN_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]{1,60}\\){0,10}[^\\/:*?\"<>|\r\n]{0,60}")
_UNC_RE = re.compile(r"\\\\([A-Za-z0-9._$-]{2,40})\\([A-Za-z0-9._$ %+\-()]{1,60})")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{2,60}\.[A-Za-z]{2,24}")
_IPV4_RE = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")
_URL_RE = re.compile(r"(?:https?|ftp|file|smb|afp)://[^\s\"'<>)\]}]{4,240}")
_PDF_DATE_TZ = re.compile(rb"D:\d{14}([Zz]|[+\-]\d{2}'?\d{2}'?)")
_ISO_TZ = re.compile(rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?([Zz]|[+\-]\d{2}:\d{2})")

# Windows path fragments that are almost always benign (fonts, system libs).
_PATH_NOISE = re.compile(r"\\Windows\\Fonts\\|\\Program Files|\\System32\\|/System/Library/", re.I)

_TZ_REGION = {
    "UTC-08:00": "US/Canada Pacific",
    "UTC-07:00": "US/Canada Mountain",
    "UTC-06:00": "US/Canada Central, Central America",
    "UTC-05:00": "US/Canada Eastern, Colombia, Peru",
    "UTC-03:00": "Argentina, Brazil (east), Greenland",
    "UTC+00:00": "UK, Portugal, Iceland, West Africa",
    "UTC+01:00": "Central Europe, West/Central Africa",
    "UTC+02:00": "Eastern Europe, Egypt, South Africa, Israel",
    "UTC+03:00": "Moscow, Turkey, East Africa, Arabia",
    "UTC+03:30": "Iran",
    "UTC+04:00": "UAE, Azerbaijan, Georgia",
    "UTC+05:00": "Pakistan, Uzbekistan, Yekaterinburg",
    "UTC+05:30": "India, Sri Lanka",
    "UTC+05:45": "Nepal",
    "UTC+06:00": "Bangladesh, Bhutan, Omsk",
    "UTC+07:00": "Thailand, Vietnam, Indonesia (west)",
    "UTC+08:00": "China, Singapore, Malaysia, Philippines, Western Australia",
    "UTC+09:00": "Japan, Korea",
    "UTC+09:30": "Central Australia",
    "UTC+10:00": "Eastern Australia, Papua New Guinea",
    "UTC+12:00": "New Zealand, Fiji",
}

_NOTES = [
    "A document does not record the author's public IP address — there is no field for it in PDF or "
    "Office formats, and no tool writes one. Anything below is a trace the creating software left behind.",
    "Names are self-reported and unverified unless marked verified (they come from a digital-signature "
    "certificate).",
    "A timezone or an embedded-photo location points to a region, not a person.",
]


def _norm_tz(raw: str) -> str:
    raw = raw.replace("'", "")
    if raw in ("Z", "z"):
        return "UTC+00:00"
    sign = raw[0]
    digits = raw[1:].replace(":", "")
    return f"UTC{sign}{digits[:2]}:{digits[2:4]}"


# --------------------------------------------------------------------------- #
# EXIF (minimal, GPS + camera identity only)
# --------------------------------------------------------------------------- #
def _rational(buf, off, order):
    num = struct.unpack(order + "I", buf[off : off + 4])[0]
    den = struct.unpack(order + "I", buf[off + 4 : off + 8])[0]
    return num / den if den else 0.0


def _read_ifd(buf, ifd_off, order):
    entries = {}
    count = struct.unpack(order + "H", buf[ifd_off : ifd_off + 2])[0]
    for i in range(count):
        e = ifd_off + 2 + i * 12
        tag, typ, cnt = struct.unpack(order + "HHI", buf[e : e + 8])
        val_off = e + 8
        entries[tag] = (typ, cnt, val_off)
    return entries


def _ascii_val(buf, order, entry):
    typ, cnt, val_off = entry
    if typ != 2:
        return None
    if cnt <= 4:
        raw = buf[val_off : val_off + cnt]
    else:
        ptr = struct.unpack(order + "I", buf[val_off : val_off + 4])[0]
        raw = buf[ptr : ptr + cnt]
    return raw.split(b"\x00", 1)[0].decode("latin-1", "ignore").strip() or None


def _tiff_exif(tiff: bytes):
    try:
        order = "<" if tiff[:2] == b"II" else ">"
        if struct.unpack(order + "H", tiff[2:4])[0] != 42:
            return None
        ifd0_off = struct.unpack(order + "I", tiff[4:8])[0]
        ifd0 = _read_ifd(tiff, ifd0_off, order)
        out = {}
        for tag, key in ((0x010F, "make"), (0x0110, "model"), (0x0131, "software"), (0x013B, "artist")):
            if tag in ifd0:
                v = _ascii_val(tiff, order, ifd0[tag])
                if v:
                    out[key] = v
        if 0x8825 in ifd0:
            gps_ptr = struct.unpack(order + "I", tiff[ifd0[0x8825][2] : ifd0[0x8825][2] + 4])[0]
            gps = _read_ifd(tiff, gps_ptr, order)

            def coord(ref_tag, val_tag):
                if val_tag not in gps or ref_tag not in gps:
                    return None
                ref = _ascii_val(tiff, order, gps[ref_tag]) or ""
                typ, cnt, voff = gps[val_tag]
                ptr = struct.unpack(order + "I", tiff[voff : voff + 4])[0]
                d = _rational(tiff, ptr, order)
                m = _rational(tiff, ptr + 8, order)
                s = _rational(tiff, ptr + 16, order)
                dec = d + m / 60 + s / 3600
                if ref.upper() in ("S", "W"):
                    dec = -dec
                return round(dec, 6)

            lat = coord(1, 2)
            lon = coord(3, 4)
            if lat is not None and lon is not None and (lat or lon):
                out["lat"] = lat
                out["lon"] = lon
        return out or None
    except Exception:
        return None


def _exif_from_jpeg(jpeg: bytes):
    try:
        if jpeg[:3] != b"\xff\xd8\xff":
            return None
        i, n = 2, len(jpeg)
        while i + 4 <= n and jpeg[i] == 0xFF:
            marker = jpeg[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            if marker in (0xDA, 0xD9):
                break
            seglen = struct.unpack(">H", jpeg[i + 2 : i + 4])[0]
            seg = jpeg[i + 4 : i + 2 + seglen]
            if marker == 0xE1 and seg[:6] == b"Exif\x00\x00":
                return _tiff_exif(seg[6:])
            i += 2 + seglen
    except Exception:
        return None
    return None


def _collect_jpegs(data: bytes, fmt: str):
    jpegs = []
    if fmt in ("docx", "xlsx", "pptx", "ooxml"):
        try:
            zf = zipfile.ZipFile(BytesIO(data))
            for name in zf.namelist():
                if "media/" in name and name.lower().endswith((".jpg", ".jpeg")):
                    jpegs.append((name, zf.read(name)))
                    if len(jpegs) >= 8:
                        break
        except Exception:
            pass
    else:  # pdf / anything — scan raw for embedded JPEG streams
        for m in re.finditer(rb"\xff\xd8\xff", data):
            start = m.start()
            end = data.find(b"\xff\xd9", start)
            if end == -1:
                continue
            blob = data[start : end + 2]
            if 128 < len(blob) <= 6_000_000:
                jpegs.append((f"embedded image @ offset {start}", blob))
            if len(jpegs) >= 8:
                break
    return jpegs


def _corpus(data: bytes, fmt: str) -> tuple[str, bytes]:
    """A searchable (text, bytes) view of the file — OOXML parts are decompressed first."""
    if fmt in ("docx", "xlsx", "pptx", "ooxml"):
        try:
            zf = zipfile.ZipFile(BytesIO(data))
            chunks = []
            for name in zf.namelist():
                low = name.lower()
                if low.endswith((".xml", ".rels", ".txt", ".vml")) or "printersettings" in low or "custom" in low:
                    try:
                        chunks.append(zf.read(name))
                    except Exception:
                        pass
            if chunks:
                blob = b"\n".join(chunks)
                return blob.decode("latin-1", "ignore"), blob
        except Exception:
            pass
    return data.decode("latin-1", "ignore"), data


# --------------------------------------------------------------------------- #
def extract(data: bytes, ev: dict, fmt: str) -> dict:
    text, blob = _corpus(data, fmt)
    d = ev.get("_derived", {})

    identities: list[dict] = []
    seen_id = set()

    def add_id(name, role, source, verified=False, email=None):
        name = (name or "").strip()
        if not name or len(name) > 120:
            return
        key = (name.lower(), role)
        if key in seen_id:
            return
        seen_id.add(key)
        identities.append({
            "name": name, "role": role, "source": source, "verified": verified, "email": email,
            "label": "verified" if verified else "self-reported",
        })

    add_id(d.get("author"), "author", "document metadata")
    add_id(d.get("last_modified_by"), "last editor", "document metadata")
    add_id((ev.get("app") or {}).get("company"), "organisation", "app.xml Company")
    add_id((ev.get("app") or {}).get("manager"), "manager", "app.xml Manager")
    for h in (ev.get("xmp") or {}).get("history", []) or []:
        if h.get("software_agent"):
            pass  # software, not a person
    for sig in ev.get("signatures", []) or []:
        subj = sig.get("signer_subject")
        if subj:
            add_id(subj, "digital signer", f"signature #{sig.get('index')} certificate", verified=True)
        if sig.get("name") and sig.get("name") != subj:
            add_id(sig["name"], "declared signer", f"signature #{sig.get('index')} /Name")
    # comment / revision authors (OOXML)
    for m in re.finditer(r'w:author="([^"]{1,80})"', text):
        add_id(m.group(1), "comment / revision author", "word/comments.xml")
    # .doc last-authors list is OLE-encoded; skip for v1

    # ---- device traces ------------------------------------------------- #
    usernames: dict[str, str] = {}
    machines: dict[str, str] = {}
    local_paths: set[str] = set()
    printers: dict[str, str] = {}

    for m in _USERS_RE.finditer(text):
        u = m.group(1)
        if u.lower() not in ("public", "default", "default user", "all users"):
            usernames.setdefault(u, "embedded path  …\\Users\\%s\\…" % u)
    for m in _DOCSET_RE.finditer(text):
        usernames.setdefault(m.group(1), "embedded path  …\\Documents and Settings\\%s\\…" % m.group(1))
    for m in _NIX_USER_RE.finditer(text):
        usernames.setdefault(m.group(1), "embedded path  /home/%s/" % m.group(1))
    for m in _WIN_PATH_RE.finditer(text):
        p = m.group(0)
        if len(p) > 8 and not _PATH_NOISE.search(p):
            local_paths.add(p.strip())
    for m in _UNC_RE.finditer(text):
        host, share = m.group(1), m.group(2)
        if host.lower() not in ("localhost", "?", "."):
            low = share.lower()
            if any(t in low for t in ("print", "hp", "canon", "epson", "xerox", "ricoh", "brother", "kyocera")):
                printers.setdefault(f"\\\\{host}\\{share}", "UNC printer share")
            else:
                machines.setdefault(host, f"UNC path  \\\\{host}\\{share}")
    for m in re.finditer(r"<w:printerSettings[^>]*/>|printerSettings\d*\.bin", text):
        printers.setdefault("(binary printer settings present)", "word/printerSettings")

    # MAC address from version-1 UUIDs
    macs: dict[str, dict] = {}
    for m in _UUID_RE.finditer(blob):
        if m.group(3).lower() != b"1":
            continue
        node = m.group(6).decode("ascii").lower()
        mac = ":".join(node[i : i + 2] for i in range(0, 12, 2))
        first = int(node[0:2], 16)
        macs.setdefault(
            mac,
            {
                "value": mac,
                "randomized": bool(first & 0x01),
                "source": "version-1 UUID embedded by the authoring tool",
            },
        )

    # timezones
    tz_hits: dict[str, str] = {}
    for m in _PDF_DATE_TZ.finditer(blob):
        tz_hits.setdefault(_norm_tz(m.group(1).decode("ascii")), "PDF date offset")
    for m in _ISO_TZ.finditer(blob):
        tz_hits.setdefault(_norm_tz(m.group(1).decode("ascii")), "ISO-8601 timestamp offset")

    software = []
    for s, src in (
        (d.get("creator_tool"), "XMP CreatorTool"),
        (d.get("producer"), "PDF /Producer"),
        ((ev.get("app") or {}).get("application"), "app.xml Application"),
    ):
        if s and s not in [x["value"] for x in software]:
            software.append({"value": s, "source": src})
    for h in (ev.get("xmp") or {}).get("history", []) or []:
        if h.get("software_agent") and h["software_agent"] not in [x["value"] for x in software]:
            software.append({"value": h["software_agent"], "source": "XMP history"})

    locales = sorted({m.group(1) for m in re.finditer(r'w:(?:lang|val)="([a-z]{2}-[A-Z]{2})"', text)})

    # ---- network / contact ------------------------------------------- #
    emails = sorted({e for e in _EMAIL_RE.findall(text) if not e.endswith((".png", ".jpg", ".gif"))})[:20]
    urls = sorted(set(_URL_RE.findall(text)))[:20]
    ext_urls = [u for u in urls if not u.startswith(("http://ns.adobe", "http://www.w3.org", "http://purl.org",
                                                     "http://schemas.", "https://schemas.", "http://www.aiim"))]
    ips = []
    for ip in sorted(set(_IPV4_RE.findall(text)))[:20]:
        if ip.startswith(("0.", "255.")) or ip == "127.0.0.1":
            continue
        ips.append({"value": ip, "source": "referenced in the file (URL / path / config)",
                    "note": "a server, proxy or scanner address — not the author's computer"})

    # ---- embedded-photo EXIF --------------------------------------- #
    image_gps = []
    cameras = []
    for name, jpeg in _collect_jpegs(data, fmt):
        ex = _exif_from_jpeg(jpeg)
        if not ex:
            continue
        if "model" in ex or "make" in ex:
            cam = " ".join(x for x in (ex.get("make"), ex.get("model")) if x)
            if cam and cam not in [c["value"] for c in cameras]:
                cameras.append({"value": cam, "software": ex.get("software"), "artist": ex.get("artist"),
                                "source": name})
        if "lat" in ex:
            image_gps.append({
                "lat": ex["lat"], "lon": ex["lon"], "source": name, "confidence": "medium",
                "interpretation": "where an embedded photo was taken — not necessarily where the document was made",
                "maps_url": f"https://www.openstreetmap.org/?mlat={ex['lat']}&mlon={ex['lon']}#map=15/{ex['lat']}/{ex['lon']}",
            })

    device = {
        "usernames": [
            {"value": k, "source": v, "confidence": "medium",
             "interpretation": "an account on a machine that touched the file — may be an editor, not the author"}
            for k, v in usernames.items()
        ],
        "machine_names": [
            {"value": k, "source": v, "confidence": "medium",
             "interpretation": "a host referenced by the file — could be a file server, not the author's PC"}
            for k, v in machines.items()
        ],
        "mac_addresses": [
            {**m, "confidence": "low" if m["randomized"] else "medium",
             "interpretation": "possible originating-device network-card artefact; may be a VM/spoofed/shared NIC"}
            for m in macs.values()
        ],
        "printers": [{"value": k, "source": v, "confidence": "medium"} for k, v in printers.items()],
        "timezones": [
            {"value": k, "region": _TZ_REGION.get(k), "source": v, "confidence": "low",
             "interpretation": "region hint from the creating machine's clock offset — not an identity"}
            for k, v in sorted(tz_hits.items())
        ],
        "software": software,
        "locales": locales,
        "local_paths": sorted(local_paths)[:25],
        "cameras": [{**c, "confidence": "medium",
                     "interpretation": "the device that took an embedded photo — not necessarily the document's"}
                    for c in cameras],
    }
    network = {"ip_addresses": ips, "emails": emails, "external_urls": ext_urls}
    geolocation = {
        "image_gps": image_gps,
        "timezone_region": (
            "; ".join(f"{t['value']} ({t['region']})" for t in device["timezones"] if t.get("region"))
            or None
        ),
    }

    signals = (
        len(device["usernames"]) + len(device["machine_names"]) + len(device["mac_addresses"])
        + len(device["printers"]) + len(image_gps) + len(cameras)
    )
    strong = bool(device["usernames"] or device["machine_names"] or device["mac_addresses"] or image_gps)

    findings = []
    if device["usernames"]:
        findings.append(_f("username_disclosed", 2, "privacy",
            "A user account name is embedded in this document",
            "The account name(s) " + ", ".join(f"“{u['value']}”" for u in device["usernames"])
            + " appear in file paths stored inside the document. This identifies the user account on the "
            "machine the file was made or edited on."))
    if device["machine_names"]:
        findings.append(_f("machine_name_disclosed", 2, "privacy",
            "A computer / server name is embedded in this document",
            "Host name(s) " + ", ".join(f"“{h['value']}”" for h in device["machine_names"])
            + " appear in UNC paths inside the document."))
    if device["mac_addresses"]:
        real = [m for m in device["mac_addresses"] if not m["randomized"]]
        findings.append(_f("mac_address_disclosed", 3 if real else 2, "privacy",
            "A hardware MAC address is recoverable from this document",
            "The authoring tool generated a version-1 UUID, whose last 48 bits are the network-card address "
            + ", ".join(f"“{m['value']}”" + (" (randomised)" if m["randomized"] else "") for m in device["mac_addresses"])
            + ". A non-randomised value uniquely identifies the network interface of the creating machine."))
    if image_gps:
        findings.append(_f("gps_in_embedded_image", 3, "privacy",
            "An embedded image carries GPS coordinates",
            "; ".join(f"{g['lat']}, {g['lon']} ({g['source']})" for g in image_gps)
            + ". The location where an embedded photo was taken is exposed."))
    if device["cameras"]:
        findings.append(_f("camera_model_disclosed", 1, "privacy",
            "An embedded image identifies the camera / phone that took it",
            ", ".join(f"“{c['value']}”" for c in device["cameras"]) + "."))
    if device["local_paths"] and not device["usernames"]:
        findings.append(_f("local_path_disclosed", 1, "privacy",
            "Local file paths are embedded in this document",
            f"{len(device['local_paths'])} absolute path(s) from the creating machine are stored in the file."))

    return {
        "block": {
            "summary": {
                "people": sorted({i["name"] for i in identities}),
                "verified_people": sorted({i["name"] for i in identities if i["verified"]}),
                "has_device_traces": strong,
                "signals": signals,
            },
            "identities": identities,
            "device": device,
            "network": network,
            "geolocation": geolocation,
            "notes": _NOTES,
        },
        "findings": findings,
    }


def _f(code, sev, cat, title, detail):
    return {"code": code, "severity": sev, "severity_label": _SEV[sev],
            "category": cat, "title": title, "detail": detail, "evidence": {}}
