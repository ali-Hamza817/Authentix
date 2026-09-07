import type { EvidenceRow } from "../lib/types";
import { reliabilityTone } from "../lib/format";

/** The Evidence Matrix — every observation the assessment rests on, tiered by reliability. */
export default function EvidenceMatrix({ rows }: { rows: EvidenceRow[] }) {
  if (!rows || rows.length === 0) {
    return <div className="card empty">No structured evidence items for this file.</div>;
  }
  const sorted = [...rows].sort((a, b) => b.reliability - a.reliability);

  return (
    <div className="ematrix card">
      <div className="ematrix__scroll">
        <table className="ematrix__tbl">
          <thead>
            <tr>
              <th>Evidence</th>
              <th>Value</th>
              <th>Reliability</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.id} className={r.present ? "" : "is-absent"}>
                <td>{r.label}</td>
                <td className="ematrix__val">{r.present ? r.value : "— not present —"}</td>
                <td>
                  <div className="ematrix__rel">
                    <span className="ematrix__bar">
                      <span
                        style={{ width: `${Math.round(r.reliability * 100)}%`, background: reliabilityTone(r.reliability) }}
                      />
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
        Reliability is the trust that can be placed in the <em>evidence itself</em> — cryptographic ≈ 0.97,
        structural ≈ 0.88, internal ≈ 0.80, tool fingerprint ≈ 0.66, declared metadata ≈ 0.25. Contradictions are
        weighted by it, and findings are ranked by impact&nbsp;&times;&nbsp;reliability. Defaults, pending
        experimental calibration.
      </p>
    </div>
  );
}
