import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ChevronRight } from "lucide-react";
import type { Finding } from "../lib/types";
import { SEV_META, STANCE_META, reliabilityTone } from "../lib/format";
import SpotlightCard from "./reactbits/SpotlightCard";

function FindingCard({ f, i }: { f: Finding; i: number }) {
  const [open, setOpen] = useState(false);
  const sev = SEV_META[f.severity_label];
  const stance = STANCE_META[f.stance] ?? STANCE_META.neutral;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: Math.min(i * 0.05, 0.35), ease: [0.22, 1, 0.36, 1] }}
    >
      <SpotlightCard className="finding card" spotlightColor={stance.soft}>
        <div className="finding__bar" style={{ background: stance.color }} />
        <div className="finding__body">
          <div className="finding__head">
            <span className="finding__stance" style={{ color: stance.color, background: stance.soft }}>
              {stance.label}
            </span>
            <h3 className="finding__title">{f.title}</h3>
            <span className="finding__sev" style={{ color: sev.color }}>
              {f.severity_label}
            </span>
          </div>

          <p className="finding__detail">{f.detail}</p>

          <button className="finding__toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
            <ChevronRight size={13} className={`finding__chev ${open ? "is-open" : ""}`} />
            reasoning
            <span className="finding__meta">
              {f.reliability != null && (
                <span style={{ color: reliabilityTone(f.reliability) }}>
                  reliability {f.reliability.toFixed(2)}
                </span>
              )}
              {f.confidence !== "n/a" && <span>· confidence {f.confidence}</span>}
              <span>· {f.category}</span>
            </span>
          </button>

          {open && (
            <dl className="finding__chain">
              <div>
                <dt>Evidence</dt>
                <dd>{f.reasoning.evidence}</dd>
              </div>
              <div>
                <dt>Reasoning</dt>
                <dd>{f.reasoning.reasoning}</dd>
              </div>
              <div>
                <dt>Conclusion</dt>
                <dd>{f.reasoning.conclusion}</dd>
              </div>
              <div>
                <dt>Reliability</dt>
                <dd>
                  {f.reliability == null
                    ? "n/a — this is an absence of evidence, interpreted as insufficient"
                    : `${f.reliability.toFixed(2)} — ${stance.blurb}`}
                </dd>
              </div>
            </dl>
          )}
        </div>
      </SpotlightCard>
    </motion.div>
  );
}

export default function Findings({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <div className="card empty">
        <ShieldCheck size={18} />
        <span>No inconsistencies detected across the applicable consistency checks.</span>
      </div>
    );
  }
  return (
    <div className="findings">
      {findings.map((f, i) => (
        <FindingCard key={f.code + i} f={f} i={i} />
      ))}
    </div>
  );
}
