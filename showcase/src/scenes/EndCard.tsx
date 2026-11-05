import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, clamp, ease, mono, sans, serif } from "../theme";

const ROWS = [
  ["Bézier", "Centerline", "Fourier epicycles", "SDF", "Implicit curves", "Tupper"],
  ["MP4", "GIF", "MOV with alpha", "WebM with alpha", "SVG", "Desmos"],
];

// Clients that read the open Agent Skills format (agentskills.io and each client's own docs).
export const AGENTS = [
  "Claude",
  "ChatGPT",
  "Codex",
  "Gemini CLI",
  "Antigravity",
  "OpenCode",
  "Cursor",
  "GitHub Copilot",
  "any compatible agent",
];
// The names change on half-beats of the music (one beat = 23 frames).
export const START = 34.5; // first change
export const STEP = 11.5; // frames per name
const LINE = 76; // slot height in px

const Slot: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Each step moves the slot up by one line, with a short spring.
  let pos = 0;
  for (let i = 1; i < AGENTS.length; i++) {
    pos += spring({ frame: frame - START - (i - 1) * STEP, fps, config: { damping: 200 }, durationInFrames: 9 });
  }
  return (
    <span style={{ display: "block", height: LINE, overflow: "hidden" }}>
      <span style={{ display: "block", translate: `0px ${-pos * LINE}px` }}>
        {AGENTS.map((a, i) => (
          <span
            key={a}
            style={{
              display: "block",
              height: LINE,
              lineHeight: `${LINE}px`,
              color: C.coral,
              fontWeight: 600,
              fontSize: 60,
              opacity: interpolate(Math.abs(pos - i), [0, 0.7], [1, 0], clamp),
            }}
          >
            {a}.
          </span>
        ))}
      </span>
    </span>
  );
};

export const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = (at: number) => ({
    opacity: interpolate(frame, [at, at + 20], [0, 1], { ...clamp, easing: ease }),
    translate: interpolate(frame, [at, at + 24], ["0px 16px", "0px 0px"], { ...clamp, easing: ease }),
  });
  const chipsAt = START + (AGENTS.length - 1) * STEP;
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", alignItems: "center", textAlign: "center" }}>
      <div style={{ fontFamily: serif, fontSize: 132, color: C.ink, letterSpacing: -2, ...fade(4) }}>draw-anything</div>
      <div style={{ fontFamily: sans, fontSize: 40, color: C.muted, marginTop: 4, ...fade(10) }}>
        Draw anything with math.
      </div>
      <div style={{ fontFamily: sans, fontSize: 48, color: C.ink, marginTop: 14, ...fade(16) }}>
        An Agent Skill for
        <Slot />
      </div>
      {ROWS.map((row, r) => (
        <div key={r} style={{ display: "flex", gap: 14, marginTop: r === 0 ? 44 : 18, justifyContent: "center" }}>
          {row.map((label, i) => (
            <div
              key={label}
              style={{
                fontFamily: mono,
                fontSize: 24,
                padding: "10px 20px",
                borderRadius: 999,
                border: `1.5px solid ${r === 0 ? C.coral : "#D8D3C8"}`,
                color: r === 0 ? C.coral : C.ink,
                ...fade(chipsAt - 30 + r * 10 + i * 3),
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
