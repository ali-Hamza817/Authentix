"""Authentix command-line interface: ``python -m authentix <file>``."""
from __future__ import annotations

import argparse
import json
import sys

from .analyzer import analyze_path
from .report_html import render_html


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="authentix",
        description="Authentix — digital document authenticity & provenance analyzer",
    )
    ap.add_argument("file", help="path to a PDF or Office (.docx/.xlsx/.pptx) document")
    ap.add_argument("--json", metavar="PATH", help="write the full report as JSON")
    ap.add_argument("--html", metavar="PATH", help="write a standalone HTML report")
    ap.add_argument("--quiet", action="store_true", help="print only the verdict line")
    args = ap.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):  # survive legacy Windows code pages
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    try:
        rep = analyze_path(args.file)
    except FileNotFoundError:
        print(f"authentix: file not found: {args.file}", file=sys.stderr)
        return 1

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2)
    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(render_html(rep))

    s = rep["summary"]
    band = s["band"]
    score = s["credibility_score"]
    colour = {"Credible": "32", "Guarded": "33", "Suspicious": "31", "Untrusted": "31"}.get(band, "0")

    print(_c(f"\n  AUTHENTIX  ·  {rep['file']['name']}", "1"))
    print(f"  {rep['file']['format_detail']}  ·  {rep['file']['size_bytes']:,} bytes")
    print(f"  sha-256 {rep['file']['sha256']}")
    print(f"  {'-' * 66}")
    sc_txt = "n/a" if score is None else f"{score}/100"
    print(_c(f"  Credibility {sc_txt}  —  {band}", colour + ";1"))
    print(f"  {s['verdict']}\n")
    if args.quiet:
        return 0 if band in ("Credible", "Guarded") else 2

    cr, mo = s["created"], s["last_modified"]
    print(_c("  WHO & WHEN", "1"))
    print(f"    Created        {cr['when'] or 'unknown':<32} by {cr['by'] or 'unknown'}")
    print(f"    Creating tool  {cr['tool'] or 'unknown'}")
    print(f"    Last modified  {mo['when'] or 'unknown':<32} by {mo['by'] or 'unknown'}")
    print(f"    Modifying tool {mo['tool'] or 'unknown'}")
    print(f"    Revisions      {s['revisions']}")
    print(f"    Signatures     {s['signature_status']}")
    print(f"    Toolchain      {rep['origin']['toolchain_inference']}")

    g = rep["consistency_graph"]
    print(_c("\n  CONSISTENCY GRAPH", "1"))
    print(f"    {g['contradiction_count']} contradiction(s) / {g['edge_count']} checks   "
          f"(density rho = {g['contradiction_density']}, mean kappa = {g['mean_kappa']})")
    for ed in g["edges"]:
        mark = {"consistent": "  ok ", "weak": " weak", "contradiction": " !!! "}.get(ed["status"], "  ? ")
        tag = {"consistent": "32", "weak": "33", "contradiction": "31"}.get(ed["status"], "0")
        print(_c(f"    [{mark}] {ed['a']} <-> {ed['b']}: {ed['observed']}", tag))

    print(_c("\n  WHAT CHANGED / WHAT LOOKS FORGED", "1"))
    if rep["findings"]:
        for f in rep["findings"]:
            tag = {"High": "31", "Medium": "33", "Low": "36", "Info": "0"}.get(f["severity_label"], "0")
            print(_c(f"    [{f['severity_label']:>6}] {f['title']}", tag))
            print(f"             {f['detail']}")
    else:
        print("    No inconsistencies detected.")

    print(_c("\n  TIMELINE", "1"))
    for e in rep["timeline"]:
        when = e["when"] or "        —        "
        note = f"  ({e['note']})" if e.get("note") else ""
        print(f"    {when}  {e['label']}   [{e['source']}]{note}")

    attr = rep.get("attribution", {})
    dev = attr.get("device", {})
    if attr.get("summary", {}).get("signals") or attr.get("identities"):
        print(_c("\n  ATTRIBUTION & DEVICE TRACES", "1"))
        for i in attr.get("identities", []):
            mark = " (verified)" if i.get("verified") else ""
            print(f"    person   {i['name']}  — {i['role']}{mark}  [{i['source']}]")
        for u in dev.get("usernames", []):
            print(_c(f"    account  {u['value']}   [{u['source']}]", "33"))
        for h in dev.get("machine_names", []):
            print(_c(f"    machine  {h['value']}   [{h['source']}]", "33"))
        for m in dev.get("mac_addresses", []):
            r = " (randomised)" if m["randomized"] else ""
            print(_c(f"    MAC      {m['value']}{r}   [{m['source']}]", "31"))
        for t in dev.get("timezones", []):
            reg = f" — {t['region']}" if t.get("region") else ""
            print(f"    timezone {t['value']}{reg}   [{t['source']}]")
        for c in dev.get("cameras", []):
            print(f"    camera   {c['value']}   [{c['source']}]")
        for g in attr.get("geolocation", {}).get("image_gps", []):
            print(_c(f"    GPS      {g['lat']}, {g['lon']}   [{g['source']}]  {g['maps_url']}", "31"))
        for p in dev.get("local_paths", [])[:6]:
            print(f"    path     {p}")
        for ip in attr.get("network", {}).get("ip_addresses", []):
            print(f"    ip       {ip['value']}   ({ip['note']})")
        print(_c("    note: a document does not store the author's IP address; names are unverified "
                 "unless marked (verified).", "0"))

    if rep["errors"]:
        print(_c("\n  NOTES", "1"))
        for er in rep["errors"]:
            print(f"    {er['stage']}: {er['error']}")

    print()
    return 0 if band in ("Credible", "Guarded") else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
