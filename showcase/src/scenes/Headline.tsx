import { interpolate, useCurrentFrame } from "remotion";
import { C, clamp, ease, sans, serif } from "../theme";

export const Headline: React.FC<{ title: string; sub?: string; at?: number }> = ({ title, sub, at = 0 }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ position: "absolute", top: 64, left: 0, right: 0, textAlign: "center" }}>
      <div
        style={{
          fontFamily: serif,
          fontSize: 68,
          color: C.ink,
          letterSpacing: -0.5,
          opacity: interpolate(frame, [at, at + 20], [0, 1], { ...clamp, easing: ease }),
          translate: interpolate(frame, [at, at + 24], ["0px 18px", "0px 0px"], { ...clamp, easing: ease }),
        }}
      >
        {title}
      </div>
      {sub ? (
        <div
          style={{
            fontFamily: sans,
            fontSize: 30,
            color: C.muted,
            marginTop: 10,
            opacity: interpolate(frame, [at + 10, at + 30], [0, 1], { ...clamp, easing: ease }),
          }}
        >
          {sub}
        </div>
      ) : null}
    </div>
  );
};
