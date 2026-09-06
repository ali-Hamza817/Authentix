import type { ConsistencyGraph } from "../lib/types";

const STATUS_TONE: Record<string, { color: string; soft: string }> = {
  consistent: { color: "var(--ok)", soft: "var(--ok-soft)" },
  weak: { color: "var(--guard)", soft: "var(--guard-soft)" },
  contradiction: { color: "var(--bad)", soft: "var(--bad-soft)" },
};

export default function ConsistencyGraphView({ graph }: { graph: ConsistencyGraph }) {
  if (graph.edges.length === 0) {
    return <div className="card empty">No expectation edges were applicable to this document.</div>;
  }

  return (
    <div className="decg card">
      <div className="decg__scroll">
        <table className="decg__table">
          <thead>
            <tr>
              <th>Evidence pair</th>
              <th>Expectation</th>
              <th>Observed</th>
              <th>Status</th>
              <th className="decg__num">divergence</th>
            </tr>
          </thead>
          <tbody>
            {graph.edges.map((e) => {
              const tone = STATUS_TONE[e.status] ?? STATUS_TONE.consistent;
              return (
                <tr key={e.id}>
                  <td className="decg__pair">
                    <span>{e.a}</span>
                    <span className="decg__arrow">↔</span>
                    <span>{e.b}</span>
                  </td>
                  <td>{e.relation}</td>
                  <td>{e.observed}</td>
                  <td>
                    <span className="decg__pill" style={{ color: tone.color, background: tone.soft }}>
                      {e.status}
                    </span>
                  </td>
                  <td className="decg__num mono">{e.kappa.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="decg__foot">
        <Stat label="edges" value={graph.edge_count} />
        <Stat label="contradictions" value={graph.contradiction_count} tone="var(--bad)" />
        <Stat label="weak" value={graph.weak_count} tone="var(--guard)" />
        <Stat label="contradiction density" value={graph.contradiction_density} />
        <Stat label="mean divergence" value={graph.mean_kappa} />
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <span className="decg__stat">
      <b style={tone ? { color: tone } : undefined}>{value}</b>
      {label}
    </span>
  );
}
