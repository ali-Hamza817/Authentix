# Authentix

**Digital document authenticity & provenance analyzer.**

Upload a document and Authentix reconstructs its history from its own forensic
evidence:

- **who created it, and when** — author, creating application, creation timestamp
- **what happened to it since** — modification dates, incremental revisions, re-saves, signing events
- **what looks forged** — back-dated timestamps, tool/producer contradictions, content added after signing, metadata edited separately from content, active/malicious constructs
- **attribution & device traces** — named people (a digital-signature subject is the only *verified* one), an embedded Windows **username** or **machine / UNC host**, a hardware **MAC address** recovered from a version-1 UUID, the creating machine's **timezone**, printer names, and **GPS + camera model** from EXIF inside embedded photos
- a **credibility score (0–100)** with a band and a ranked, plain-language list of risk factors

> A document does **not** contain the author's IP address — no PDF/Office field holds one. Attribution is whatever the creating software happened to leave behind, and names are self-reported unless verified by a signature.

The score is not a malware verdict. It measures how far the document's *claimed*
history agrees with the evidence it carries. A valid digital signature does **not**
by itself make a document trustworthy — Authentix checks signature **coverage**,
not just validity.

Supported formats: **PDF** (primary), **DOCX / XLSX / PPTX**. Legacy `.doc/.xls/.ppt`
get a limited report.

---

## Quick start (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 1. web app  ->  http://127.0.0.1:8000
.\.venv\Scripts\python.exe server.py

# 2. command line
.\.venv\Scripts\python.exe -m authentix path\to\document.pdf
.\.venv\Scripts\python.exe -m authentix report.docx --html report.html --json report.json
```

macOS / Linux: use `./.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.

There is also `run.ps1` (Windows) / `run.sh` (Unix) that does the venv + install +
launch in one step (and builds the React UI if Node is present).

### Frontend (React)

The polished UI is a **Vite + React + TypeScript** app in `frontend/` (Poppins,
theme-aware, with hand-rolled [React Bits](https://reactbits.dev)-style
components — CountUp, SpotlightCard, ShinyText, BlurText, an ambient DotGrid).

```powershell
npm --prefix frontend install
npm --prefix frontend run build     # emits frontend/dist, which server.py serves
# then:  python server.py  ->  http://127.0.0.1:8000

# live development (Vite on :5173, proxies /api to :8000):
npm --prefix frontend run dev

# UI smoke test — uploads every ./samples file, checks the report renders
# (needs a running server + `npx playwright install chromium` once):
npm --prefix frontend run e2e            # BASE=http://127.0.0.1:8010 to point elsewhere
```

If `frontend/dist` is absent, `server.py` falls back to the dependency-free UI in
`web/`.

### Try it on the bundled samples

```powershell
.\.venv\Scripts\python.exe tests\make_samples.py          # writes ./samples
.\.venv\Scripts\python.exe -m authentix samples\tampered_dates.pdf
.\.venv\Scripts\python.exe -m authentix samples\signed_then_modified.pdf
```

CLI exit code: `0` if the document lands **Credible/Guarded**, `2` if **Suspicious/Untrusted**
(handy in scripts), `1` on a usage error.

---

## How it works

```
document ─▶ intake ─▶ evidence extraction ─▶ normalization ─▶ DECG ─▶ EWDCA ─▶ report
                       (metadata · structure                (consistency  (score +
                        · signature · provenance)             graph)        risk factors)
```

1. **Intake** — identify the format, hash the bytes (SHA-256 / MD5).
2. **Evidence extraction** — pull DocInfo + XMP metadata, physical structure
   (objects, XRef, incremental updates, streams, active content), digital
   signatures (`/ByteRange` coverage, PKCS#7 signer certificate) and provenance
   — see `authentix/evidence/`. The producer string is classified as an
   *application*, a *generator* (from-scratch / HTML-to-PDF: reportlab,
   wkhtmltopdf, …) or a *manipulator* (pypdf, iText, Ghostscript, qpdf, … —
   tools that rewrite an existing PDF). A file last written by a manipulator,
   with its author and dates gone, is flagged `programmatic_rewrite` and its
   origin is reported as **not established** rather than a wall of "unknown".
3. **DECG** (`authentix/decg.py`) — build the *Document Evidence Consistency
   Graph*: nodes are evidence, edges are *forensic expectations* (e.g. "creation
   ≤ modification", "signature covers the whole file", "producer matches the
   authoring app"). Each edge gets a contradiction score κ; the fraction of
   contradicting edges is the density ρ.
4. **EWDCA** (`authentix/ewdca.py`) — the score:

   ```
   Risk = α·A + β·K + γ·(1−P) + δ·(1−S) + λ·ρ + μ·L
   Credibility = round( 100 · (1 − Risk) )
   ```

   `A` structural anomaly · `K` contradiction magnitude · `P` provenance
   confidence · `S` signature integrity (coverage, not just validity) · `ρ`
   contradiction density · `L` finding-severity load. Weights are documented
   defaults in the source; some findings (modification-before-creation, future
   dates, post-signing edits) are *dispositive* and cap the score outright.
5. **Report** (`authentix/report.py`) — a single JSON object with `summary`,
   `origin`, `timeline`, `findings`, `signatures`, `consistency_graph`, `ewdca`
   and a raw `evidence` appendix. `authentix/report_html.py` renders it as a
   standalone HTML page.

---

## Project layout

```
authentix/
├── intake.py            format detection + hashing
├── evidence/
│   ├── pdf.py           DocInfo, XMP, structure, revisions, signatures, findings
│   └── ooxml.py         core.xml / app.xml, ZIP part timestamps, tracked changes, macros
├── decg.py              Document Evidence Consistency Graph
├── ewdca.py             Evidence-Weighted Document Credibility Assessment
├── attribution.py       identities + device traces (username, host, MAC, timezone, EXIF GPS)
├── report.py            assemble the final report object
├── report_html.py       standalone HTML renderer (CLI --html)
└── cli.py               command-line interface
server.py                FastAPI service + UI host (serves frontend/dist, else web/)
frontend/                Vite + React + TypeScript UI
├── src/components/reactbits/   CountUp · SpotlightCard · ShinyText · BlurText · DotGrid · …
├── src/components/             Report, ScoreGauge, Timeline, Findings, Signatures, …
└── src/lib/                    api client · report types · formatting
web/                     no-build fallback UI (index.html · styles.css · app.js)
tests/
├── make_samples.py      synthetic clean + tampered documents
└── test_analyzer.py     behavioural tests  (python tests/test_analyzer.py  or  pytest)
```

---

## API

`POST /api/analyze` — `multipart/form-data`, field `file`. Returns the report JSON.
`GET /api/health` · `GET /api/docs` (OpenAPI).

---

## Limitations

- **No IP address / geolocation of the author.** PDF and Office files do not
  store the creator's IP. Attribution is limited to what the software left in
  metadata, embedded file paths, UUIDs and embedded-photo EXIF — a username, a
  machine name, a network-card MAC, a timezone or a photo's GPS tag, and only
  when it happens to be present.
- Signature analysis validates **structure and coverage** and reads the signer
  certificate; it does **not** perform full RFC 5280 chain / revocation
  validation. Use a dedicated validator (e.g. pyHanko) for legal reliance.
- Heuristics are tuned on synthetic data. A low score flags **inconsistency**,
  not proven forgery; a high score is **not** a guarantee of authenticity.
- Encrypted PDFs and legacy OLE Office files are analysed only partially.
