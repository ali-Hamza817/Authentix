import type { ReactNode } from "react";
import { motion } from "framer-motion";

interface Props {
  children: ReactNode;
  delay?: number;
  distance?: number;
  direction?: "vertical" | "horizontal";
  className?: string;
}

/** React Bits — AnimatedContent. Fade + slide a block in on mount (ends fully visible). */
export default function AnimatedContent({
  children,
  delay = 0,
  distance = 16,
  direction = "vertical",
  className = "",
}: Props) {
  const axis = direction === "vertical" ? "y" : "x";
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, [axis]: distance }}
      animate={{ opacity: 1, [axis]: 0 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay }}
    >
      {children}
    </motion.div>
  );
}
