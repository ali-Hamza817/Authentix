import type { Band, SeverityLabel } from "./types";

export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export function fmtDateTime(iso: string | null): string {
  if (!iso) return "unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export function fmtDate(iso: string | null): string {
  if (!iso) return "unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

export function relTime(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const day = 86_400_000;
  if (Math.abs(diff) < day) return "today";
  const days = Math.round(diff / day);
  if (Math.abs(days) < 45) return `${days}d ago`;
  const months = Math.round(days / 30);
  if (Math.abs(months) < 24) return `${months}mo ago`;
  return `${Math.round(days / 365)}y ago`;
}

export const BAND_META: Record<Band, { label: string; color: string; soft: string; note: string }> = {
  Credible: { label: "Credible", color: "var(--ok)", soft: "var(--ok-soft)", note: "consistent evidence" },
  Guarded: { label: "Guarded", color: "var(--guard)", soft: "var(--guard-soft)", note: "review advised" },
  Suspicious: { label: "Suspicious", color: "var(--warn)", soft: "var(--warn-soft)", note: "contradicted history" },
  Untrusted: { label: "Untrusted", color: "var(--bad)", soft: "var(--bad-soft)", note: "definitive inconsistency" },
  Unknown: { label: "Unknown", color: "var(--unknown)", soft: "var(--surface-2)", note: "not analysable" },
};

export const SEV_META: Record<SeverityLabel, { color: string; soft: string }> = {
  High: { color: "var(--bad)", soft: "var(--bad-soft)" },
  Medium: { color: "var(--warn)", soft: "var(--warn-soft)" },
  Low: { color: "var(--brand-bright)", soft: "var(--brand-soft)" },
  Info: { color: "var(--ink-3)", soft: "var(--surface-2)" },
};

export const STANCE_META: Record<
  string,
  { label: string; color: string; soft: string; blurb: string }
> = {
  contradicted: {
    label: "Contradicted",
    color: "var(--bad)",
    soft: "var(--bad-soft)",
    blurb: "evidence is inconsistent with the claimed origin/history",
  },
  insufficient: {
    label: "Insufficient",
    color: "var(--guard)",
    soft: "var(--guard-soft)",
    blurb: "corroborating evidence is absent — not a sign of authenticity",
  },
  supported: {
    label: "Supported",
    color: "var(--authentic)",
    soft: "var(--ok-soft)",
    blurb: "evidence is consistent with the claim",
  },
  neutral: {
    label: "Observation",
    color: "var(--ink-3)",
    soft: "var(--surface-2)",
    blurb: "recorded for context; not an authenticity signal",
  },
};

export function reliabilityTone(r: number | null): string {
  if (r == null) return "var(--ink-3)";
  if (r >= 0.75) return "var(--authentic)";
  if (r >= 0.5) return "var(--guard)";
  return "var(--warn)";
}

/** Score bands on the 0-100 meter: [start, end, color] */
export const METER_ZONES: [number, number, string][] = [
  [0, 25, "var(--bad)"],
  [25, 50, "var(--warn)"],
  [50, 75, "var(--guard)"],
  [75, 100, "var(--ok)"],
];
