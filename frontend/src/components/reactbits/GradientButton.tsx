import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./reactbits.css";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "solid" | "ghost";
}

/** React Bits — GradientButton. Gradient fill, lift on hover, sweeping highlight. */
export default function GradientButton({ children, variant = "solid", className = "", ...rest }: Props) {
  return (
    <button className={`rb-gbtn rb-gbtn--${variant} ${className}`} {...rest}>
      <span className="rb-gbtn__label">{children}</span>
    </button>
  );
}
