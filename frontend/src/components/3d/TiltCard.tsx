import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { useTilt } from "@/hooks/useTilt";
import { clsx } from "@/lib/cx";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** raise inner content toward the viewer for parallax depth */
  contentClassName?: string;
  glow?: boolean;
  max?: number;
}

/**
 * Interactive spatial card: reacts to pointer position with perspective shift,
 * a cursor-following light glare, and a springy lift. Children sit on a raised
 * 3D layer for genuine parallax.
 */
export function TiltCard({ children, className, contentClassName, glow = true, max = 12 }: TiltCardProps) {
  const { ref, style, glare, onMouseMove, onMouseLeave } = useTilt({ max });

  return (
    <div className="perspective">
      <motion.div
        ref={ref}
        onMouseMove={onMouseMove}
        onMouseLeave={onMouseLeave}
        style={style}
        whileTap={{ scale: 0.99 }}
        className={clsx("group relative rounded-2xl", className)}
      >
        {glow && <div className="ambient-ring" aria-hidden />}
        <div className="glass relative overflow-hidden p-5">
          {/* cursor-following light */}
          <motion.div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{ background: glare }}
          />
          <div
            className={clsx("relative", contentClassName)}
            style={{ transform: "translateZ(40px)" }}
          >
            {children}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
