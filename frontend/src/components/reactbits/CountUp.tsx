import { useEffect, useRef, useState } from "react";
import { animate, useInView } from "framer-motion";

interface Props {
  to: number;
  from?: number;
  duration?: number;
  decimals?: number;
  className?: string;
  startWhenVisible?: boolean;
}

/** React Bits — CountUp. Eases a number from `from` to `to`. */
export default function CountUp({
  to,
  from = 0,
  duration = 1.1,
  decimals = 0,
  className,
  startWhenVisible = true,
}: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [value, setValue] = useState(from);

  useEffect(() => {
    if (startWhenVisible && !inView) return;
    const controls = animate(from, to, {
      duration,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setValue(v),
    });
    return () => controls.stop();
  }, [to, from, duration, inView, startWhenVisible]);

  return (
    <span ref={ref} className={className}>
      {value.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
    </span>
  );
}
