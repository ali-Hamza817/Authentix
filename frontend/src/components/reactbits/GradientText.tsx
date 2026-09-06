import type { CSSProperties, ReactNode } from "react";
import "./reactbits.css";

interface Props {
  children: ReactNode;
  colors?: string[];
  animate?: boolean;
  className?: string;
}

/** React Bits — GradientText. Gradient-clipped text, optionally flowing. */
export default function GradientText({
  children,
  colors = ["var(--brand)", "var(--brand-bright)", "var(--brand)"],
  animate = false,
  className = "",
}: Props) {
  const style: CSSProperties = {
    backgroundImage: `linear-gradient(90deg, ${colors.join(", ")})`,
  };
  return (
    <span className={`rb-gradient ${animate ? "rb-gradient--flow" : ""} ${className}`} style={style}>
      {children}
    </span>
  );
}
