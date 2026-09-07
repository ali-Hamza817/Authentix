import { useState } from "react";
import { ChevronRight } from "lucide-react";
import type { EvidenceRow } from "../lib/types";
import { reliabilityTone } from "../lib/format";

const BANDS = [
  { key: "high", label: "High (structural / crypto)", min: 0.75, color: "var(--authentic)" },
  { key: "med", label: "Medium (internal / fingerprint)", min: 0.5, color: "var(--guard)" },
  { key: "low", label: "Low (declared metadata)", min: 0, color: "var(--warn)" },
];

/** The Evidence Matrix — every observation the assessment rests on, tiered by reliability. */
export default function EvidenceMatrix({ rows }: { rows: EvidenceRow[] }) {
  const [open, setOpen] = useState(false);

  if (!rows || rows.length === 0) {
    return <div className="card empty">No structured evidence items for this file.</div>;
  }
  const present = rows.filter((r) => r.present);
  const sorted = [...rows].sort((a, b) => b.reliability - a.reliability);

  const counts = BANDS.map((b, i) => ({
    ...b,
    n: present.filter((r) => r.reliability >= b.min && (i === 0 || r.reliability < BANDS[i - 1].min)).length,
  }));

  return (
    <div className="ematrix card">
      <div className="ematrix__summary">
        <div className="ematrix__bars">
          {counts.map((c) => (
            <div
              key={c.key}
              className="ematrix__seg"
              style={{ flexGrow: c.n || 0.001, background: c.color }}
              title={`${c.label}: ${c.n}`}
            />
          ))}
        </div>
        <div className="ematrix__key">
          {counts.map((c) => (
            <span key={c.key}>
              <i style={{ background: c.color }} />
              {c.n} {c.label.split(" ")[0].toLowerCase()}
            </span>
          ))}
          <span className="ematrix__keynote">
            {present.length} of {rows.length} evidence items present
          </span>
        </div>
      </div>

      <button className="ematrix__toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <ChevronRight size={14} className={open ? "is-open" : ""} />
        {open ? "hide" : "show"} every observation
      </button>

      {open && (
        <>
          <div className="ematrix__scroll">
            <table className="ematrix__tbl">
              <thead>
                <tr><th>Evidence</th><th>Value</th><th>Reliability</th><th>Source</th></tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr key={r.id} className={r.present ? "" : "is-absent"}>
                    <td>{r.label}</td>
                    <td className="ematrix__val">{r.present ? r.value : "— not present —"}</td>
                    <td>
                      <div className="ematrix__rel">
                        <span className="ematrix__bar">
                          <span style={{ width: `${Math.round(r.reliability * 100)}%`, background: reliabilityTone(r.reliability) }} />
                        </span>
                        <span className="ematrix__relnum" style={{ color: reliabilityTone(r.reliability) }}>
                          {r.reliability.toFixed(2)}
                        </span>
                        <span className="ematrix__tier">{r.reliability_label}</span>
                      </div>
                    </td>
                    <td className="ematrix__src">{r.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="ematrix__note">
            Reliability is trust in the <em>evidence itself</em> — cryptographic ≈ 0.97, structural ≈ 0.88, internal ≈ 0.80,
            tool fingerprint ≈ 0.66, declared metadata ≈ 0.25. Contradictions are weighted by it; findings rank by
            impact&nbsp;&times;&nbsp;reliability. Defaults, pending experimental calibration.
          </p>
        </>
      )}
    </div>
  );
}
