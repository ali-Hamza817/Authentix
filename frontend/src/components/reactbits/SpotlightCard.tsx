import { createElement, useRef, type ReactNode, type MouseEvent } from "react";
import "./reactbits.css";

interface Props {
  children: ReactNode;
  className?: string;
  spotlightColor?: string;
  as?: "div" | "section" | "article";
}

/** React Bits — SpotlightCard. A soft radial glow tracks the cursor. */
export default function SpotlightCard({
  children,
  className = "",
  spotlightColor = "var(--brand-glow)",
  as = "div",
}: Props) {
  const ref = useRef<HTMLElement>(null);

  function onMove(e: MouseEvent<HTMLElement>) {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--rb-x", `${e.clientX - r.left}px`);
    el.style.setProperty("--rb-y", `${e.clientY - r.top}px`);
    el.style.setProperty("--rb-opacity", "1");
  }
  function onLeave() {
    ref.current?.style.setProperty("--rb-opacity", "0");
  }

  return createElement(
    as,
    {
      ref,
      onMouseMove: onMove,
      onMouseLeave: onLeave,
      className: `rb-spotlight ${className}`,
      style: { ["--rb-spot" as string]: spotlightColor },
    },
    children
  );
}
