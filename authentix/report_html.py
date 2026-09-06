"""Render an Authentix report as a standalone, self-contained HTML file (CLI --html)."""
from __future__ import annotations

import html
import json

_BAND_COLOR = {
    "Credible": "#3B7A4E",
    "Guarded": "#A9772A",
    "Suspicious": "#BE5C2B",
    "Untrusted": "#A23333",
    "Unknown": "#585B5E",
}
_SEV_COLOR = {"High": "#A23333", "Medium": "#BE5C2B", "Low": "#1F5C79", "Info": "#585B5E"}


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def render_html(rep: dict) -> str:
    s = rep["summary"]
    band = s.get("band", "Unknown")
    bc = _BAND_COLOR.get(band, "#585B5E")
    score = s.get("credibility_score")
    score_txt = "n/a" if score is None else str(score)
    needle = 0 if score is None else max(0, min(100, score))

    cr, mo = s["created"], s["last_modified"]
    g = rep["consistency_graph"]

    findings_html = "".join(
        f"""<div class="finding">
              <div class="fhead"><span class="sev" style="background:{_SEV_COLOR.get(f['severity_label'], '#585B5E')}">{_e(f['severity_label'])}</span>
              <span class="ftitle">{_e(f['title'])}</span><span class="fcat">{_e(f['category'])}</span></div>
              <p>{_e(f['detail'])}</p>
            </div>"""
        for f in rep["findings"]
    ) or '<p class="ok">No inconsistencies detected.</p>'

    timeline_html = "".join(
        f"""<li><span class="tw">{_e(e['when'] or '—')}</span>
             <span class="tl">{_e(e['label'])}</span>
             <span class="ts">{_e(e['source'])}{' · ' + _e(e['note']) if e.get('note') else ''}</span></li>"""
        for e in rep["timeline"]
    ) or "<li>No datable events recovered.</li>"

    edges_html = "".join(
        f"""<tr class="st-{_e(ed['status'])}">
              <td>{_e(ed['a'])} &harr; {_e(ed['b'])}</td>
              <td>{_e(ed['relation'])}</td>
              <td>{_e(ed['observed'])}</td>
              <td><span class="pill p-{_e(ed['status'])}">{_e(ed['status'])}</span></td>
              <td class="num">{ed['kappa']:.2f}</td>
            </tr>"""
        for ed in g["edges"]
    ) or '<tr><td colspan="5">No expectation edges were applicable.</td></tr>'

    sig_html = ""
    for sig in rep.get("signatures", []):
        sig_html += f"""<div class="sig">
            <b>Signature #{_e(sig.get('index'))}</b> — {_e(sig.get('sub_filter') or 'unknown filter')}<br>
            Signer: {_e(sig.get('signer_subject') or sig.get('name') or 'unknown')}<br>
            Issuer: {_e(sig.get('signer_issuer') or 'n/a')}{' · self-signed' if sig.get('self_signed') else ''}<br>
            Signing time: {_e(sig.get('signing_time') or 'not stated')}<br>
            Coverage: {'whole file' if sig.get('covers_whole_file') else _e(str(sig.get('bytes_after_signature')) + ' bytes after signed range')}
            &nbsp;→&nbsp; <b>{_e(sig.get('integrity'))}</b>
          </div>"""
    if not sig_html:
        sig_html = '<p class="ok">Document is not digitally signed.</p>'

    comp = rep["ewdca"].get("components", {})
    comp_html = "".join(
        f'<div class="cmp"><span>{_e(k)}</span><b>{v}</b></div>' for k, v in comp.items()
    )

    origin = rep["origin"]

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Authentix report — {_e(rep['file']['name'])}</title>
<style>
  :root {{ --ink:#1A1C1E; --soft:#585B5E; --paper:#F3F1EA; --card:#FBFAF5; --rule:#D7D2C4; --accent:#1F5C79; --band:{bc}; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
         font:16px/1.6 "Source Serif 4",Georgia,serif; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:32px 20px 80px; }}
  h1 {{ font:700 1.1rem/1.2 "IBM Plex Mono",ui-monospace,monospace; letter-spacing:.04em; margin:0 0 4px; }}
  .muted {{ color:var(--soft); font:0.8rem/1.5 "IBM Plex Mono",monospace; word-break:break-all; }}
  .score {{ display:flex; gap:20px; align-items:center; background:var(--card); border:1px solid var(--rule);
            border-left:5px solid var(--band); padding:20px; margin:20px 0; border-radius:8px; }}
  .score .n {{ font:800 3rem/1 "IBM Plex Mono",monospace; }}
  .score .b {{ font:700 .8rem/1 "IBM Plex Mono",monospace; letter-spacing:.12em; text-transform:uppercase; color:var(--band); }}
  .meter {{ height:12px; border-radius:6px; overflow:hidden; display:flex; margin:8px 0 3px; }}
  .meter i {{ flex:1; display:block; }}
  .meter .z1{{background:#A23333}} .meter .z2{{background:#BE5C2B}} .meter .z3{{background:#A9772A}} .meter .z4{{background:#3B7A4E}}
  .mwrap {{ position:relative; }}
  .needle {{ position:absolute; top:-4px; width:2px; height:20px; background:var(--ink); left:{needle}%; }}
  h2 {{ font:700 .75rem/1 "IBM Plex Mono",monospace; letter-spacing:.16em; text-transform:uppercase;
        color:var(--accent); border-bottom:1px solid var(--rule); padding-bottom:6px; margin:34px 0 14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1px; background:var(--rule);
           border:1px solid var(--rule); border-radius:8px; overflow:hidden; }}
  .grid > div {{ background:var(--card); padding:12px 14px; }}
  .grid dt {{ font:0.66rem/1.4 "IBM Plex Mono",monospace; letter-spacing:.1em; text-transform:uppercase; color:var(--soft); }}
  .grid dd {{ margin:3px 0 0; }}
  .finding {{ background:var(--card); border:1px solid var(--rule); border-radius:8px; padding:12px 14px; margin:8px 0; }}
  .fhead {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
  .sev {{ color:#fff; font:600 .62rem/1 "IBM Plex Mono",monospace; letter-spacing:.08em; padding:4px 6px; border-radius:4px; text-transform:uppercase; }}
  .ftitle {{ font-weight:600; }}
  .fcat {{ color:var(--soft); font:0.7rem "IBM Plex Mono",monospace; margin-left:auto; }}
  .finding p {{ margin:6px 0 0; font-size:.92rem; }}
  ul.tl {{ list-style:none; padding:0; margin:0; }}
  ul.tl li {{ display:grid; grid-template-columns:190px 1fr; gap:4px 14px; padding:8px 0; border-bottom:1px solid var(--rule); }}
  ul.tl .tw {{ font:0.78rem "IBM Plex Mono",monospace; color:var(--soft); }}
  ul.tl .ts {{ grid-column:2; font:0.72rem "IBM Plex Mono",monospace; color:var(--soft); }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--rule); border-radius:8px; overflow:hidden; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--rule); font-size:.85rem; vertical-align:top; }}
  th {{ font:600 .62rem/1 "IBM Plex Mono",monospace; letter-spacing:.1em; text-transform:uppercase; color:var(--soft); }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .pill {{ font:600 .62rem/1 "IBM Plex Mono",monospace; padding:3px 6px; border-radius:4px; text-transform:uppercase; }}
  .p-consistent {{ background:#e2ede4; color:#3B7A4E; }}
  .p-weak {{ background:#f6e9d8; color:#A9772A; }}
  .p-contradiction {{ background:#f3dede; color:#A23333; }}
  .sig {{ background:var(--card); border:1px solid var(--rule); border-radius:8px; padding:12px 14px; margin:8px 0; font-size:.9rem; }}
  .cmp {{ display:inline-flex; gap:8px; align-items:baseline; background:var(--card); border:1px solid var(--rule);
          border-radius:6px; padding:6px 10px; margin:3px 6px 3px 0; font:0.78rem "IBM Plex Mono",monospace; }}
  .ok {{ color:#3B7A4E; }}
  details {{ margin-top:10px; }} summary {{ cursor:pointer; font:0.8rem "IBM Plex Mono",monospace; color:var(--accent); }}
  pre {{ background:#12333f; color:#dfeef4; padding:14px; border-radius:8px; overflow:auto; font-size:.72rem; line-height:1.5; }}
  .foot {{ margin-top:40px; color:var(--soft); font:0.72rem "IBM Plex Mono",monospace; }}
</style></head><body><div class="wrap">

<h1>AUTHENTIX · DOCUMENT AUTHENTICITY REPORT</h1>
<div class="muted">{_e(rep['file']['name'])} &nbsp;·&nbsp; {_e(rep['file']['format_detail'])} &nbsp;·&nbsp; {rep['file']['size_bytes']:,} bytes<br>
sha-256 {_e(rep['file']['sha256'])}<br>analysed {_e(rep['analyzed_at'])} · Authentix {_e(rep['version'])}</div>

<div class="score">
  <div class="n">{score_txt}<span style="font-size:1rem;color:var(--soft)"> / 100</span></div>
  <div>
    <div class="b">{_e(band)}</div>
    <div class="mwrap" style="width:260px">
      <div class="meter"><i class="z1"></i><i class="z2"></i><i class="z3"></i><i class="z4"></i></div>
      <div class="needle"></div>
    </div>
    <div class="muted">0 · untrusted &nbsp;&nbsp;&nbsp; 100 · credible</div>
  </div>
  <p style="margin:0;flex:1;min-width:220px">{_e(s['verdict'])}</p>
</div>

<h2>Who &amp; when</h2>
<div class="grid">
  <div><dt>Created</dt><dd>{_e(cr['when'] or 'unknown')}</dd></div>
  <div><dt>Created by</dt><dd>{_e(cr['by'] or 'unknown')}</dd></div>
  <div><dt>Creating tool</dt><dd>{_e(cr['tool'] or 'unknown')}</dd></div>
  <div><dt>Last modified</dt><dd>{_e(mo['when'] or 'unknown')}</dd></div>
  <div><dt>Last modified by</dt><dd>{_e(mo['by'] or 'unknown')}</dd></div>
  <div><dt>Modifying tool</dt><dd>{_e(mo['tool'] or 'unknown')}</dd></div>
  <div><dt>Revisions</dt><dd>{_e(s['revisions'])}</dd></div>
  <div><dt>Signatures</dt><dd>{_e(s['signature_status'])}</dd></div>
  <div><dt>Tampering detected</dt><dd>{'yes — ' + str(s['tampering_count']) + ' material finding(s)' if s['tampering_detected'] else 'no'}</dd></div>
</div>
<p class="muted" style="margin-top:10px">Toolchain inference: {_e(origin['toolchain_inference'])}</p>

<h2>What changed / what looks forged</h2>
{findings_html}

<h2>Timeline</h2>
<ul class="tl">{timeline_html}</ul>

<h2>Digital signatures</h2>
{sig_html}

<h2>Consistency graph — {g['contradiction_count']} contradiction(s) / {g['edge_count']} checks · &rho; = {g['contradiction_density']}</h2>
<table><thead><tr><th>Evidence pair</th><th>Expectation</th><th>Observed</th><th>Status</th><th>&kappa;</th></tr></thead>
<tbody>{edges_html}</tbody></table>

<h2>EWDCA score components</h2>
<div>{comp_html}</div>
<p class="muted">Risk = {rep['ewdca'].get('risk')} · weights {_e(json.dumps(rep['ewdca'].get('weights', {})))}</p>

<details><summary>Raw evidence (JSON)</summary>
<pre>{_e(json.dumps(rep['evidence'], indent=2))}</pre></details>

<div class="foot">Authentix {_e(rep['version'])} — heuristic forensic analysis. A low score flags inconsistency, not proven forgery;
a high score is not a guarantee of authenticity.</div>
</div></body></html>"""
