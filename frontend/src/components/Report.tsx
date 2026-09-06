import { motion } from "framer-motion";
import {
  RotateCcw,
  Download,
  UserRound,
  Clock3,
  Wrench,
  Layers,
  PenLine,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import type { Report } from "../lib/types";
import { fmtBytes, fmtDateTime } from "../lib/format";
import ScoreGauge from "./ScoreGauge";
import Findings from "./Findings";
import Timeline from "./Timeline";
import Signatures from "./Signatures";
import ConsistencyGraph from "./ConsistencyGraph";
import EwdcaPanel from "./EwdcaPanel";
import EvidenceAccordion from "./EvidenceAccordion";
import GradientButton from "./reactbits/GradientButton";
import SpotlightCard from "./reactbits/SpotlightCard";
import AnimatedContent from "./reactbits/AnimatedContent";
import "./Report.css";

function Fact({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "bad" | "ok";
}) {
  return (
    <div className="fact">
      <span className="fact__icon">{icon}</span>
      <div>
        <p className="fact__label">{label}</p>
        <p className={`fact__value ${tone ? `is-${tone}` : ""}`}>{value}</p>
      </div>
    </div>
  );
}

export default function ReportView({ report, onReset }: { report: Report; onReset: () => void }) {
  const s = report.summary;
  const g = report.consistency_graph;

  function download() {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${report.file.name || "document"}.authentix.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="rep">
      {/* file line */}
      <div className="rep__file mono">
        <b>{report.file.name}</b>
        <span>{report.file.format_detail}</span>
        <span>{fmtBytes(report.file.size_bytes)}</span>
        <span className="rep__hash">sha-256 {report.file.sha256}</span>
      </div>

      {/* hero */}
      <SpotlightCard className="rep__hero card" as="section">
        <div className="rep__heroGrid">
          <ScoreGauge score={s.credibility_score} band={s.band} cappedAt={report.ewdca.score_capped_at} />

          <div className="rep__verdict">
            <p className="eyebrow">Verdict</p>
            <p className="rep__verdictText">{s.verdict}</p>
            <div className="rep__chips">
              <span className="chip">
                <Layers size={13} /> {s.revisions} revision{s.revisions === 1 ? "" : "s"}
              </span>
              <span className="chip">
                {s.signed ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />} {s.signature_status}
              </span>
              <span className={`chip ${s.tampering_detected ? "chip--bad" : "chip--ok"}`}>
                {s.tampering_detected
                  ? `${s.tampering_count} material finding${s.tampering_count === 1 ? "" : "s"}`
                  : "no tampering detected"}
              </span>
            </div>
          </div>
        </div>

        <div className="rep__facts">
          <Fact icon={<Clock3 size={16} />} label="Created" value={fmtDateTime(s.created.when)} />
          <Fact icon={<UserRound size={16} />} label="Created by" value={s.created.by ?? "unknown"} />
          <Fact icon={<Wrench size={16} />} label="Creating tool" value={s.created.tool ?? "unknown"} />
          <Fact icon={<PenLine size={16} />} label="Last modified" value={fmtDateTime(s.last_modified.when)} />
          <Fact icon={<UserRound size={16} />} label="Last modified by" value={s.last_modified.by ?? "unknown"} />
          <Fact icon={<Wrench size={16} />} label="Modifying tool" value={s.last_modified.tool ?? "unknown"} />
        </div>

        <p className="rep__toolchain">
          <span className="eyebrow">Toolchain inference</span>
          {report.origin.toolchain_inference}
        </p>
      </SpotlightCard>

      {/* findings */}
      <AnimatedContent>
        <h2 className="section-title">What changed / what looks forged</h2>
        <Findings findings={report.findings} />
      </AnimatedContent>

      {/* timeline */}
      <AnimatedContent delay={0.05}>
        <h2 className="section-title">Timeline</h2>
        <Timeline events={report.timeline} />
      </AnimatedContent>

      {/* signatures */}
      <AnimatedContent delay={0.05}>
        <h2 className="section-title">Digital signatures</h2>
        <Signatures signatures={report.signatures} />
      </AnimatedContent>

      {/* consistency graph */}
      <AnimatedContent delay={0.05}>
        <h2 className="section-title">
          Consistency graph — {g.contradiction_count} contradiction{g.contradiction_count === 1 ? "" : "s"} /{" "}
          {g.edge_count} checks · ρ&nbsp;=&nbsp;{g.contradiction_density}
        </h2>
        <ConsistencyGraph graph={g} />
      </AnimatedContent>

      {/* ewdca */}
      <AnimatedContent delay={0.05}>
        <h2 className="section-title">EWDCA score model</h2>
        <EwdcaPanel ewdca={report.ewdca} />
      </AnimatedContent>

      {/* raw evidence */}
      <AnimatedContent delay={0.05}>
        <h2 className="section-title">Raw evidence</h2>
        <EvidenceAccordion evidence={report.evidence} errors={report.errors} />
      </AnimatedContent>

      <motion.div
        className="rep__actions"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
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
