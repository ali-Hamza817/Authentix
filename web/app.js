"use strict";

const $ = (sel) => document.querySelector(sel);

const dropzone = $("#dropzone");
const fileInput = $("#fileInput");
const uploadError = $("#uploadError");
const elUploader = $("#uploader");
const elLoading = $("#loading");
const elReport = $("#report");

const BAND_COLOR = {
  Credible: "var(--authentic)",
  Guarded: "var(--suspicious)",
  Suspicious: "var(--tampered)",
  Untrusted: "var(--malicious)",
  Unknown: "var(--ink-soft)",
};
const SEV_COLOR = {
  High: "var(--malicious)",
  Medium: "var(--tampered)",
  Low: "var(--accent)",
  Info: "var(--ink-soft)",
};

/* ---------- upload wiring ---------- */
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) analyze(fileInput.files[0]);
});
["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag"); })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag"); })
);
dropzone.addEventListener("drop", (e) => {
  const f = e.dataTransfer.files[0];
  if (f) analyze(f);
});

/* ---------- run analysis ---------- */
async function analyze(file) {
  uploadError.hidden = true;
  elUploader.hidden = true;
  elReport.hidden = true;
  elLoading.hidden = false;

  const fd = new FormData();
  fd.append("file", file, file.name);
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
    renderReport(body);
  } catch (err) {
    elLoading.hidden = true;
    elUploader.hidden = false;
    uploadError.textContent = "Analysis failed: " + err.message;
    uploadError.hidden = false;
  } finally {
    fileInput.value = "";
  }
}

/* ---------- helpers ---------- */
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
const orUnknown = (s) => (s === null || s === undefined || s === "" ? "unknown" : esc(s));

function fact(dt, dd, cls) {
  return `<div><dt>${esc(dt)}</dt><dd${cls ? ` class="${cls}"` : ""}>${dd}</dd></div>`;
}

