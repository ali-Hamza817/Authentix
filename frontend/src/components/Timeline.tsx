import type { TimelineEvent } from "../lib/types";
import { fmtDateTime } from "../lib/format";

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return <div className="card empty">No datable events could be recovered.</div>;
  }

  return (
    <ol className="tl card">
      {events.map((e, i) => (
        <li key={i} className={`tl__row conf-${e.confidence}`}>
          <span className="tl__marker" aria-hidden="true">
            <span className="tl__dot" />
          </span>
          <div className="tl__content">
            <div className="tl__top">
              <span className="tl__when mono">{e.when ? fmtDateTime(e.when) : "date unknown"}</span>
              {e.confidence !== "high" && <span className="tl__conf">{e.confidence} confidence</span>}
            </div>
            <p className="tl__label">{e.label}</p>
            <p className="tl__src mono">
              {e.source}
              {e.note ? ` · ${e.note}` : ""}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
