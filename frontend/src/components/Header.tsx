import { useEffect, useState } from "react";
import { ShieldCheck, Moon, Sun } from "lucide-react";

type ThemeChoice = "light" | "dark" | "system";

function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
}

export default function Header({ onHome }: { onHome?: () => void }) {
  const [choice, setChoice] = useState<ThemeChoice>(
    () => (localStorage.getItem("authentix-theme") as ThemeChoice) || "system"
  );

  useEffect(() => {
    applyTheme(choice);
    localStorage.setItem("authentix-theme", choice);
  }, [choice]);

  const isDark =
    choice === "dark" ||
    (choice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  return (
    <header className="hdr">
      <div className="shell hdr__inner">
        <button className="hdr__brand" onClick={onHome} disabled={!onHome} aria-label="Authentix home">
          <span className="hdr__mark">
            <ShieldCheck size={17} strokeWidth={2.4} />
          </span>
          <span className="hdr__name">
            Authent<span>ix</span>
          </span>
        </button>

        <div className="hdr__right">
          <span className="hdr__tag">Document authenticity &amp; provenance</span>
          <button
            className="icon-btn"
            aria-label="Toggle colour theme"
            onClick={() => setChoice(isDark ? "light" : "dark")}
          >
            {isDark ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </div>
      </div>
    </header>
  );
}
