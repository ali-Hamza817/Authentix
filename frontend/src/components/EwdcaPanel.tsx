import { motion } from "framer-motion";
import type { Ewdca } from "../lib/types";

const LABELS: Record<string, string> = {
  A_anomaly: "A · structural anomaly",
  K_contradiction: "K · contradiction magnitude",
  P_provenance_confidence: "P · provenance confidence",
  S_signature_integrity: "S · signature integrity",
  rho_contradiction_density: "ρ · contradiction density",
  L_finding_load: "L · finding load",
};
// components where a HIGH value is bad (drives risk up)
const RISK_UP = new Set(["A_anomaly", "K_contradiction", "rho_contradiction_density", "L_finding_load"]);

export default function EwdcaPanel({ ewdca }: { ewdca: Ewdca }) {
  const comps = Object.entries(ewdca.components);

  return (
    <div className="ewdca card">
      <p className="ewdca__formula mono">
        Risk = αA + βK + γ(1−P) + δ(1−S) + λρ + μL {ewdca.risk !== null && `= ${ewdca.risk}`}
      </p>

      {comps.length > 0 && (
        <div className="ewdca__bars">
          {comps.map(([key, value]) => {
            const bad = RISK_UP.has(key);
            return (
              <div key={key} className="ewdca__row">
                <span className="ewdca__label">{LABELS[key] ?? key}</span>
                <span className="ewdca__val mono">{value.toFixed(2)}</span>
                <span className="ewdca__track">
                  <motion.span
                    className="ewdca__fill"
                    style={{ background: bad ? "var(--warn)" : "var(--ok)" }}
                    initial={{ width: 0 }}
                    animate={{ width: value > 0 ? `${Math.max(3, value * 100)}%` : "0%" }}
                    transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
                  />
                </span>
              </div>
            );
          })}
        </div>
      )}

      {ewdca.primary_drivers.length > 0 && (
        <div className="ewdca__drivers">
          <p className="eyebrow">Primary drivers</p>
          <ul>
            {ewdca.primary_drivers.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
