import type { TimelineEvent } from "../lib/types";
import { fmtDate, fmtDateTime } from "../lib/format";

const CONF_TONE: Record<string, string> = {
  high: "var(--brand-bright)",
  medium: "var(--guard)",
  low: "var(--ink-3)",
};

export default function TimelineVisual({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return <div className="card empty">No datable events could be recovered.</div>;
  }

  const dated = events
    .map((e) => ({ ...e, t: e.when ? new Date(e.when).getTime() : NaN }))
    .filter((e) => !Number.isNaN(e.t))
    .sort((a, b) => a.t - b.t);
  const undated = events.filter((e) => !e.when);

  const min = dated.length ? dated[0].t : 0;
  const max = dated.length ? dated[dated.length - 1].t : 1;
  const span = max - min;
  // even spacing for a few events (or all-same-time); time-proportional for many
  const evenSpread = span === 0 || dated.length < 4;
  const pos = (t: number, i: number) =>
    evenSpread
      ? dated.length === 1
        ? 50
        : 12 + (i / (dated.length - 1)) * 76
      : 8 + ((t - min) / span) * 84;

  return (
    <div className="tlv card">
      {dated.length > 0 && (
        <>
          <div className="tlv__scroll">
            <div className="tlv__track" style={{ minWidth: dated.length > 4 ? `${dated.length * 155}px` : "100%" }}>
              <div className="tlv__axis" />
              {dated.map((e, i) => (
                <div
                  key={i}
                  className={`tlv__pt ${i % 2 ? "is-down" : "is-up"}`}
                  style={{ left: `${pos(e.t, i)}%`, ["--pt" as string]: CONF_TONE[e.confidence] }}
                >
                  <span className="tlv__stem" />
                  <span className="tlv__dot" />
                  <div className="tlv__card">
                    <span className="tlv__when">{fmtDate(e.when)}</span>
                    <span className="tlv__label">{e.label}</span>
                    <span className="tlv__src">{fmtDateTime(e.when)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="tlv__legend">
            <span><i style={{ background: CONF_TONE.high }} /> recorded date</span>
            <span><i style={{ background: CONF_TONE.medium }} /> secondary / XMP</span>
            <span><i style={{ background: CONF_TONE.low }} /> low confidence</span>
          </div>
        </>
      )}

      {undated.length > 0 && (
        <div className="tlv__undated">
          <span className="tlv__undated-h">undated events</span>
          {undated.map((e, i) => (
            <span key={i} className="tlv__pill" title={e.note ?? e.source}>
              {e.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
