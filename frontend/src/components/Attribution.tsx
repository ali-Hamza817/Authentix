import { BadgeCheck, MapPin, ShieldQuestion } from "lucide-react";
import type { Attribution } from "../lib/types";

type Row = { label: string; value: React.ReactNode; source: string; confidence?: string; hot?: boolean };

const CONF_TONE: Record<string, string> = {
  high: "var(--bad)",
  medium: "var(--warn)",
  low: "var(--ink-3)",
};

export default function AttributionView({ attribution }: { attribution: Attribution }) {
  const a = attribution;
  const dev = a.device || {};
  const net = a.network || {};
  const gps = a.geolocation?.image_gps || [];

  const rows: Row[] = [];
  for (const u of dev.usernames || [])
    rows.push({ label: "User account", value: u.value, source: u.source, confidence: u.confidence, hot: true });
  for (const h of dev.machine_names || [])
    rows.push({ label: "Computer / host", value: h.value, source: h.source, confidence: h.confidence, hot: true });
  for (const m of dev.mac_addresses || [])
    rows.push({
      label: "MAC address",
      value: `${m.value}${m.randomized ? " (randomised)" : ""}`,
      source: m.source,
      confidence: m.confidence,
      hot: !m.randomized,
    });
  for (const g of gps)
    rows.push({
      label: "Photo GPS",
      value: (
        <a href={g.maps_url} target="_blank" rel="noreferrer">
          {g.lat}, {g.lon} <MapPin size={12} style={{ verticalAlign: "-1px" }} />
        </a>
      ),
      source: g.source,
      confidence: g.confidence,
      hot: true,
    });
  for (const c of dev.cameras || [])
    rows.push({ label: "Camera / phone", value: c.value, source: c.source, confidence: c.confidence });
  for (const t of dev.timezones || [])
    rows.push({
      label: "Timezone",
      value: t.region ? `${t.value} — ${t.region}` : t.value,
      source: t.source,
      confidence: t.confidence,
    });
  for (const p of dev.printers || []) rows.push({ label: "Printer", value: p.value, source: p.source, confidence: p.confidence });
  for (const ip of net.ip_addresses || [])
    rows.push({ label: "IP in file", value: ip.value, source: ip.note, confidence: "low" });
  for (const s of dev.software || []) rows.push({ label: "Software", value: s.value, source: s.source });
  for (const l of dev.locales || []) rows.push({ label: "Locale", value: l, source: "document settings" });
  for (const p of (dev.local_paths || []).slice(0, 10))
    rows.push({ label: "Local path", value: <span className="mono">{p}</span>, source: "creating machine" });

  const emails = net.emails || [];

  return (
    <div className="attr">
      <div className="attr__disclaimer">
        <ShieldQuestion size={16} />
        <span>
          A document does <b>not</b> store the author&rsquo;s IP address — there is no field for it. What&rsquo;s
          below are traces the creating software left in metadata, embedded paths, UUIDs and photos. Names are
          self-reported unless marked <BadgeCheck size={12} style={{ verticalAlign: "-2px" }} /> verified.
        </span>
      </div>

      {a.identities.length > 0 && (
        <div className="attr__people">
          <p className="eyebrow">People named in this file</p>
          <ul>
            {a.identities.map((i, idx) => (
              <li key={idx} className={i.verified ? "is-verified" : ""}>
                <span className="attr__name">{i.name}</span>
                <span className="attr__role">{i.role}</span>
                <span className={`attr__label ${i.verified ? "is-verified" : ""}`}>
                  {i.verified && <BadgeCheck size={12} />} {i.label ?? (i.verified ? "verified" : "self-reported")}
                </span>
                <span className="attr__src">{i.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {rows.length > 0 ? (
        <div className="attr__tblwrap">
          <table className="attr__tbl">
            <thead>
              <tr>
                <th>Trace</th>
                <th>Value</th>
                <th>Confidence</th>
                <th>Source / interpretation</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => (
                <tr key={idx} className={r.hot ? "is-hot" : ""}>
                  <td>{r.label}</td>
                  <td className="attr__val">{r.value}</td>
                  <td>
                    {r.confidence && (
                      <span
                        className="attr__conf"
                        style={{ color: CONF_TONE[r.confidence] ?? "var(--ink-3)" }}
                      >
                        {r.confidence}
                      </span>
                    )}
                  </td>
                  <td className="attr__rowsrc">{r.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="no-findings">No identifying device traces were found in this file.</p>
      )}

      {emails.length > 0 && (
        <p className="attr__emails mono">
          e-mail addresses in file: {emails.join("  ·  ")}
        </p>
      )}
    </div>
  );
}
