import { ShieldX, ShieldCheck, ShieldQuestion } from "lucide-react";
import type { Signature } from "../lib/types";
import { fmtDateTime } from "../lib/format";

const INTEGRITY: Record<Signature["integrity"], { label: string; tone: string; Icon: typeof ShieldCheck }> = {
  "structure-intact": { label: "structure intact · full coverage", tone: "var(--ok)", Icon: ShieldCheck },
  superseded: { label: "superseded by a later revision", tone: "var(--guard)", Icon: ShieldQuestion },
  "modified-after-signing": { label: "content added after signing", tone: "var(--bad)", Icon: ShieldX },
};

export default function Signatures({ signatures }: { signatures: Signature[] }) {
  if (signatures.length === 0) {
    return <div className="card empty">This document is not digitally signed.</div>;
  }

  return (
    <div className="sigs">
      {signatures.map((sig) => {
        const meta = INTEGRITY[sig.integrity];
        return (
          <div key={sig.index} className="sig card">
            <div className="sig__head">
              <span className="sig__badge" style={{ color: meta.tone, background: "var(--surface-2)" }}>
                <meta.Icon size={15} /> Signature #{sig.index}
              </span>
              <span className="sig__filter mono">{sig.sub_filter ?? "unknown filter"}</span>
            </div>
            <dl className="sig__grid">
              <div>
                <dt>Signer</dt>
                <dd>{sig.signer_subject ?? sig.name ?? "unknown"}</dd>
              </div>
              <div>
                <dt>Issuer</dt>
                <dd>
                  {sig.signer_issuer ?? "n/a"}
                  {sig.self_signed ? " · self-signed" : ""}
                </dd>
              </div>
              <div>
                <dt>Signing time</dt>
                <dd>{sig.signing_time ? fmtDateTime(sig.signing_time) : "not stated"}</dd>
              </div>
              <div>
                <dt>Coverage</dt>
                <dd style={{ color: meta.tone }}>
                  {sig.covers_whole_file
                    ? "whole file"
                    : `${sig.bytes_after_signature.toLocaleString()} bytes after the signed range`}
                </dd>
              </div>
            </dl>
            <p className="sig__verdict" style={{ color: meta.tone }}>
              {meta.label}
            </p>
            <p className="sig__range mono">byte range [{sig.byte_range.join(", ")}]</p>
          </div>
        );
      })}
    </div>
  );
}
