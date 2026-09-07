import { useState } from "react";
import { ChevronRight } from "lucide-react";
import type { ConsistencyGraph } from "../lib/types";

const TONE: Record<string, string> = {
  consistent: "var(--line-strong)",
  weak: "var(--guard)",
  contradiction: "var(--bad)",
};

function shorten(s: string, n = 14) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export default function DecgDiagram({ graph }: { graph: ConsistencyGraph }) {
  const [showTable, setShowTable] = useState(false);

  if (graph.edges.length === 0) {
    return <div className="card empty">No expectation edges were applicable to this document.</div>;
  }

  const nodes = graph.nodes.slice(0, 9);
  const idx = new Map(nodes.map((n, i) => [n, i]));
  const W = 780;
  const H = 320;
  const cx = W / 2;
  const cy = H / 2;
  const r = 100;
  const p = (i: number) => {
    const a = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a), a };
  };

  const drawn = graph.edges.filter((e) => idx.has(e.a) && idx.has(e.b));
  drawn.sort((a, b) => (a.status === "contradiction" ? 1 : 0) - (b.status === "contradiction" ? 1 : 0));

  return (
    <div className="decg2 card">
      <div className="decg2__figure">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Document Evidence Consistency Graph: evidence nodes with contradiction edges highlighted.">
          {drawn.map((e) => {
            const A = p(idx.get(e.a)!);
            const B = p(idx.get(e.b)!);
            const contra = e.status === "contradiction";
            return (
              <line
                key={e.id}
                x1={A.x} y1={A.y} x2={B.x} y2={B.y}
                stroke={TONE[e.status] ?? TONE.consistent}
                strokeWidth={contra ? 2.4 : e.status === "weak" ? 1.8 : 1}
                strokeDasharray={e.status === "weak" ? "5 4" : undefined}
                opacity={e.status === "consistent" ? 0.5 : 1}
              />
            );
          })}
          {nodes.map((n, i) => {
            const { x, y, a } = p(i);
            const right = Math.cos(a) >= -0.15;
            return (
              <g key={n}>
                <circle cx={x} cy={y} r={6} fill="var(--surface)" stroke="var(--ink-2)" strokeWidth={1.5} />
                <text
                  x={x + (right ? 12 : -12)}
                  y={y + 4}
                  textAnchor={right ? "start" : "end"}
                  fontSize="11.5"
                  fill="var(--ink-2)"
                  fontFamily="'IBM Plex Mono', monospace"
                >
                  {shorten(n)}
                  <title>{n}</title>
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="decg2__stats">
        <span><b style={{ color: "var(--bad)" }}>{graph.contradiction_count}</b> contradiction(s)</span>
        <span><b style={{ color: "var(--guard)" }}>{graph.weak_count}</b> weak</span>
        <span><b>{graph.edge_count}</b> checks</span>
        <span>density <b>{graph.weighted_density ?? graph.contradiction_density}</b></span>
        <span className="decg2__legend">
          <i style={{ background: TONE.contradiction }} /> contradiction
          <i style={{ background: TONE.weak }} /> weak
          <i style={{ background: TONE.consistent }} /> consistent
        </span>
      </div>

      <button className="decg2__toggle" onClick={() => setShowTable((v) => !v)} aria-expanded={showTable}>
        <ChevronRight size={14} className={showTable ? "is-open" : ""} />
        {showTable ? "hide" : "show"} the {graph.edge_count} checks
      </button>

      {showTable && (
        <div className="decg2__scroll">
          <table className="decg__table">
            <thead>
              <tr><th>Evidence pair</th><th>Expectation</th><th>Observed</th><th>Status</th><th className="decg__num">rel · &kappa;</th></tr>
            </thead>
            <tbody>
              {graph.edges.map((e) => (
                <tr key={e.id}>
                  <td className="decg__pair">{e.a} <span className="decg__arrow">&harr;</span> {e.b}</td>
                  <td>{e.relation}</td>
                  <td>{e.observed}</td>
                  <td><span className={`pill ${e.status}`}>{e.status}</span></td>
                  <td className="decg__num mono">{(e.reliability ?? 0).toFixed(2)} · {e.kappa.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
