import { motion } from "framer-motion";
import CountUp from "./reactbits/CountUp";
import { BAND_META, METER_ZONES } from "../lib/format";
import type { Band } from "../lib/types";

const CX = 130;
const CY = 130;
const R = 100;
const STROKE = 15;

/** Point on the circle for a 0-100 value (0 = left / 9 o'clock, 100 = right / 3 o'clock). */
function point(value: number, radius = R) {
  const a = Math.PI - (value / 100) * Math.PI; // math angle, y flipped below
  return { x: CX + radius * Math.cos(a), y: CY - radius * Math.sin(a) };
}

/** Circular arc across the TOP of the gauge. sweep-flag 1 = clockwise on screen = over the top. */
function arc(from: number, to: number) {
  const a = point(from);
  const b = point(to);
  return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} A ${R} ${R} 0 0 1 ${b.x.toFixed(2)} ${b.y.toFixed(2)}`;
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
  const tip = point(shown, R - 6);

  return (
    <div className="gauge">
      <svg
        viewBox="0 0 260 168"
        className="gauge__svg"
        role="img"
        aria-label={`Credibility ${score ?? "not available"} of 100, ${band}`}
      >
        <path d={arc(0, 100)} className="gauge__track" strokeWidth={STROKE} fill="none" strokeLinecap="round" />
        {METER_ZONES.map(([f, t, color]) => (
          <path
            key={f}
            d={arc(f + 1.2, t - 1.2)}
            stroke={color}
            strokeWidth={STROKE}
            fill="none"
            strokeLinecap="round"
            opacity={score === null ? 0.2 : 0.95}
          />
        ))}

        {score !== null && (
          <>
            <motion.line
              x1={CX}
              y1={CY}
              className="gauge__needle"
              initial={{ x2: point(0, R - 6).x, y2: point(0, R - 6).y }}
              animate={{ x2: tip.x, y2: tip.y }}
              transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
            />
            <circle cx={CX} cy={CY} r={6} className="gauge__hub" />
          </>
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
