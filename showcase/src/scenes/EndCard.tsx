import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, clamp, ease, mono, sans, serif } from "../theme";

const ROWS = [
  ["Bézier", "Centerline", "Fourier epicycles", "SDF", "Implicit curves", "Tupper"],
  ["MP4", "GIF", "MOV with alpha", "WebM with alpha", "SVG", "Desmos"],
];

export const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = (at: number) => ({
    opacity: interpolate(frame, [at, at + 20], [0, 1], { ...clamp, easing: ease }),
    translate: interpolate(frame, [at, at + 24], ["0px 16px", "0px 0px"], { ...clamp, easing: ease }),
  });
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", alignItems: "center", textAlign: "center" }}>
      <div style={{ fontFamily: serif, fontSize: 132, color: C.ink, letterSpacing: -2, ...fade(4) }}>draw-anything</div>
      <div style={{ fontFamily: sans, fontSize: 40, color: C.muted, marginTop: 8, ...fade(14) }}>
        Draw anything with math. An Agent Skill for Claude.
      </div>
      {ROWS.map((row, r) => (
        <div key={r} style={{ display: "flex", gap: 14, marginTop: r === 0 ? 64 : 18, justifyContent: "center" }}>
          {row.map((label, i) => (
            <div
              key={label}
              style={{
                fontFamily: mono, fontSize: 24, padding: "10px 20px", borderRadius: 999,
                border: `1.5px solid ${r === 0 ? C.coral : "#D8D3C8"}`, color: r === 0 ? C.coral : C.ink,
                ...fade(28 + r * 12 + i * 3),
              }}
            >
              {label}
            </div>
          ))}
        </div>
      ))}
    </AbsoluteFill>
  );
};
