import { useEffect, useRef } from "react";

interface Props {
  gap?: number;
  dotRadius?: number;
  className?: string;
}

/**
 * React Bits — DotGrid (ambient variant).
 * A field of dots that gently brighten in a slow travelling wave and lift
 * toward the pointer. Purely decorative; hidden from assistive tech.
 */
export default function DotGrid({ gap = 30, dotRadius = 1.6, className = "" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointer = useRef({ x: -9999, y: -9999 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let w = 0;
    let h = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      w = parent.clientWidth;
      h = parent.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const brand = getComputedStyle(document.documentElement)
      .getPropertyValue("--brand-bright")
      .trim() || "#2e83ab";

    const render = (t: number) => {
      ctx.clearRect(0, 0, w, h);
      const time = reduce ? 0 : t / 1000;
      for (let y = gap; y < h; y += gap) {
        for (let x = gap; x < w; x += gap) {
          const wave = Math.sin(x * 0.015 + y * 0.015 - time * 0.9) * 0.5 + 0.5;
          const dx = x - pointer.current.x;
          const dy = y - pointer.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const near = Math.max(0, 1 - dist / 130);
          const alpha = 0.05 + wave * 0.09 + near * 0.5;
          const r = dotRadius + near * 1.4;
          ctx.beginPath();
          ctx.arc(x, y, r, 0, Math.PI * 2);
          ctx.fillStyle = brand;
          ctx.globalAlpha = Math.min(alpha, 0.7);
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(render);
    };

    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      pointer.current = { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    const onLeave = () => (pointer.current = { x: -9999, y: -9999 });

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerleave", onLeave);
    raf = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
    };
  }, [gap, dotRadius]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
