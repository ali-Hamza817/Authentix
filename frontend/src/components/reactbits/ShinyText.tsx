import "./reactbits.css";

interface Props {
  text: string;
  speed?: number;
  className?: string;
  disabled?: boolean;
}

/** React Bits — ShinyText. A sheen sweeps across the text. */
export default function ShinyText({ text, speed = 4, className = "", disabled = false }: Props) {
  return (
    <span
      className={`rb-shiny ${disabled ? "rb-shiny--off" : ""} ${className}`}
      style={{ animationDuration: `${speed}s` }}
    >
      {text}
    </span>
  );
}
