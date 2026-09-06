import { useCallback, useState } from "react";
import { AnimatePresence, motion, MotionConfig } from "framer-motion";
import Header from "./components/Header";
import UploadPanel from "./components/UploadPanel";
import Loading from "./components/Loading";
import ReportView from "./components/Report";
import Footer from "./components/Footer";
import { analyzeDocument, ApiError } from "./lib/api";
import type { Report } from "./lib/types";
import "./App.css";

type Phase = "idle" | "loading" | "done" | "error";

export default function App() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");

  const run = useCallback(async (file: File) => {
    setFileName(file.name);
    setError("");
    setPhase("loading");
    try {
      const rep = await analyzeDocument(file);
      setReport(rep);
      setPhase("done");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong during analysis.");
      setPhase("error");
    }
  }, []);

  const reset = useCallback(() => {
    setPhase("idle");
    setReport(null);
    setError("");
  }, []);

  return (
    <MotionConfig reducedMotion="user">
    <div className="app">
      <Header onHome={phase === "done" ? reset : undefined} />

      <main className="shell app__main">
        <AnimatePresence mode="wait">
          {(phase === "idle" || phase === "error") && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            >
              <UploadPanel onFile={run} error={error} />
            </motion.div>
          )}

          {phase === "loading" && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Loading fileName={fileName} />
            </motion.div>
          )}

          {phase === "done" && report && (
            <motion.div
              key="report"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              <ReportView report={report} onReset={reset} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <Footer />
    </div>
    </MotionConfig>
  );
}
