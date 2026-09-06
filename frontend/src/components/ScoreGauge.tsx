import { motion } from "framer-motion";
import CountUp from "./reactbits/CountUp";
import { BAND_META, METER_ZONES } from "../lib/format";
import type { Band } from "../lib/types";

const CX = 130;
const CY = 128;
const R = 104;
const STROKE = 16;

function polar(value: number) {
  const angle = Math.PI - (value / 100) * Math.PI; // 0 -> left (PI), 100 -> right (0)
  return { x: CX + R * Math.cos(angle), y: CY - R * Math.sin(angle) };
}

function arc(from: number, to: number) {
  const a = polar(from);
  const b = polar(to);
  const large = to - from > 50 ? 1 : 0;
  return `M ${a.x} ${a.y} A ${R} ${R} 0 ${large} 1 ${b.x} ${b.y}`;
}

export default function ScoreGauge({
  score,
  band,
  cappedAt,
}: {
  score: number | null;
  band: Band;
  cappedAt: number | null;
}) {
  const meta = BAND_META[band];
  const shown = score ?? 0;
  const needleAngle = -90 + (shown / 100) * 180;

  return (
    <div className="gauge">
      <svg viewBox="0 0 260 150" className="gauge__svg" role="img" aria-label={`Credibility ${score ?? "n/a"} of 100, ${band}`}>
        <path d={arc(0, 100)} className="gauge__track" strokeWidth={STROKE} fill="none" strokeLinecap="round" />
        {METER_ZONES.map(([f, t, color]) => (
          <path
            key={f}
            d={arc(f + 1, t - 1)}
            stroke={color}
            strokeWidth={STROKE}
            fill="none"
            strokeLinecap="round"
            opacity={score === null ? 0.25 : 0.9}
          />
        ))}

        {score !== null && (
          <motion.g
            initial={{ rotate: -90 }}
            animate={{ rotate: needleAngle }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
            style={{ originX: `${CX}px`, originY: `${CY}px` }}
          >
            <line x1={CX} y1={CY} x2={CX} y2={CY - R + 6} className="gauge__needle" />
            <circle cx={CX} cy={CY} r={7} className="gauge__hub" />
          </motion.g>
        )}
      </svg>

      <div className="gauge__readout">
        {score === null ? (
          <span className="gauge__na">n/a</span>
        ) : (
          <span className="gauge__num">
            <CountUp to={score} duration={1.2} />
            <span className="gauge__den">/100</span>
          </span>
        )}
        <span className="gauge__band" style={{ color: meta.color, background: meta.soft }}>
          {meta.label}
        </span>
        {cappedAt !== null && <span className="gauge__cap">score capped at {cappedAt}</span>}
      </div>
    </div>
  );
}
