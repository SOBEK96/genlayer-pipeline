import { forwardRef, type HTMLAttributes } from "react";
import { clsx } from "@/lib/cx";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  /** show the animated conic ambient ring on hover */
  glow?: boolean;
  as?: "div" | "section" | "article";
}

/** Frosted-glass surface with layered borders, inner sheen, and depth shadow. */
export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  ({ glow = false, className, children, ...rest }, ref) => {
    return (
      <div ref={ref} className={clsx("group relative", className)} {...rest}>
        {glow && <div className="ambient-ring" aria-hidden />}
        <div className="glass glass-hover h-full w-full p-5">{children}</div>
      </div>
    );
  },
);
GlassCard.displayName = "GlassCard";
