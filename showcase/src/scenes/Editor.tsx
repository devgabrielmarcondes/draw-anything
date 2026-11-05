import { Video } from "@remotion/media";
import {
  AbsoluteFill,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Cursor } from "../Cursor";
import { C, clamp, ease, sans, ui } from "../theme";

// Frames of the drag and drop (the sound effects in Root.tsx use them too).
export const DROP = { grab: 18, release: 30 };
import { Headline } from "./Headline";

// Stand-in for the creator's footage: a slow sunset over the sea.
const Footage: React.FC = () => {
  const t = useCurrentFrame() / 30;
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, #f3c9a0 0%, #e9a27f ${38 + 4 * Math.sin(t)}%, #6f8fa6 ${62 + 3 * Math.sin(t * 0.7)}%, #2f4d66 100%)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "70%",
          top: "22%",
          width: 80,
          height: 80,
          borderRadius: 40,
          background: "#fff4e0",
          opacity: 0.85,
          filter: "blur(2px)",
        }}
      />
    </AbsoluteFill>
  );
};

const Clip: React.FC<{ left: number; width: number; color: string; label: string; grow?: number }> = ({
  left,
  width,
  color,
  label,
  grow = 1,
}) => (
  <div
    style={{
      position: "absolute",
      left,
      width: width * grow,
      top: 6,
      bottom: 6,
      borderRadius: 6,
      background: color,
      color: "#fff",
      fontFamily: sans,
      fontSize: 15,
      fontWeight: 500,
      padding: "6px 10px",
      overflow: "hidden",
      whiteSpace: "nowrap",
      opacity: Math.min(1, grow * 3),
    }}
  >
    {label}
  </div>
);