/* ---------- render ---------- */
function renderReport(r) {
  const s = r.summary;
  const g = r.consistency_graph;
  const band = s.band || "Unknown";
  const score = s.credibility_score;
  const needle = score == null ? 0 : Math.max(0, Math.min(100, score));

  const facts = [
    fact("Created", orUnknown(s.created.when)),
    fact("Created by", orUnknown(s.created.by)),
    fact("Creating tool", orUnknown(s.created.tool)),
    fact("Last modified", orUnknown(s.last_modified.when)),
    fact("Last modified by", orUnknown(s.last_modified.by)),
    fact("Modifying tool", orUnknown(s.last_modified.tool)),
    fact("Revisions", esc(s.revisions)),
    fact("Signatures", esc(s.signature_status)),
    fact(
      "Tampering detected",
      s.tampering_detected ? `yes — ${s.tampering_count} material finding(s)` : "no",
      s.tampering_detected ? "bad" : "good"
    ),
  ].join("");

  const findings = r.findings.length
    ? r.findings
        .map(
          (f) => `
      <div class="finding" style="--sev:${SEV_COLOR[f.severity_label] || "var(--ink-soft)"}">
        <div class="fhead">
          <span class="sev">${esc(f.severity_label)}</span>
          <span class="ftitle">${esc(f.title)}</span>
          <span class="fcat">${esc(f.category)}</span>
        </div>
        <p>${esc(f.detail)}</p>
      </div>`
        )
        .join("")
    : `<p class="no-findings">No inconsistencies detected across ${g.edge_count} consistency checks.</p>`;

  const timeline = r.timeline.length
    ? r.timeline
        .map(
          (e) => `
      <li>
        <span class="tw">${e.when ? esc(e.when) : "—"}</span>
        <span class="tl"><span class="dot">&bull;</span> ${esc(e.label)}</span>
        <span class="ts">${esc(e.source)}${e.note ? " · " + esc(e.note) : ""}</span>
      </li>`
        )
        .join("")
    : "<li>No datable events could be recovered.</li>";

  const sigs = (r.signatures || []).length
    ? r.signatures
        .map(
          (sig) => `
      <div class="sig">
        <b>Signature #${esc(sig.index)}</b> — ${esc(sig.sub_filter || "unknown filter")}<br>
        Signer: ${esc(sig.signer_subject || sig.name || "unknown")}<br>
        Issuer: ${esc(sig.signer_issuer || "n/a")}${sig.self_signed ? " · <b>self-signed</b>" : ""}<br>
        Signing time: ${esc(sig.signing_time || "not stated")}<br>
        Coverage: ${
          sig.covers_whole_file
            ? "whole file"
            : esc(sig.bytes_after_signature + " bytes after the signed range")
        }
        &nbsp;→&nbsp; <span class="sig-int">${esc(sig.integrity)}</span>
        <div class="k">byte range [${sig.byte_range.join(", ")}]</div>
      </div>`
        )
        .join("")
    : `<p class="no-findings">Document is not digitally signed.</p>`;

  const edges = g.edges.length
    ? g.edges
        .map(
          (ed) => `
      <tr>
        <td>${esc(ed.a)} &harr; ${esc(ed.b)}</td>
        <td>${esc(ed.relation)}</td>
        <td>${esc(ed.observed)}</td>
        <td><span class="pill ${esc(ed.status)}">${esc(ed.status)}</span></td>
        <td class="k">${ed.kappa.toFixed(2)}</td>
      </tr>`
        )
        .join("")
    : `<tr><td colspan="5">No expectation edges were applicable to this document.</td></tr>`;

  const comp = r.ewdca.components || {};
  const components = Object.entries(comp)
    .map(([k, v]) => `<span class="cmp">${esc(k)} <b>${esc(v)}</b></span>`)
    .join("");

  elReport.innerHTML = `
    <div class="r-file">
      <b>${esc(r.file.name)}</b> &nbsp;·&nbsp; ${esc(r.file.format_detail)} &nbsp;·&nbsp; ${r.file.size_bytes.toLocaleString()} bytes<br>
      sha-256 ${esc(r.file.sha256)}<br>
      analysed ${esc(r.analyzed_at)} · Authentix ${esc(r.version)}
    </div>

    <div class="scorecard" style="--band:${BAND_COLOR[band]}">
      <div class="big">${score == null ? "n/a" : score}<small> / 100</small></div>
      <div>
        <div class="band">${esc(band)}</div>
        <div class="meter-wrap">
          <div class="meter"><i class="z1"></i><i class="z2"></i><i class="z3"></i><i class="z4"></i></div>
          <div class="needle" style="left:${needle}%"></div>
        </div>
        <div class="meter-scale"><span>0 · untrusted</span><span>credible · 100</span></div>
      </div>
      <p class="verdict">${esc(s.verdict)}</p>
    </div>

    <h2 class="section">Who &amp; when</h2>
    <dl class="facts">${facts}</dl>
    <p class="toolchain">Toolchain inference: ${esc(r.origin.toolchain_inference)}</p>

    <h2 class="section">What changed / what looks forged</h2>
    ${findings}

    <h2 class="section">Timeline</h2>
    <ul class="timeline">${timeline}</ul>

    <h2 class="section">Digital signatures</h2>
    ${sigs}

    <h2 class="section">
      Consistency graph — ${g.contradiction_count} contradiction(s) / ${g.edge_count} checks · &rho; = ${g.contradiction_density}
    </h2>
    <div class="tbl-wrap">
      <table class="decg">
        <thead><tr><th>Evidence pair</th><th>Expectation</th><th>Observed</th><th>Status</th><th>&kappa;</th></tr></thead>
        <tbody>${edges}</tbody>
      </table>
    </div>

    <h2 class="section">EWDCA score components</h2>
    <div class="components">${components}</div>
    <p class="cmp-note">
      Risk = ${r.ewdca.risk} = &alpha;A + &beta;K + &gamma;(1&minus;P) + &delta;(1&minus;S) + &lambda;&rho;
      &nbsp;·&nbsp; drivers: ${esc((r.ewdca.primary_drivers || []).join("; "))}
    </p>

    <details class="raw">
      <summary>Raw evidence (JSON)</summary>
      <pre>${esc(JSON.stringify(r.evidence, null, 2))}</pre>
    </details>

    <div class="actions">
      <button class="btn" id="againBtn">Analyse another document</button>
      <button class="btn secondary" id="dlBtn">Download report (JSON)</button>
    </div>
  `;

  elLoading.hidden = true;
  elReport.hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });

  $("#againBtn").addEventListener("click", () => {
    elReport.hidden = true;
    elUploader.hidden = false;
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  $("#dlBtn").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(r, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (r.file.name || "document") + ".authentix.json";
    a.click();
    URL.revokeObjectURL(a.href);
  });
}
