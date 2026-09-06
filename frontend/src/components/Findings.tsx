import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import type { Finding } from "../lib/types";
import { SEV_META } from "../lib/format";
import SpotlightCard from "./reactbits/SpotlightCard";

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
      {findings.map((f, i) => {
        const sev = SEV_META[f.severity_label];
        return (
          <motion.div
            key={f.code + i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: Math.min(i * 0.05, 0.35), ease: [0.22, 1, 0.36, 1] }}
          >
            <SpotlightCard className="finding card" spotlightColor={sev.soft}>
              <div className="finding__bar" style={{ background: sev.color }} />
              <div className="finding__body">
                <div className="finding__head">
                  <span className="finding__sev" style={{ color: sev.color, background: sev.soft }}>
                    {f.severity_label}
                  </span>
                  <h3 className="finding__title">{f.title}</h3>
                  <span className="finding__cat">{f.category}</span>
                </div>
                <p className="finding__detail">{f.detail}</p>
              </div>
            </SpotlightCard>
          </motion.div>
        );
      })}
    </div>
  );
}
