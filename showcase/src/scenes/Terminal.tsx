import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Cursor } from "../Cursor";
import { C, clamp, ease, mono, sans, ui } from "../theme";
import { Headline } from "./Headline";

// Frames of the actions (the sound effects in Root.tsx use them too).
export const ASK = { drop: 22, typeFrom: 28, typeTo: 82, press: 92, sent: 96 };

const PROMPT = "Copy this wave with math. I need a transparent clip for my edit.";

// The real command and output of the skill for this image (see assets/README.md).
const STEPS: { at: number; text: string; tone: "tool" | "out" | "done" }[] = [
  { at: 112, text: "Skill(draw-anything)", tone: "tool" },
  {
    at: 128,
    text: "Bash(python scripts/trace_image.py great-wave.jpg --mode color --colors 16 --lines --transparent --anim wave.webm --svg wave.svg)",
    tone: "tool",
  },
  { at: 168, text: "19,081 closed curves · 118,879 Bézier segments · color accuracy 96.3%", tone: "out" },
  { at: 186, text: "wave.webm (VP9 with alpha) · wave.svg", tone: "out" },
  { at: 206, text: "Done. Put wave.webm on V2, above your footage. The background is transparent.", tone: "done" },
];

const Line: React.FC<{ at: number; text: string; tone: "tool" | "out" | "done" }> = ({ at, text, tone }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [at, at + 12], [0, 1], { ...clamp, easing: ease });
  const isOut = tone === "out";
  return (
    <div
      style={{
        display: "flex",
        gap: 14,
        opacity: o,
        translate: `0px ${(1 - o) * 10}px`,
        marginTop: isOut ? 4 : 18,
        paddingLeft: isOut ? 34 : 0,
        color: isOut ? C.uiMuted : C.uiText,
        fontSize: 28,
        lineHeight: 1.45,
      }}
    >
      <span style={{ color: isOut ? C.uiMuted : tone === "done" ? C.uiText : C.coral }}>{isOut ? "⎿" : "⏺"}</span>
      <span>
        {tone === "tool" ? (
          <>
            <b style={{ fontWeight: 500 }}>{text.split("(")[0]}</b>
            <span style={{ color: C.uiMuted }}>({text.slice(text.indexOf("(") + 1)}</span>
          </>
        ) : (
          text
        )}
      </span>
    </div>
  );
};

export const Terminal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 } });
  const typed = Math.round(interpolate(frame, [ASK.typeFrom, ASK.typeTo], [0, PROMPT.length], clamp));
  const sent = frame >= ASK.sent;
  const chip = spring({ frame: frame - ASK.drop, fps, config: ui });
  const pressed = frame >= ASK.press && frame < ASK.press + 4;
  const cursorOn = Math.floor(frame / 15) % 2 === 0;
  const spinner = "✻✳✢·✢✳"[Math.floor(frame / 4) % 6];

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Headline
        title="Ask Claude Code in plain words."
        sub="The draw-anything skill picks the method and runs it."
        at={4}
      />
      <div
        style={{
          position: "absolute",
          left: 210,
          top: 260,
          width: 1500,
          height: 760,
          borderRadius: 18,
          background: C.ui,
          boxShadow: "0 40px 90px rgba(31,30,29,0.22)",
          overflow: "hidden",
          fontFamily: mono,
          opacity: enter,
          translate: `0px ${(1 - enter) * 40}px`,
        }}
      >
        <div
          style={{ height: 40, background: C.panel, display: "flex", alignItems: "center", gap: 8, padding: "0 16px" }}
        >
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
            <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />
          ))}
          <div style={{ flex: 1, textAlign: "center", color: C.uiMuted, fontFamily: sans, fontSize: 15 }}>
            claude — ~/projects/ocean-reel
          </div>
        </div>

        <div style={{ padding: "28px 40px" }}>
          {sent ? (
            <div style={{ color: C.uiMuted, fontSize: 28, display: "flex", gap: 14, alignItems: "center" }}>
              <span>&gt;</span>
              <span style={{ color: C.uiText }}>{PROMPT}</span>
            </div>
          ) : null}
          {sent ? (
            <div style={{ marginTop: 12, paddingLeft: 34 }}>
              <Chip />
            </div>
          ) : null}
          {STEPS.map((s) => (
            <Line key={s.at} {...s} />
          ))}
          {frame > 132 && frame < 168 ? (
            <div style={{ marginTop: 18, color: C.coral, fontSize: 28 }}>
              {spinner} <span style={{ color: C.uiMuted }}>Tracing 16 color layers…</span>
            </div>
          ) : null}
        </div>

        {/* Input box */}
        <div
          style={{
            position: "absolute",
            left: 32,
            right: 32,
            bottom: 32,
            border: `1.5px solid ${C.line}`,
            borderRadius: 12,
            padding: "18px 22px",
            color: C.uiText,
            fontSize: 28,
            minHeight: 40,
          }}
        >
          {!sent ? (
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <span style={{ color: C.uiMuted }}>&gt;</span>
              {frame >= ASK.drop ? (
                <span
                  style={{ display: "inline-flex", scale: String(0.6 + 0.4 * chip), opacity: Math.min(1, chip * 2) }}
                >
                  <Chip />
                </span>
              ) : null}
              <span>
                {PROMPT.slice(0, typed)}
                <span style={{ opacity: cursorOn ? 1 : 0, color: C.coral }}>▍</span>
              </span>
            </div>
          ) : (
            <span style={{ color: C.uiMuted }}>&gt;</span>
          )}
          <div
            style={{
              position: "absolute",
              right: 14,
              top: "50%",
              width: 44,
              height: 44,
              marginTop: -22,
              borderRadius: 22,
              background: sent ? C.line : C.coral,
              color: "#fff",
              fontFamily: sans,
              fontSize: 24,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              scale: pressed ? "0.88" : "1",
            }}
          >
            ↑
          </div>
        </div>
      </div>
      <Cursor
        show={[0, 120]}
        moves={[
          { at: 0, x: 1900, y: 720 },
          { at: 2, x: 420, y: 950, dur: 20 }, // drag the image in from the desktop
          { at: 60, x: 1650, y: 952, dur: 22 }, // to the send button
          { at: 102, x: 1760, y: 1060, dur: 18 },
        ]}
        presses={[
          [0, ASK.drop],
          [ASK.press, ASK.press + 4],
        ]}
        carry={{
          from: 0,
          to: ASK.drop,
          node: (
            <Img
              src={staticFile("great-wave-original.jpg")}
              style={{ width: 170, borderRadius: 6, boxShadow: "0 12px 30px rgba(0,0,0,0.35)", display: "block" }}
            />
          ),
        }}
      />
    </AbsoluteFill>
  );
};

const Chip: React.FC = () => (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      background: C.panel,
      border: `1px solid ${C.line}`,
      borderRadius: 8,
      padding: "4px 12px 4px 4px",
      fontSize: 22,
      color: C.uiText,
      flexShrink: 0,
    }}
  >
    <Img src={staticFile("great-wave-original.jpg")} style={{ height: 36, borderRadius: 4 }} />
    great-wave.jpg
  </span>
);
