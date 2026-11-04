import type { TransitionPresentation, TransitionPresentationComponentProps } from "@remotion/transitions";
import { AbsoluteFill } from "remotion";

type Dir = "left" | "right" | "up" | "down";
type WhipProps = { dir: Dir; blur: number };

// A whip pan: both scenes move fast in one direction. The smear (blur and stretch along
// the move) peaks in the middle, so the cut is hidden in the fastest frames.
const Whip: React.FC<TransitionPresentationComponentProps<WhipProps>> = ({
  children, presentationProgress: p, presentationDirection, passedProps: { dir, blur },
}) => {
  const horizontal = dir === "left" || dir === "right";
  const sign = dir === "left" || dir === "up" ? -1 : 1;
  const offset = (presentationDirection === "exiting" ? p : p - 1) * 100 * sign;
  const smear = Math.sin(Math.PI * p);
  return (
    <AbsoluteFill
      style={{
        translate: horizontal ? `${offset}% 0` : `0 ${offset}%`,
        scale: horizontal ? `${1 + 0.25 * smear} 1` : `1 ${1 + 0.25 * smear}`,
        filter: `blur(${blur * smear}px)`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const whip = (dir: Dir, blur = 22): TransitionPresentation<WhipProps> => ({
  component: Whip,
  props: { dir, blur },
});