// A minimal, generic video editor. With `withOverlay`, the skill output plays on track V2.
export const Editor: React.FC<{ withOverlay?: boolean; title: string; sub: string }> = ({
  withOverlay = false,
  title,
  sub,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = withOverlay ? 1 : spring({ frame, fps, config: { damping: 200 } });
  const card = spring({ frame: frame - 26, fps, config: ui });
  const binIn = spring({ frame: frame - 2, fps, config: ui });
  const clipIn = spring({ frame: frame - DROP.release, fps, config: ui });
  const playhead = interpolate(frame, [0, 7 * fps], withOverlay ? [210, 520] : [70, 210], clamp);

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Headline title={title} sub={sub} at={6} />
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
            ocean-reel — Edit
          </div>
        </div>

        {/* Media bin */}
        <div
          style={{
            position: "absolute",
            left: 16,
            top: 56,
            width: 330,
            height: 420,
            background: C.panel,
            borderRadius: 10,
            padding: 16,
          }}
        >
          <div style={{ color: C.uiMuted, fontFamily: sans, fontSize: 14, marginBottom: 12 }}>Media</div>
          <div
            style={{
              height: 70,
              borderRadius: 6,
              background: "linear-gradient(180deg,#f3c9a0,#6f8fa6)",
              marginBottom: 8,
            }}
          />
          <div style={{ color: C.uiText, fontFamily: sans, fontSize: 14, marginBottom: 18 }}>ocean_broll.mp4</div>
          {withOverlay ? (
            <div style={{ opacity: Math.min(1, binIn * 2), scale: String(0.9 + 0.1 * binIn) }}>
              <div
                style={{
                  height: 70,
                  borderRadius: 6,
                  overflow: "hidden",
                  marginBottom: 8,
                  background: "repeating-conic-gradient(#3a3935 0% 25%, #2c2b28 0% 50%) 50% / 14px 14px",
                }}
              >
                <Img src={staticFile("great-wave-original.jpg")} style={{ height: "100%", opacity: 0.9 }} />
              </div>
              <div style={{ color: C.coral, fontFamily: sans, fontSize: 14 }}>wave.webm · alpha</div>
            </div>
          ) : null}
        </div>

        {/* Preview monitor */}
        <div
          style={{
            position: "absolute",
            left: 362,
            top: 56,
            width: 750,
            height: 420,
            borderRadius: 10,
            overflow: "hidden",
            background: "#000",
          }}
        >
          <Footage />
          {withOverlay ? (
            <Sequence from={DROP.release}>
              <Video src={staticFile("wave.webm")} muted style={{ width: "100%", height: "100%" }} />
            </Sequence>
          ) : null}
        </div>

        {/* Inspector */}
        <div
          style={{
            position: "absolute",
            left: 1128,
            top: 56,
            right: 16,
            height: 420,
            background: C.panel,
            borderRadius: 10,
            padding: 16,
            fontFamily: sans,
            fontSize: 15,
            color: C.uiMuted,
            lineHeight: 2.1,
          }}
        >
          <div style={{ color: C.uiText }}>Inspector</div>
          <div>Sequence · 1920 × 1080</div>
          <div>Frame rate · 30 fps</div>
          {withOverlay ? (
            <>
              <div style={{ color: C.coral, opacity: clipIn }}>Clip · wave.webm</div>
              <div style={{ color: C.coral, opacity: clipIn }}>Alpha · yes</div>
            </>
          ) : null}
        </div>

        {/* Timeline */}
        <div
          style={{
            position: "absolute",
            left: 16,
            right: 16,
            top: 492,
            bottom: 16,
            background: C.panel,
            borderRadius: 10,
          }}
        >
          {["V2", "V1", "A1"].map((t, i) => (
            <div
              key={t}
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: 24 + i * 66,
                height: 58,
                borderTop: `1px solid ${C.line}`,
              }}
            >
              <div
                style={{ position: "absolute", left: 16, top: 18, color: C.uiMuted, fontFamily: sans, fontSize: 14 }}
              >
                {t}
              </div>
            </div>
          ))}
          <div style={{ position: "absolute", left: 70, right: 16, top: 90, height: 58 }}>
            <Clip left={0} width={520} color="#3f6e8c" label="ocean_broll.mp4" />
            <Clip left={526} width={640} color="#3f6e8c" label="ocean_broll_02.mp4" />
          </div>
          <div style={{ position: "absolute", left: 70, right: 16, top: 156, height: 58 }}>
            <Clip left={0} width={1166} color="#4b5d3f" label="♪ soundtrack.wav" />
          </div>
          {withOverlay ? (
            <div style={{ position: "absolute", left: 70, right: 16, top: 24, height: 58 }}>
              {frame >= DROP.release ? (
                <Clip left={140} width={460} color={C.coral} label="wave.webm" grow={clipIn} />
              ) : null}
            </div>
          ) : null}
          <div
            style={{ position: "absolute", top: 8, bottom: 8, left: 70 + playhead, width: 2, background: C.coral }}
          />
        </div>
      </div>

      {withOverlay ? (
        <Cursor
          show={[0, 70]}
          moves={[
            { at: 0, x: 1100, y: 640 },
            { at: 2, x: 300, y: 500, dur: 16 }, // to wave.webm in the media bin
            { at: DROP.grab + 1, x: 470, y: 800, dur: DROP.release - DROP.grab - 2 }, // drag to V2
            { at: DROP.release + 8, x: 760, y: 1000, dur: 20 },
          ]}
          presses={[[DROP.grab, DROP.release]]}
          carry={{
            from: DROP.grab,
            to: DROP.release,
            node: (
              <div
                style={{
                  width: 180,
                  height: 40,
                  borderRadius: 6,
                  background: C.coral,
                  color: "#fff",
                  fontFamily: sans,
                  fontSize: 15,
                  padding: "10px 12px",
                  boxSizing: "border-box",
                }}
              >
                wave.webm
              </div>
            ),
          }}
        />
      ) : null}
      {!withOverlay ? (
        <div
          style={{
            position: "absolute",
            left: 1250,
            top: 470,
            width: 560,
            borderRadius: 14,
            background: "#fff",
            padding: 14,
            boxShadow: "0 30px 70px rgba(31,30,29,0.28)",
            opacity: Math.min(1, card * 1.5),
            translate: `${(1 - card) * 140}px ${(1 - card) * 30}px`,
            rotate: `${(1 - card) * 6 + 2}deg`,
          }}
        >
          <Img
            src={staticFile("great-wave-original.jpg")}
            style={{ width: "100%", borderRadius: 8, display: "block" }}
          />
          <div
            style={{
              fontFamily: sans,
              fontSize: 20,
              color: C.muted,
              marginTop: 10,
              opacity: interpolate(frame, [48, 64], [0, 1], { ...clamp, easing: ease }),
            }}
          >
            great-wave.jpg
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
