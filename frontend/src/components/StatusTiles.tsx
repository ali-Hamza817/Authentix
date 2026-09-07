import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Fingerprint,
  PenTool,
  History,
  ScanFace,
  FileWarning,
} from "lucide-react";
import type { Report } from "../lib/types";

type Tone = "good" | "warn" | "bad" | "neutral";
type Tile = { key: string; label: string; Icon: typeof ShieldCheck; status: string; detail: string; tone: Tone };

const TONE_VAR: Record<Tone, string> = {
  good: "var(--authentic)",
  warn: "var(--guard)",
  bad: "var(--bad)",
  neutral: "var(--ink-3)",
};

function derive(r: Report): Tile[] {
  const s = r.summary;
  const g = r.consistency_graph;
  const codes = new Set(r.findings.map((f) => f.code));
  const contradicted = r.findings.filter((f) => f.stance === "contradicted");

  // Integrity
  let integrity: Tile;
  if (contradicted.length === 0 && g.contradiction_count === 0) {
    integrity = { key: "i", label: "Integrity", Icon: ShieldCheck, status: "Consistent", detail: `${g.edge_count} checks passed`, tone: "good" };
  } else if (contradicted.length === 0) {
    integrity = { key: "i", label: "Integrity", Icon: ShieldAlert, status: "Minor issues", detail: `${g.weak_count} weak link(s)`, tone: "warn" };
  } else {
    integrity = { key: "i", label: "Integrity", Icon: ShieldX, status: "Contradicted", detail: `${contradicted.length} contradiction(s)`, tone: "bad" };
  }

  // Provenance
  const tk = r.origin.tool_kind;
  let provenance: Tile;
  if (!s.origin_known) {
    provenance = { key: "p", label: "Provenance", Icon: Fingerprint, status: "Not established", detail: "no author or dates", tone: "bad" };
  } else if (tk === "manipulator" || tk === "generator") {
    provenance = { key: "p", label: "Provenance", Icon: Fingerprint, status: tk === "manipulator" ? "Re-saved by tool" : "Machine-generated", detail: r.origin.library ?? "automated", tone: "warn" };
  } else {
    provenance = { key: "p", label: "Provenance", Icon: Fingerprint, status: "Established", detail: r.origin.creator_application ?? "authored in an app", tone: "good" };
  }

  // Signature
  let signature: Tile;
  if (!s.signed) {
    signature = { key: "s", label: "Signature", Icon: PenTool, status: "Unsigned", detail: "no digital signature", tone: "neutral" };
  } else if (codes.has("modified_after_signing")) {
    signature = { key: "s", label: "Signature", Icon: ShieldX, status: "Broken", detail: "content added after signing", tone: "bad" };
  } else if (r.evidence.signature_integrity === 1) {
    signature = { key: "s", label: "Signature", Icon: ShieldCheck, status: "Full coverage", detail: "covers the whole file", tone: "good" };
  } else {
    signature = { key: "s", label: "Signature", Icon: ShieldAlert, status: "Partial", detail: "coverage / chain unverified", tone: "warn" };
  }

  // Timeline
  const dated = r.timeline.filter((e) => e.when).length;
  const temporalBad = ["modified_before_created", "future_creation_date", "future_created", "timestamp_gap_no_edits", "signed_before_created"].some((c) => codes.has(c));
  const timeline: Tile = temporalBad
    ? { key: "t", label: "Timeline", Icon: History, status: "Inconsistent", detail: "an impossible ordering", tone: "bad" }
    : { key: "t", label: "Timeline", Icon: History, status: `${dated} dated event${dated === 1 ? "" : "s"}`, detail: `${s.revisions} revision(s)`, tone: dated ? "good" : "neutral" };

  // Attribution
  const attribution: Tile = s.attribution_signals > 0
    ? { key: "a", label: "Attribution", Icon: ScanFace, status: `${s.attribution_signals} trace(s)`, detail: "device / identity leaks", tone: "warn" }
    : { key: "a", label: "Attribution", Icon: ScanFace, status: "No traces", detail: "nothing identifying leaked", tone: "neutral" };

  // Content
  const active = (r.evidence.structure as { active_content?: string[] } | undefined)?.active_content ?? [];
  const macros = codes.has("contains_macros");
  const content: Tile = macros || active.length
    ? { key: "c", label: "Content", Icon: FileWarning, status: macros ? "Contains macros" : "Active content", detail: macros ? "executable VBA" : active.slice(0, 2).join(", "), tone: "warn" }
    : { key: "c", label: "Content", Icon: ShieldCheck, status: "Static", detail: "no scripts or macros", tone: "good" };

  return [integrity, provenance, signature, timeline, attribution, content];
}

export default function StatusTiles({ report }: { report: Report }) {
  return (
    <div className="tiles">
      {derive(report).map((t) => (
        <div key={t.key} className="tile" style={{ ["--tile" as string]: TONE_VAR[t.tone] }}>
          <div className="tile__top">
            <t.Icon size={15} />
            <span>{t.label}</span>
          </div>
          <div className="tile__status">{t.status}</div>
          <div className="tile__detail">{t.detail}</div>
        </div>
      ))}
    </div>
  );
}
