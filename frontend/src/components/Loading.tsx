import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ScanSearch } from "lucide-react";
import "./Loading.css";

const STEPS = [
  "Reading file structure…",
  "Extracting metadata & XMP…",
  "Reconstructing the revision timeline…",
  "Checking digital signatures…",
  "Building the consistency graph…",
  "Scoring credibility…",
];

export default function Loading({ fileName }: { fileName: string }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 750);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="load">
      <div className="load__ring">
        <motion.span
          className="load__pulse"
          animate={{ scale: [1, 1.35, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        />
        <span className="load__core">
          <ScanSearch size={26} strokeWidth={1.8} />
        </span>
      </div>

      <p className="load__file mono">{fileName}</p>

      <ul className="load__steps">
        {STEPS.map((label, i) => (
          <li key={label} className={i <= step ? "is-active" : ""} aria-hidden={i > step}>
            <span className="load__dot" />
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
