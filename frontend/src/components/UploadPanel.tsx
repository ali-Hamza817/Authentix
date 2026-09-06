import { useRef, useState, type DragEvent } from "react";
import { FileSearch, UploadCloud, AlertTriangle, FileText, FileSpreadsheet, Presentation } from "lucide-react";
import BlurText from "./reactbits/BlurText";
import ShinyText from "./reactbits/ShinyText";
import GradientText from "./reactbits/GradientText";
import DotGrid from "./reactbits/DotGrid";
import "./UploadPanel.css";

const ACCEPT = ".pdf,.docx,.xlsx,.pptx,.doc,.xls,.ppt";

export default function UploadPanel({
  onFile,
  error,
}: {
  onFile: (f: File) => void;
  error?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  function pick(files: FileList | null) {
    if (files && files[0]) onFile(files[0]);
  }
  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    pick(e.dataTransfer.files);
  }

  return (
    <section className="up">
      <div className="up__hero">
        <DotGrid className="up__grid" />
        <div className="up__heroText">
          <p className="eyebrow">Forensic authenticity check</p>
          <h1 className="up__title">
            <BlurText as="span" text="Know who made a document," />{" "}
            <GradientText className="up__titleAccent">when, and what changed since.</GradientText>
          </h1>
          <p className="up__sub">
            Authentix reads a file&rsquo;s metadata, structure, timestamps, revision history and
            digital signatures, then scores how far its <em>claimed</em> history agrees with the
            evidence it actually carries.
          </p>
        </div>
      </div>

      <div
        className={`up__zone ${drag ? "is-drag" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
      >
        <span className="up__zoneIcon">
          {drag ? <UploadCloud size={30} strokeWidth={1.7} /> : <FileSearch size={30} strokeWidth={1.7} />}
        </span>
        <p className="up__zoneMain">
          Drop a document here, or <span className="up__browse">browse</span>
        </p>
        <p className="up__zoneSub">
          <ShinyText text="PDF · DOCX · XLSX · PPTX — up to 30 MB" speed={5} />
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(e) => pick(e.target.files)}
        />
      </div>

      {error && (
        <div className="up__error" role="alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      <ul className="up__formats">
        <li>
          <FileText size={15} /> PDF — DocInfo, XMP, XRef revisions, /ByteRange coverage, PKCS#7 signer
        </li>
        <li>
          <FileSpreadsheet size={15} /> Office Open XML — core.xml / app.xml, ZIP part times, tracked
          changes, macros
        </li>
        <li>
          <Presentation size={15} /> Output — credibility 0&ndash;100, timeline, and a ranked list of
          what looks forged
        </li>
      </ul>
    </section>
  );
}
