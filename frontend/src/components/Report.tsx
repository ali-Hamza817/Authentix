import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  RotateCcw, Download, UserRound, Clock3, Wrench, PenLine, Info, Copy, Check,
} from "lucide-react";
import type { Report } from "../lib/types";
import { fmtBytes, fmtDateTime } from "../lib/format";
import ScoreGauge from "./ScoreGauge";
import StatusTiles from "./StatusTiles";
import Findings from "./Findings";
import TimelineVisual from "./TimelineVisual";
import Signatures from "./Signatures";
import DecgDiagram from "./DecgDiagram";
import EwdcaPanel from "./EwdcaPanel";
import EvidenceMatrix from "./EvidenceMatrix";
import AttributionView from "./Attribution";
import EvidenceAccordion from "./EvidenceAccordion";
import GradientButton from "./reactbits/GradientButton";
import SpotlightCard from "./reactbits/SpotlightCard";
import "./Report.css";

const TOOL_BADGE: Record<string, string> = { manipulator: "library", generator: "generated" };

const SECTIONS = [
  ["evidence", "Evidence"],
  ["findings", "Findings"],
  ["timeline", "Timeline"],
  ["signatures", "Signatures"],
  ["graph", "Graph"],
  ["attribution", "Attribution"],
  ["model", "Model"],
] as const;

function Fact({
  icon, label, value, badge,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | null;
  badge?: string;
}) {
  const missing = value == null || value === "";
  return (
    <div className="fact">
      <span className="fact__icon">{icon}</span>
      <div>
        <p className="fact__label">{label}</p>
        <p className={`fact__value ${missing ? "is-missing" : ""}`}>
          {missing ? "not recorded" : value}
          {badge && !missing && <span className="fact__badge">{badge}</span>}
        </p>
      </div>
    </div>
  );
}

export default function ReportView({ report, onReset }: { report: Report; onReset: () => void }) {
  const s = report.summary;
  const g = report.consistency_graph;
  const [copied, setCopied] = useState(false);
  const [active, setActive] = useState<string>("evidence");
  const secRefs = useRef<Record<string, HTMLElement | null>>({});

  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (vis[0]) setActive(vis[0].target.id);
      },
      { rootMargin: "-45% 0px -50% 0px", threshold: [0, 0.5, 1] }
    );
    Object.values(secRefs.current).forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, []);

  function download() {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${report.file.name || "document"}.authentix.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
  function copyHash() {
    navigator.clipboard?.writeText(report.file.sha256).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  const Section = ({ id, title, count, children }: { id: string; title: string; count?: number; children: React.ReactNode }) => (
    <section id={id} ref={(el) => (secRefs.current[id] = el)} className="sec">
      <h2 className="section-title">
        {title}
        {count != null && count > 0 && <span className="section-count">{count}</span>}
      </h2>
      {children}
    </section>
  );

  return (
    <div className="rep">
      {/* file line */}
      <div className="rep__file mono">
        <b>{report.file.name}</b>
        <span>{report.file.format_detail}</span>
        <span>{fmtBytes(report.file.size_bytes)}</span>
        <button className="rep__hash" onClick={copyHash} title="Copy SHA-256">
          {copied ? <Check size={11} /> : <Copy size={11} />} sha-256 {report.file.sha256.slice(0, 16)}…
        </button>
      </div>

      {/* ---------------- hero: verdict at a glance ---------------- */}
      <SpotlightCard className="rep__hero card" as="section">
        <div className="rep__heroGrid">
          <ScoreGauge score={s.credibility_score} band={s.band} cappedAt={report.ewdca.score_capped_at} />

          <div className="rep__verdict">
            <p className="eyebrow">
              Verdict
              {s.confidence !== "n/a" && (
                <span className="rep__conf" title={s.confidence_basis ?? undefined}>
                  {s.confidence} confidence
                </span>
              )}
            </p>
            <p className="rep__verdictText">{s.verdict}</p>

            <div className="rep__facts">
              <Fact icon={<Clock3 size={15} />} label="Created" value={s.created.when ? fmtDateTime(s.created.when) : null} />
              <Fact icon={<UserRound size={15} />} label="By" value={s.created.by} />
              <Fact
                icon={<Wrench size={15} />}
                label="Tool"
                value={s.created.tool}
                badge={report.origin.tool_kind ? TOOL_BADGE[report.origin.tool_kind] : undefined}
              />
              <Fact icon={<PenLine size={15} />} label="Last modified" value={s.last_modified.when ? fmtDateTime(s.last_modified.when) : null} />
            </div>
          </div>
        </div>

        {!s.origin_known && (
          <div className="rep__originNote">
            <Info size={15} />
            <span>
              <b>Origin not established.</b> No author and no creation date — the tools shown are the last software to
              write the file, not who authored it.
            </span>
          </div>
        )}

        <p className="rep__toolchain">
          <span className="eyebrow">Toolchain</span>
          {report.origin.toolchain_inference}
        </p>
      </SpotlightCard>

      {/* ---------------- at-a-glance status tiles ---------------- */}
      <StatusTiles report={report} />

      {/* ---------------- sticky section nav ---------------- */}
      <nav className="rep__nav">
        {SECTIONS.map(([id, label]) => (
          <a key={id} href={`#${id}`} className={active === id ? "is-active" : ""}>
            {label}
          </a>
        ))}
      </nav>

      <Section id="evidence" title="Evidence & reliability">
        <EvidenceMatrix rows={report.evidence_matrix} />
      </Section>

      <Section id="findings" title="Findings" count={report.findings.length}>
        <Findings findings={report.findings} />
      </Section>

      <Section id="timeline" title="Timeline">
        <TimelineVisual events={report.timeline} />
      </Section>

      <Section id="signatures" title="Digital signatures" count={report.signatures.length}>
        <Signatures signatures={report.signatures} />
      </Section>

      <Section id="graph" title="Consistency graph" count={g.contradiction_count}>
        <DecgDiagram graph={g} />
      </Section>

      <Section id="attribution" title="Attribution & device traces" count={s.attribution_signals}>
        <AttributionView attribution={report.attribution} />
      </Section>

      <Section id="model" title="EWDCA score model">
        <EwdcaPanel ewdca={report.ewdca} />
        <div style={{ marginTop: 12 }}>
          <EvidenceAccordion evidence={report.evidence} errors={report.errors} />
        </div>
      </Section>

      <motion.div
        className="rep__actions"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.25 }}
      >
        <GradientButton onClick={onReset}>
          <RotateCcw size={15} style={{ marginRight: 8, verticalAlign: "-2px" }} />
          Analyse another document
        </GradientButton>
        <GradientButton variant="ghost" onClick={download}>
          <Download size={15} style={{ marginRight: 8, verticalAlign: "-2px" }} />
          Download report (JSON)
        </GradientButton>
      </motion.div>

      <p className="rep__meta mono">
        Authentix {report.version} · analysed {fmtDateTime(report.analyzed_at)}
      </p>
    </div>
  );
}
