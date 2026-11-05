import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp } from "./theme";

// A waypoint: from frame `at`, glide to (x, y) in `dur` frames.
export type Move = { at: number; x: number; y: number; dur?: number };

// One closed-form spring per move, added on top of the previous ones (no restart),
// so the path stays continuous and any frame can be rendered on its own.
const track = (frame: number, fps: number, moves: Move[], key: "x" | "y") =>
  moves
    .slice(1)
    .reduce(
      (v, m, i) =>
        v +
        (m[key] - moves[i][key]) *
          spring({ frame: frame - m.at, fps, config: { damping: 200 }, durationInFrames: m.dur ?? 16 }),
      moves[0][key],
    );

// A macOS-style pointer. `presses`: [down, up] frame pairs. `carry`: what it drags, from grab to release.
export const Cursor: React.FC<{
  moves: Move[];
  presses?: [number, number][];
  carry?: { from: number; to: number; node: React.ReactNode };
  show: [number, number];
}> = ({ moves, presses = [], carry, show }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const x = track(frame, fps, moves, "x");
  const y = track(frame, fps, moves, "y");
  const down = presses.some(([d, u]) => frame >= d && frame < u);
  const opacity = interpolate(frame, [show[0], show[0] + 6, show[1] - 8, show[1]], [0, 1, 1, 0], clamp);
  const carrying = carry && frame >= carry.from && frame < carry.to;
  return (
    <div style={{ position: "absolute", left: x, top: y, opacity, pointerEvents: "none" }}>
      {carrying ? (
        <div style={{ position: "absolute", left: 10, top: 14, rotate: "-4deg", opacity: 0.92 }}>{carry.node}</div>
      ) : null}
      <svg width="40" height="40" viewBox="0 0 24 24" style={{ scale: down ? "0.86" : "1", transformOrigin: "0 0" }}>
        <path
          d="M3 2 L3 19.5 L7.6 15.4 L10.6 22 L13.6 20.7 L10.7 14.2 L16.8 14.2 Z"
          fill="#111"
          stroke="#fff"
          strokeWidth="1.4"
          strokeLinejoin="round"
          style={{ filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.35))" }}
        />
      </svg>
    </div>
  );
};
