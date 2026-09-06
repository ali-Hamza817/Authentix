import { useState } from "react";
import { ChevronRight } from "lucide-react";

export default function EvidenceAccordion({
  evidence,
  errors,
}: {
  evidence: Record<string, unknown>;
  errors: { stage: string; error: string }[];
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="ev card">
      <button className="ev__toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <ChevronRight size={16} className={`ev__chev ${open ? "is-open" : ""}`} />
        {open ? "Hide" : "Show"} raw evidence JSON
        <span className="ev__hint mono">
          {Object.keys(evidence).length} keys{errors.length ? ` · ${errors.length} note(s)` : ""}
        </span>
      </button>

      {open && (
        <div className="ev__body">
          {errors.length > 0 && (
            <div className="ev__errors">
              {errors.map((e, i) => (
                <p key={i} className="mono">
                  <b>{e.stage}:</b> {e.error}
                </p>
              ))}
            </div>
          )}
          <pre className="ev__pre">{JSON.stringify(evidence, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
