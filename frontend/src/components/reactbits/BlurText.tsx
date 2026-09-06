import { motion } from "framer-motion";

interface Props {
  text: string;
  delay?: number;
  className?: string;
  as?: "h1" | "h2" | "h3" | "p" | "span";
}

/** React Bits — BlurText. Words rise and sharpen into place, one after another. */
export default function BlurText({ text, delay = 0, className = "", as = "span" }: Props) {
  const words = text.split(" ");
  const MotionTag = motion[as];

  return (
    <MotionTag
      className={className}
      initial="hidden"
      animate="visible"
      transition={{ staggerChildren: 0.055, delayChildren: delay }}
      aria-label={text}
    >
      {words.map((w, i) => (
        <motion.span
          key={`${w}-${i}`}
          style={{ display: "inline-block", willChange: "transform, filter, opacity" }}
          variants={{
            hidden: { opacity: 0, y: "0.5em", filter: "blur(8px)" },
            visible: {
              opacity: 1,
              y: 0,
              filter: "blur(0px)",
              transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
            },
          }}
        >
          {w}
          {i < words.length - 1 ? " " : ""}
        </motion.span>
      ))}
    </MotionTag>
  );
}
