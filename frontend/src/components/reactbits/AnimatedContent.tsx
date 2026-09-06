import type { ReactNode } from "react";
import { motion } from "framer-motion";

interface Props {
  children: ReactNode;
  delay?: number;
  distance?: number;
  direction?: "vertical" | "horizontal";
  className?: string;
  once?: boolean;
}

/** React Bits — AnimatedContent. Fade + slide a block into view. */
export default function AnimatedContent({
  children,
  delay = 0,
  distance = 18,
  direction = "vertical",
  className = "",
  once = true,
}: Props) {
  const axis = direction === "vertical" ? "y" : "x";
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, [axis]: distance }}
      whileInView={{ opacity: 1, [axis]: 0 }}
      viewport={{ once, margin: "-60px" }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay }}
    >
      {children}
    </motion.div>
  );
}
