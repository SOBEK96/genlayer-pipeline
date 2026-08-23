import { useRef } from "react";
import {
  useMotionValue,
  useSpring,
  useTransform,
  type MotionStyle,
  type MotionValue,
} from "framer-motion";

interface TiltOptions {
  /** max rotation in degrees */
  max?: number;
  /** how far the card lifts toward the viewer (px) */
  lift?: number;
  /** spring stiffness/damping feel */
  stiffness?: number;
  damping?: number;
}

interface TiltApi {
  ref: React.RefObject<HTMLDivElement>;
  style: MotionStyle;
  glare: MotionValue<string>;
  onMouseMove: (e: React.MouseEvent) => void;
  onMouseLeave: () => void;
}

/**
 * Subtle 3D tilt driven by pointer position, smoothed by springs.
 * Apply `style` to a motion.div inside a `.perspective` parent.
 */
export function useTilt({
  max = 12,
  lift = 18,
  stiffness = 220,
  damping = 18,
}: TiltOptions = {}): TiltApi {
  const ref = useRef<HTMLDivElement>(null);

  // normalized pointer position, -0.5 .. 0.5
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const hovered = useMotionValue(0);

  const spring = { stiffness, damping, mass: 0.4 };
  const rotateX = useSpring(useTransform(py, [-0.5, 0.5], [max, -max]), spring);
  const rotateY = useSpring(useTransform(px, [-0.5, 0.5], [-max, max]), spring);
  const z = useSpring(useTransform(hovered, [0, 1], [0, lift]), spring);

  // moving light highlight follows the cursor
  const glareX = useTransform(px, [-0.5, 0.5], [0, 100]);
  const glareY = useTransform(py, [-0.5, 0.5], [0, 100]);
  const glare = useTransform(
    [glareX, glareY, hovered] as MotionValue[],
    ([gx, gy, h]) =>
      `radial-gradient(600px circle at ${gx}% ${gy}%, rgba(255,255,255,${
        0.1 * (h as number)
      }), transparent 40%)`,
  );

  const onMouseMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    px.set((e.clientX - rect.left) / rect.width - 0.5);
    py.set((e.clientY - rect.top) / rect.height - 0.5);
    hovered.set(1);
  };

  const onMouseLeave = () => {
    px.set(0);
    py.set(0);
    hovered.set(0);
  };

  const style: MotionStyle = {
    rotateX,
    rotateY,
    z,
    transformStyle: "preserve-3d",
  };

  return { ref, style, glare, onMouseMove, onMouseLeave };
}
